from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modeltranslation.fields import TranslationField

from .base import (
    AssessmentVersion,
    Attribute,
    BaseModel,
    Organization,
)
from .management import ManagementArea
from .survey import SurveyQuestionLikert


class Assessment(BaseModel):
    assessment_lookup = ""

    ALLOWED_PUBLISHED_NULLFIELDS = ("created_by", "updated_by")

    NOT_FINALIZED = 90
    TEST = 80
    FINALIZED = 10
    STATUSES = (
        (NOT_FINALIZED, _("not finalized")),
        (TEST, _("test")),
        (FINALIZED, _("finalized")),
    )

    PRIVATE = 10
    PUBLIC = 90
    DATA_POLICIES = ((PRIVATE, _("private")), (PUBLIC, _("public")))

    NONPROFIT = 10
    MANAGER = 20
    PERSONNEL = 30
    GOVERNMENT = 40
    COMMITTEE = 50
    COMMUNITY = 60
    PERSON_RESPONSIBLE_ROLES = (
        (NONPROFIT, _("nonprofit staff")),
        (MANAGER, _("management area manager")),
        (PERSONNEL, _("management area personnel")),
        (GOVERNMENT, _("government personnel")),
        (COMMITTEE, _("members of local community / indigenous committees")),
        (COMMUNITY, _("community leaders / representatives")),
    )

    DESKBASED = 10
    FIELDBASED = 30
    OTHER_COLLECTION_METHOD = 50
    COLLECTION_METHOD_CHOICES = (
        (DESKBASED, _("Desk-based assessment")),
        (FIELDBASED, _("Field-based assessment")),
        (OTHER_COLLECTION_METHOD, _("Other (please provide details below)")),
    )

    published_version = models.ForeignKey(
        AssessmentVersion, blank=True, null=True, on_delete=models.PROTECT
    )
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, blank=True, null=True
    )
    status = models.PositiveSmallIntegerField(choices=STATUSES, default=NOT_FINALIZED)
    data_policy = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PRIVATE
    )
    attributes = models.ManyToManyField(Attribute, blank=True)
    person_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="collaborator_aps",
    )
    person_responsible_role = models.PositiveSmallIntegerField(
        choices=PERSON_RESPONSIBLE_ROLES,
        null=True,
        blank=True,
    )
    person_responsible_role_other = models.CharField(max_length=255, blank=True)
    year = models.PositiveSmallIntegerField()
    management_area = models.OneToOneField(
        ManagementArea,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )
    count_community = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("local community leader count")
    )
    count_ngo = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("NGO personnel count")
    )
    count_academic = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("academic personnel count")
    )
    count_government = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("government personnel count")
    )
    count_private = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("private sector personnel count")
    )
    count_indigenous = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("indigenous leader count")
    )
    count_gender_female = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("female count")
    )
    count_gender_male = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("male count")
    )
    count_gender_nonbinary = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("non-binary count")
    )
    count_gender_prefer_not_say = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("prefer not to declare gender count")
    )
    consent_given = models.BooleanField(default=False)
    consent_given_written = models.BooleanField(default=False)
    management_plan_file = models.FileField(upload_to="upload", blank=True, null=True)
    collection_method = models.PositiveSmallIntegerField(
        choices=COLLECTION_METHOD_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Please choose which option best describes how information for this assessment was collected"
        ),
    )
    collection_method_text = models.TextField(blank=True)
    strengths_explanation = models.TextField(blank=True)
    needs_explanation = models.TextField(blank=True)
    context = models.TextField(blank=True)
    checkout = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="checked_out_assessments",
    )

    @property
    def required_questions(self):
        if hasattr(self, "_required_questions"):
            return self._required_questions

        self._required_questions = SurveyQuestionLikert.objects.filter(
            Q(attribute__in=self.attributes.all()) | Q(attribute__required=True)
        )
        return self._required_questions

    @property
    def percent_complete(self):
        if hasattr(self, "_percent_complete"):
            return self._percent_complete

        answered = self.survey_answer_likerts.filter(
            Q(question__attribute__in=self.attributes.all())
            | Q(question__attribute__required=True)
        ).count()
        total = self.required_questions.count()
        if total < 1:
            total = 1
        self._percent_complete = round(100 * (answered / total))
        return self._percent_complete

    def _check_nulls(self):
        #  Disallow publishing if any fields on the model itself are null.
        #  Does not check non-nullable fields with default values or char/text fields with empty strings.
        nullfields = []
        for field in self._meta.get_fields():
            if (
                not (field.is_relation or isinstance(field, TranslationField))
                or field.one_to_one
            ):
                value = getattr(self, field.name)
                if (
                    value is None
                    and field.name not in self.ALLOWED_PUBLISHED_NULLFIELDS
                ):
                    nullfields.append(field.name)
        if nullfields:
            raise ValidationError(
                {f: _("May not be published unanswered") for f in nullfields}
            )

    def _check_attributes(self):
        # Ensure at least one attribute is associated with assessment
        attributes = self.attributes.all()
        if attributes.count() < 1:
            raise ValidationError(
                "May not be published without at least one associated attribute"
            )

    def _check_questions(self):
        # Ensure all questions for attributes associated with assessment are answered
        #  Doublecheck required attributes even though they are automatically added by admin and viewset
        answered_question_ids = self.survey_answer_likerts.values_list(
            "question", flat=True
        )
        answered_questions = SurveyQuestionLikert.objects.filter(
            pk__in=answered_question_ids
        )
        missing_questions = self.required_questions.difference(answered_questions)
        if missing_questions:
            questions_string = ",".join([q.key for q in missing_questions])
            raise ValidationError(
                f"May not be published without answers to these questions: {questions_string}"
            )

    def clean(self):
        # Publishing checks
        if self.status == self.FINALIZED:
            self._check_nulls()
            self._check_attributes()
            self._check_questions()

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == self.FINALIZED:
            latest_version = AssessmentVersion.objects.order_by(
                "-year", "-major_version"
            ).first()
            self.published_version = latest_version
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("management_area", "year")
        ordering = ["name", "year"]

    @property
    def is_finalized(self):
        return self.status <= self.FINALIZED

    def __str__(self):
        return f"{self.name} {self.organization} {self.year}"


class Collaborator(BaseModel):
    assessment_lookup = "assessment"

    ADMIN = 70
    CONTRIBUTOR = 40
    OBSERVER = 10
    ROLES = (
        (ADMIN, _("admin")),
        (CONTRIBUTOR, _("contributor")),
        (OBSERVER, _("observer")),
    )

    assessment = models.ForeignKey(
        Assessment, related_name="collaborators", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="user_assessments",
        on_delete=models.CASCADE,
    )
    role = models.PositiveSmallIntegerField(choices=ROLES)

    @property
    def is_collector(self):
        return self.role >= self.CONTRIBUTOR

    @property
    def is_admin(self):
        return self.role >= self.ADMIN

    class Meta:
        unique_together = ("assessment", "user")

    def __str__(self):
        return f"{self.assessment} {self.user}"


class AssessmentChange(BaseModel):
    assessment_lookup = "assessment"

    SUBMIT = 1
    UNSUBMIT = 2
    DATA_POLICY_PUBLIC = 5
    DATA_POLICY_PRIVATE = 6
    EDIT = 10

    EVENT_TYPES = (
        (SUBMIT, _("submit Assessment")),
        (UNSUBMIT, _("re-open Assessment")),
        (DATA_POLICY_PUBLIC, _("make Assessment public")),
        (DATA_POLICY_PRIVATE, _("make Assessment private")),
        (EDIT, _("edit Assessment")),
    )

    assessment = models.ForeignKey(
        Assessment,
        related_name="assessment_changes",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="user_assessment_changes",
        on_delete=models.CASCADE,
    )
    event_on = models.DateTimeField(auto_now_add=True)
    event_type = models.PositiveSmallIntegerField(choices=EVENT_TYPES)

    def __str__(self):
        return f"{self.event_on} {self.assessment} {self.event_type}"


class AssessmentFlag(BaseModel):
    assessment_lookup = "assessment"

    INAPPROPRIATE = "inappropriate"
    PERSONAL = "personal"
    INACCURATE = "inaccurate"
    FLAG_TYPES = (
        (INAPPROPRIATE, _("inappropriate language or content")),
        (PERSONAL, _("personal information")),
        (INACCURATE, _("inaccurate details")),
    )

    assessment = models.ForeignKey(
        Assessment, related_name="assessment_flags", on_delete=models.CASCADE
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="user_assessment_flags",
        on_delete=models.CASCADE,
    )
    datetime_resolved = models.DateTimeField(null=True, blank=True)
    flag_type = models.CharField(max_length=20, choices=FLAG_TYPES, blank=True)
    flag_type_other = models.CharField(max_length=255, blank=True)
    explanation = models.TextField()

    def clean(self):
        if self.flag_type == "" and self.flag_type_other == "":
            raise ValidationError(
                "Either flag_type or flag_type_other must be specified"
            )
        if self.flag_type != "" and self.flag_type_other != "":
            raise ValidationError(
                "Only one of flag_type and flag_type_other can be specified, not both"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["created_on", "assessment", "reporter__username"]

    def __str__(self):
        return f"{self.assessment.name} {self.reporter}"
