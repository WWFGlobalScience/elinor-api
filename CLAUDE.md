# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Elinor API: Django 5.2 + DRF + PostGIS backend for WWF's Elinor marine/terrestrial protected-area management assessments. The Nuxt frontend lives in the sibling `../elinor-front` repo. Note that the parent `../CLAUDE.md` is partly out of date for this repo: task automation is now `make` (not Fabric `fab`), and the stack is Django 5.2 / Python 3.13 / psycopg 3.

## Commands

Everything runs in Docker (`elinor_api` + `elinor_db` PostGIS 16 containers). `src/` is bind-mounted into the container at `/var/projects/webapp`, so host edits apply immediately. Run these from the repo root:

```bash
make up / make down          # start / stop containers (down -v via `make downnocache` wipes the DB volume)
make build / make buildnocache  # rebuild image (required after changing requirements.txt or Dockerfile)
make runserver               # Django dev server on http://localhost:8082
make runserverplus           # gunicorn instead, closer to prod
make migrate
make shell / make shellplus  # bash / Django shell_plus inside the api container
make logs
make dbrestore / make dbbackup   # restore/backup the *local* S3 dump
make freshinstall            # downnocache, buildnocache, up, dbrestore, migrate
```

No `makemigrations` target exists. For any other manage.py command, use `docker compose exec elinor_api python manage.py <cmd>`, for example:
- `makemigrations`
- `dbrestore dev` or `dbrestore prod` restores a deployed env's dump locally. The Makefile db targets only use `local`. `local` is the shared dev dataset and is exempt from S3 age-based cleanup, so `make dbbackup` overwrites what every developer restores. Flags: `-f` force, `-n` skip the S3 download.
- `update_translation_fields`, run after registering new translatable fields.
- `find_null_geometries`, `test_collaborator_emails`, `test_email_verification`: diagnostic commands in `src/tools/management/commands/`. Despite the names, these are not a test suite.

There are no automated tests and no linter or formatter config. Follow PEP 8. The DB is exposed on host port 5433. `.env` (see README) must set `ENV` because settings call `os.environ.get("ENV").lower()`; `ENV` also prefixes S3 media paths (`AWS_LOCATION`).

## Architecture

Single Django app `api` (in `src/api/`), with project config in `src/app/`. The REST API is mounted at `/v2/` (`api/urls.py`, via a custom `ElinorDefaultRouter`). Auth is dj-rest-auth + allauth under `/rest-auth/` (token + session, email verification mandatory, login by email or username).

### Assessment-centric permission model
This model is the core cross-cutting concept. Read it before touching any viewset.
- `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES` is `DefaultPermission`, which **denies everything**. Every viewset must set `permission_classes` explicitly (see `api/permissions.py`).
- Each assessment-related model declares a class attribute `assessment_lookup`. It is `""` on `Assessment` itself, and the FK name (e.g. `"assessment"`) on `Collaborator`, `SurveyAnswer`, `AssessmentChange`, `AssessmentFlag`, and `ManagementArea` (via the reverse one-to-one). Two generic helpers rely on it:
  - `get_assessment_related_queryset(user, model)` in `api/utils/assessment.py` controls visibility: superuser sees all; others see finalized+public assessments plus any assessment they collaborate on.
  - `AssessmentReadOnlyOrAuthenticatedUserPermission` controls writes. It resolves the parent assessment via `assessment_lookup` and enforces three rules. First, **checkout**: if `assessment.checkout` is another user, the write is rejected. Second, collaborator role: `Collaborator.ADMIN` (70) > `CONTRIBUTOR` (40) > `OBSERVER` (10); `is_collector` means contributor or above. Third, **finalized** assessments can only have `PUBLISHED_MODIFIABLE_FIELDS` changed. On POST it builds an unsaved model instance from the serializer to find the assessment, so m2m fields are stripped first.
- New models attached to an assessment need `assessment_lookup`, the queryset helper, and this permission class.

### Validation lives on models
`BaseAPISerializer.validate()` instantiates the model and calls `full_clean()`, converting Django `ValidationError`s to DRF format. `Assessment.save()` also calls `full_clean()`. Publishing rules are in `Assessment.clean()` when `status == FINALIZED`: no null fields, ≥1 attribute, all required questions answered, and the management area has a point or polygon. Finalizing also stamps `published_version` with the latest `AssessmentVersion`. Status/role/policy constants are integers where ordering matters (`is_finalized` is `status <= FINALIZED`, i.e. FINALIZED=10 < TEST=80 < NOT_FINALIZED=90).

`BaseModel` (`api/models/base.py`) adds created/updated audit fields and overrides `validate_unique` to also check uniqueness against untranslated base fields (modeltranslation).

### Side effects
- `AssessmentViewSet.perform_create/perform_update`: auto-adds required `Attribute`s, makes the creator an ADMIN collaborator, logs `AssessmentChange` on status/data_policy changes, and emails admins on checkout/check-in.
- `api/signals.py`: auto-creates user `Profile`. After save, it moves uploaded files to `<Model>/<pk>/<filename>` in S3 storage and deletes them on model delete. It also sends emails on `AssessmentFlag` creation and on Collaborator add, role change, and remove (templates in `api/templates/emails/`).

### Scoring and survey
Likert answers are 0–3 (`api/models/survey.py`). `attribute_scores()` normalizes each attribute to 0–`ATTRIBUTE_NORMALIZER` (10). `assessment_score()` averages attributes to 0–100. Null choices are excluded. Questions belong to `Attribute`s, and `Attribute.required=True` attributes are always included.

### XLSX round-trip and reports
- `GET/POST /v2/assessments/{id}/xlsx/` (`api/ingest/xlsx.py`, `AssessmentXLSX`) downloads or uploads survey answers as Excel (a zip containing one file is also accepted). POST supports `dryrun`. Errors come back as a dict of `{key: {level, message, data}}` using constants in `api/ingest/__init__.py`.
- `/v2/reports/assessments/` (`api/resources/reports/`) is read-only and has `json`, `geojson`, `csv`, and `csv_detail` actions. CSV streaming is in `api/reports/`.

### Geometry
`ManagementArea.polygon` is a MultiPolygonField (SRID 4326). `MultiPolygonFieldValidated` in `api/resources/base.py` strictly validates GeoJSON MultiPolygon nesting. See `../MULTIPOLYGON_FIXES.md` for background.

### Translations
`django-modeltranslation` is configured in `api/translation.py`, which creates `<field>_<lang>` columns. Adding a language takes four steps: add it to `settings.LANGUAGES` and `MODELTRANSLATION_FALLBACK_LANGUAGES`, run makemigrations and migrate, click "Sync languages" in admin (`/admin/api/activelanguage/`), then mark it active. Adding a translated field takes four steps: register it in `translation.py`, run makemigrations and migrate, run `update_translation_fields`, then make the admin use `TranslationAdmin`.

## Deployment

GitHub Actions (`.github/workflows/deploy.yml`) builds the image and pushes it to GHCR, then deploys to Elastic Beanstalk. A push to `dev` deploys to `elinor-dev`. A `vX.Y.Z` tag deploys to `elinor-prod`. Branch flow: feature branch → PR to `dev` → merge `dev` into `main` → tag. The EB postdeploy hook (`.platform/hooks/postdeploy/99_delayed_commands.sh`) runs `dbbackup`, `collectstatic`, and `migrate --noinput`, then restarts supervisor, so migrations ship automatically. Prod runs nginx + gunicorn under supervisor (`config/`).

`dbbackup-mirror.yml` copies S3 DB backups to Azure daily and commits a log line to `.github/dbbackup-mirror/log.md`. Those `chore: record dbbackup mirror run [skip ci]` commits are automated noise.
