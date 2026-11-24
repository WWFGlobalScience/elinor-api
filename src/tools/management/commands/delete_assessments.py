import csv
import re
from collections import defaultdict
from datetime import date, timezone

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.signals import post_delete
from django.test.utils import override_settings
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from api import signals
from api.models import (
    Assessment,
    Collaborator,
    Document,
    ManagementArea,
)

TEST_LIKE_RE = r"(test|prueba|dummy|demo|delete|essai|teste|xxx|asdf|sample)"
ROLE_NAMES = {
    Collaborator.ADMIN: "admin",
    Collaborator.CONTRIBUTOR: "contributor",
    Collaborator.OBSERVER: "observer",
}
# Receivers that must not run during a bulk delete: collaborator-removal emails, and
# file deletes that would happen inside the transaction (files are deleted on commit instead).
SUPPRESSED_RECEIVERS = [
    (signals.notify_collaborator_deleted, Collaborator),
    (signals.delete_ap_files, Assessment),
    (signals.delete_ma_files, ManagementArea),
]

KEEP_REFERENCED = "keep: no assessment, but referenced by kept MA"
DELETE_LISTED = "delete: MA of listed assessment"
DELETE_ORPHAN = "delete: no assessment, not referenced by kept MA"


def fmt_ts(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def fmt_user(user):
    if user is None:
        return None
    name = user.get_full_name()
    return f"{user.username} / {name}" if name else user.username


def fmt_collaborators(assessment):
    collabs = sorted(
        assessment.collaborators.all(), key=lambda c: (-c.role, c.user.username)
    )
    return "; ".join(
        f"{fmt_user(c.user)} ({ROLE_NAMES.get(c.role, c.role)})" for c in collabs
    )


def assessment_status(a):
    return a.get_status_display()


def assessment_policy(a):
    return a.get_data_policy_display()


class Command(BaseCommand):
    help = (
        "Permanently delete a list of assessments, their management areas (and optionally "
        "unreferenced MAs with no assessment), with cascaded rows and S3 files. "
        "Collaborator-removal emails are suppressed. Always run with --dry-run --report first, "
        "ideally against a local restore of the target environment."
    )

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument("--ids", help="Comma-separated assessment IDs")
        source.add_argument(
            "--csv",
            help="CSV of assessments to delete (e.g. an admin export). If it has 'name' and "
            "'created on' columns, each row must match the DB or the command aborts.",
        )
        parser.add_argument(
            "--id-column", default="ID", help="ID column name in --csv (default: ID)"
        )
        parser.add_argument(
            "--orphan-mas",
            action="store_true",
            help="Also delete MAs that have no assessment, unless a kept MA refers to them "
            "(as parent or containedby).",
        )
        parser.add_argument(
            "--orphans-created-before",
            type=date.fromisoformat,
            help="YYYY-MM-DD. Limit --orphan-mas to MAs created before this date, so the "
            "deleted set matches a previously approved report and skips in-progress drafts.",
        )
        parser.add_argument(
            "--report", help="Write an XLSX report of what will be deleted and kept"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report only; make no changes to the database or storage",
        )

    # ---------- input ----------

    def read_input(self, options):
        rows = {}
        if options["ids"]:
            try:
                ids = {int(i) for i in options["ids"].split(",") if i.strip()}
            except ValueError as e:
                raise CommandError(f"Invalid --ids: {e}")
            return ids, rows

        id_col = options["id_column"]
        with open(options["csv"], newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if id_col not in (reader.fieldnames or []):
                raise CommandError(f"Column '{id_col}' not found in {options['csv']}")
            for row in reader:
                try:
                    rows[int(row[id_col])] = row
                except ValueError:
                    raise CommandError(f"Non-integer ID in CSV: {row[id_col]!r}")
        return set(rows), rows

    def verify(self, ids, rows, assessments):
        found = {a.pk: a for a in assessments}
        missing = sorted(ids - set(found))
        if missing:
            raise CommandError(f"Assessments not found: {missing}")

        # modeltranslation: compare the untranslated base column, as exported
        base_names = dict(
            Assessment.objects.rewrite(False)
            .filter(pk__in=ids)
            .values_list("pk", "name")
        )
        errors, changed = [], {}
        for pk, row in rows.items():
            a = found[pk]
            if "name" in row and row["name"] != base_names[pk]:
                errors.append(f"{pk}: name {row['name']!r} != DB {base_names[pk]!r}")
            if "created on" in row and row["created on"] != fmt_ts(a.created_on):
                errors.append(
                    f"{pk}: created on {row['created on']} != DB {fmt_ts(a.created_on)}"
                )
            if "updated on" in row and row["updated on"] != fmt_ts(a.updated_on):
                changed[pk] = f"updated {fmt_ts(a.updated_on)} (list: {row['updated on']})"
        if errors:
            raise CommandError(
                "Input does not match the database; wrong environment or stale list?\n"
                + "\n".join(errors)
            )
        return changed

    # ---------- plan ----------

    def build_plan(self, ids, include_orphans, orphans_created_before=None):
        assessments = list(
            Assessment.objects.filter(pk__in=ids)
            .select_related(
                "management_area",
                "organization",
                "person_responsible",
                "created_by",
                "checkout",
            )
            .prefetch_related("collaborators__user")
            .annotate(
                n_answers=Count("survey_answer_likerts", distinct=True),
                n_flags=Count("assessment_flags", distinct=True),
                n_changes=Count("assessment_changes", distinct=True),
            )
            .order_by("pk")
        )

        listed_mas = {a.management_area_id for a in assessments if a.management_area_id}
        orphans = set()
        if include_orphans:
            qs = ManagementArea.objects.filter(assessment__isnull=True)
            if orphans_created_before:
                qs = qs.filter(created_on__date__lt=orphans_created_before)
            orphans = set(qs.values_list("pk", flat=True))

        links = list(
            ManagementArea.objects.filter(
                Q(parent__isnull=False) | Q(containedby__isnull=False)
            ).values_list("pk", "parent_id", "containedby_id")
        )

        # Orphans referenced by any kept MA are kept; repeat until stable, since keeping
        # an orphan may in turn keep the orphans it refers to.
        delete_mas = listed_mas | orphans
        kept_orphan_refs = defaultdict(set)
        changed = True
        while changed:
            changed = False
            for pk, parent_id, containedby_id in links:
                if pk in delete_mas:
                    continue
                for target in (parent_id, containedby_id):
                    if target in orphans and target in delete_mas:
                        delete_mas.discard(target)
                        changed = True
                    if target in orphans:
                        kept_orphan_refs[target].add(pk)

        nulled_links = []
        for pk, parent_id, containedby_id in links:
            if pk in delete_mas:
                continue
            for field, target in (("parent", parent_id), ("containedby", containedby_id)):
                if target in delete_mas:
                    nulled_links.append((pk, field, target))

        return {
            "assessments": assessments,
            "listed_mas": listed_mas,
            "orphans": orphans,
            "delete_mas": delete_mas,
            "kept_orphan_refs": kept_orphan_refs,
            "nulled_links": nulled_links,
            "files": self.collect_files(assessments, delete_mas),
        }

    def collect_files(self, assessments, delete_mas):
        files = []
        for a in assessments:
            if a.management_plan_file:
                files.append(("Assessment.management_plan_file", a.pk, a.management_plan_file.name))
        for ma in ManagementArea.objects.filter(pk__in=delete_mas).only(
            "pk", "import_file", "map_image"
        ):
            for field in ("import_file", "map_image"):
                f = getattr(ma, field)
                if f:
                    files.append((f"ManagementArea.{field}", ma.pk, f.name))

        assessment_ids = [a.pk for a in assessments]
        result = []
        for field, pk, path in files:
            shared = [
                f"Assessment {x}"
                for x in Assessment.objects.filter(management_plan_file=path)
                .exclude(pk__in=assessment_ids)
                .values_list("pk", flat=True)
            ]
            shared += [
                f"ManagementArea {x}"
                for x in ManagementArea.objects.filter(
                    Q(import_file=path) | Q(map_image=path)
                )
                .exclude(pk__in=delete_mas)
                .values_list("pk", flat=True)
            ]
            shared += [
                f"Document {x}"
                for x in Document.objects.filter(file=path).values_list("pk", flat=True)
            ]
            result.append((field, pk, path, ", ".join(shared)))
        return result

    # ---------- report ----------

    def summary_rows(self, plan, changed):
        a_ids = [a.pk for a in plan["assessments"]]
        assessments = plan["assessments"]
        return [
            ("Assessments to delete", len(assessments)),
            ("  finalized", sum(a.status == Assessment.FINALIZED for a in assessments)),
            ("  public", sum(a.data_policy == Assessment.PUBLIC for a in assessments)),
            ("  checked out", sum(a.checkout_id is not None for a in assessments)),
            ("  without MA", sum(a.management_area_id is None for a in assessments)),
            ("  changed since list was made", len(changed)),
            ("Collaborator rows (emails suppressed)", Collaborator.objects.filter(assessment_id__in=a_ids).count()),
            ("  distinct users", Collaborator.objects.filter(assessment_id__in=a_ids).values("user").distinct().count()),
            ("Survey answers", sum(a.n_answers for a in assessments)),
            ("Change log rows", sum(a.n_changes for a in assessments)),
            ("Flags", sum(a.n_flags for a in assessments)),
            ("MAs to delete", len(plan["delete_mas"])),
            ("  of listed assessments", len(plan["listed_mas"])),
            ("  with no assessment", len(plan["delete_mas"] - plan["listed_mas"])),
            ("MAs with no assessment kept (referenced)", len(plan["orphans"] - plan["delete_mas"])),
            ("Links on kept MAs to be emptied", len(plan["nulled_links"])),
            ("Files to delete", sum(not f[3] for f in plan["files"])),
            ("Files kept (shared with kept record)", sum(bool(f[3]) for f in plan["files"])),
        ]

    def write_report(self, path, plan, changed):
        wb = Workbook()
        sheets = []

        def sheet(title, header, rows):
            ws = wb.active if not sheets else wb.create_sheet()
            ws.title = title[:31]
            ws.append(header)
            for r in rows:
                ws.append(list(r))
            # openpyxl treats any string starting with "=" as a formula; keep DB text as text
            for row in ws.iter_rows():
                for c in row:
                    if c.data_type == "f":
                        c.data_type = "s"
            sheets.append(ws)

        sheet("Summary", ["Item", "Count"], self.summary_rows(plan, changed))

        # 1. assessments to delete
        def attention(a):
            flags = []
            if a.status == Assessment.FINALIZED:
                flags.append("FINALIZED")
            if a.data_policy == Assessment.PUBLIC:
                flags.append("PUBLIC")
            if a.checkout_id:
                flags.append("CHECKED OUT")
            if a.pk in changed:
                flags.append("CHANGED SINCE LIST")
            return ", ".join(flags)

        rows = []
        for a in sorted(
            plan["assessments"],
            key=lambda a: (
                a.status != Assessment.FINALIZED,
                a.data_policy != Assessment.PUBLIC,
                a.checkout_id is None,
                a.pk,
            ),
        ):
            pr = a.person_responsible
            rows.append((
                a.pk, a.name, assessment_status(a), assessment_policy(a), attention(a),
                changed.get(a.pk), fmt_user(a.checkout), a.created_on.date(),
                fmt_user(a.created_by), a.updated_on.date(), fmt_user(pr),
                pr.email if pr else None,
                a.organization.name if a.organization else None, fmt_collaborators(a),
                a.n_answers, a.n_flags, a.n_changes, a.management_area_id,
                str(a.management_area) if a.management_area else None,
                a.management_plan_file.name or None,
            ))
        sheet(
            "Assessments to delete",
            ["id", "name", "status", "data policy", "attention", "change since list",
             "checked out by", "created on", "created by", "updated on",
             "person responsible", "person responsible email", "organization",
             "collaborators", "answers", "flags", "change log rows", "ma id", "ma",
             "management plan file"],
            rows,
        )

        # 2. kept MAs whose parent/containedby links will be emptied
        mas = self.ma_lookup(
            {pk for pk, _, _ in plan["nulled_links"]}
            | {t for _, _, t in plan["nulled_links"]}
            | plan["delete_mas"]
            | plan["orphans"]
        )
        rows = []
        for kept_pk, field, target_pk in sorted(plan["nulled_links"]):
            k, t = mas[kept_pk], mas[target_pk]
            ka = getattr(k, "assessment", None)
            ta = getattr(t, "assessment", None)
            rows.append((
                k.pk, str(k), fmt_user(k.created_by),
                ka.pk if ka else None, ka.name if ka else None,
                assessment_status(ka) if ka else None, assessment_policy(ka) if ka else None,
                fmt_user(ka.person_responsible) if ka else None,
                fmt_collaborators(ka) if ka else None,
                field, t.pk, str(t), fmt_user(t.created_by),
                ta.pk if ta else None, ta.name if ta else None,
                fmt_user(ta.person_responsible) if ta else None,
            ))
        sheet(
            "Kept MAs losing links",
            ["kept ma id", "kept ma", "kept ma created by", "kept assessment id",
             "kept assessment", "kept assessment status", "kept assessment policy",
             "kept assessment person responsible", "kept assessment collaborators",
             "link emptied", "deleted ma id", "deleted ma", "deleted ma created by",
             "deleted assessment id", "deleted assessment",
             "deleted assessment person responsible"],
            rows,
        )

        # 3. MAs: deleted, and orphans kept because they are referenced
        test_re = re.compile(TEST_LIKE_RE, re.I)
        rows = []
        for pk in sorted(plan["delete_mas"] | plan["orphans"]):
            m = mas[pk]
            if pk in plan["listed_mas"]:
                action = DELETE_LISTED
            elif pk in plan["delete_mas"]:
                action = DELETE_ORPHAN
            else:
                action = KEEP_REFERENCED
            a = getattr(m, "assessment", None)
            rows.append((
                pk, action, m.name, ", ".join(c.code for c in m.countries),
                m.created_on.date(), fmt_user(m.created_by), m.version_date,
                bool(test_re.search(m.name)), a.pk if a else None, a.name if a else None,
                m.parent_id, m.containedby_id, m.polygon is not None, m.point is not None,
                m.n_zones,
                ", ".join(f.name for f in (m.import_file, m.map_image) if f),
                ", ".join(str(x) for x in sorted(plan["kept_orphan_refs"].get(pk, []))),
            ))
        sheet(
            "Management areas",
            ["ma id", "action", "name", "countries", "created on", "created by",
             "version date", "test-like name", "listed assessment id",
             "listed assessment", "parent id", "containedby id", "has polygon",
             "has point", "zones", "files", "referenced by kept mas"],
            rows,
        )

        # 4. heuristic: assessments not on the list that look like tests
        listed = [a.pk for a in plan["assessments"]]
        # rewrite(False): match the base name columns, not just the active language's
        others = (
            Assessment.objects.rewrite(False)
            .exclude(pk__in=listed)
            .filter(
                Q(name__iregex=TEST_LIKE_RE)
                | Q(management_area__name__iregex=TEST_LIKE_RE)
                | Q(status=Assessment.TEST)
            )
            .select_related("person_responsible", "management_area")
            .prefetch_related("collaborators__user")
            .order_by("pk")
        )
        sheet(
            "Other test-like (not deleted)",
            ["id", "name", "status", "data policy", "created on", "person responsible",
             "collaborators", "ma id", "ma"],
            [(
                a.pk, a.name, assessment_status(a), assessment_policy(a),
                a.created_on.date(), fmt_user(a.person_responsible),
                fmt_collaborators(a), a.management_area_id,
                str(a.management_area) if a.management_area else None,
            ) for a in others],
        )

        # 5. files
        sheet(
            "Files",
            ["field", "object id", "path", "action", "also used by kept record"],
            [(f, pk, p, "keep" if shared else "delete", shared)
             for f, pk, p, shared in plan["files"]],
        )

        for ws in sheets:
            for c in ws[1]:
                c.font = Font(bold=True)
            ws.freeze_panes = "B2"
            ws.auto_filter.ref = ws.dimensions
            for i, col in enumerate(ws.iter_cols(values_only=True), 1):
                w = max((len(str(v)) for v in col if v is not None), default=8)
                ws.column_dimensions[get_column_letter(i)].width = min(max(w + 2, 8), 60)
        wb.save(path)

    def ma_lookup(self, pks):
        return {
            m.pk: m
            for m in ManagementArea.objects.filter(pk__in=pks)
            .select_related(
                "created_by",
                "assessment__person_responsible",
            )
            .prefetch_related("assessment__collaborators__user")
            .annotate(n_zones=Count("ma_zones"))
        }

    # ---------- delete ----------

    def delete(self, plan):
        assessment_ids = [a.pk for a in plan["assessments"]]
        file_paths = [p for _, _, p, shared in plan["files"] if not shared]

        for receiver, sender in SUPPRESSED_RECEIVERS:
            if not post_delete.disconnect(receiver, sender=sender):
                raise CommandError(f"Could not disconnect {receiver.__name__}")
        try:
            # Backstop: anything that still tries to email goes to locmem, not SMTP.
            with override_settings(
                EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
            ), transaction.atomic():
                _, a_counts = Assessment.objects.filter(pk__in=assessment_ids).delete()
                _, ma_counts = ManagementArea.objects.filter(
                    pk__in=plan["delete_mas"]
                ).delete()
                transaction.on_commit(lambda: self.delete_files(file_paths))
        finally:
            for receiver, sender in SUPPRESSED_RECEIVERS:
                post_delete.connect(receiver, sender=sender)

        from django.core import mail

        outbox = getattr(mail, "outbox", [])
        if outbox:
            self.stdout.write(self.style.WARNING(f"{len(outbox)} emails suppressed"))

        self.stdout.write(self.style.SUCCESS("Deleted:"))
        totals = defaultdict(int)
        for counts in (a_counts, ma_counts):
            for model, n in counts.items():
                totals[model] += n
        for model, n in sorted(totals.items()):
            self.stdout.write(f"  {model}: {n}")
        self.stdout.write(f"  Kept MA links emptied: {len(plan['nulled_links'])}")

    def delete_files(self, paths):
        failed = []
        for path in paths:
            try:
                if default_storage.exists(path):
                    default_storage.delete(path)
                    self.stdout.write(f"  deleted file {path}")
                else:
                    self.stdout.write(f"  file not found (skipped) {path}")
            except Exception as e:  # keep going; DB change is already committed
                failed.append(path)
                self.stderr.write(f"  failed to delete file {path}: {e}")
        if failed:
            self.stderr.write(self.style.ERROR(f"{len(failed)} files not deleted"))

    # ---------- main ----------

    def handle(self, *args, **options):
        if options["orphans_created_before"] and not options["orphan_mas"]:
            raise CommandError("--orphans-created-before requires --orphan-mas")
        ids, rows = self.read_input(options)
        if not ids:
            raise CommandError("No assessment IDs given")
        assessments = Assessment.objects.filter(pk__in=ids)
        changed = self.verify(ids, rows, assessments)

        plan = self.build_plan(
            ids, options["orphan_mas"], options["orphans_created_before"]
        )

        for label, n in self.summary_rows(plan, changed):
            self.stdout.write(f"{label}: {n}")
        for pk, note in sorted(changed.items()):
            self.stdout.write(self.style.WARNING(f"  assessment {pk} {note}"))

        if options["report"]:
            self.write_report(options["report"], plan, changed)
            self.stdout.write(self.style.SUCCESS(f"Report written to {options['report']}"))

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: nothing deleted"))
            return

        self.delete(plan)
