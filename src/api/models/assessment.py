from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from .base import (
    LIKERT_CHOICES,
    AssessmentVersion,
    Attribute,
    BaseModel,
    Organization,
)
from .management import ManagementArea


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

    PERSON_RESPONSIBLE = 10
    PERSON_RESPONSIBLE_AND_EXTERNAL = 20
    INTERVIEWS = 30
    COMBINATION_COLLECTION_METHOD = 40
    OTHER_COLLECTION_METHOD = 50
    COLLECTION_METHOD_CHOICES = (
        (
            PERSON_RESPONSIBLE,
            _(
                "Through knowledge of the person(s) responsible for filling out assessment"
            ),
        ),
        (
            PERSON_RESPONSIBLE_AND_EXTERNAL,
            _(
                "Through knowledge of the person(s) responsible for filling our assessment and acquired external input from informal conversations and secondary documents"
            ),
        ),
        (INTERVIEWS, _("Through semi-structured interviews and/or focus groups")),
        (COMBINATION_COLLECTION_METHOD, _("A combination of the above")),
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
        choices=DATA_POLICIES, default=PUBLIC
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

        answered = self.surveyanswerlikert_set.filter(
            Q(question__attribute__in=self.attributes.all())
            | Q(question__attribute__required=True)
        ).count()
        total = self.required_questions.count()
        if total < 1:
            total = 1
        self._percent_complete = round(100 * (answered / total))
        return self._percent_complete

    def clean(self):
        # Publishing checks
        if self.status == self.FINALIZED:
            #  Disallow publishing if any fields on the model itself are null.
            #  Does not check non-nullable fields with default values or char/text fields with empty strings.
            nullfields = []
            for field in self._meta.get_fields():
                if not field.is_relation:
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

            # Ensure at least one attribute is associated with assessment
            attributes = self.attributes.all()
            if attributes.count() < 1:
                raise ValidationError(
                    "May not be published without at least one associated attribute"
                )

            # Ensure all questions for attributes associated with assessment are answered
            #  Doublecheck required attributes even though they are automatically added by admin and viewset
            answered_question_ids = self.surveyanswerlikert_set.values_list(
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


class SurveyQuestion(BaseModel):
    attribute = models.ForeignKey(
        Attribute, related_name="attribute_questions", on_delete=models.PROTECT
    )
    key = models.CharField(
        max_length=255, unique=True
    )  # migration: populate with current field name
    number = models.PositiveSmallIntegerField()
    text = models.TextField()  # migration: populate with current verbose_name
    rationale = models.TextField()
    information = models.TextField()
    guidance = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.key}"


class SurveyQuestionLikert(SurveyQuestion):
    dontknow_10 = models.TextField()
    poor_20 = models.TextField()
    average_30 = models.TextField()
    good_40 = models.TextField()
    excellent_50 = models.TextField()

    class Meta:
        ordering = ["attribute", "number"]
        verbose_name = "Likert survey question"


class SurveyAnswer(BaseModel):
    assessment_lookup = "assessment"

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class SurveyAnswerLikert(SurveyAnswer):
    question = models.ForeignKey(
        SurveyQuestionLikert,
        related_name="questionlikert_answers",
        on_delete=models.PROTECT,
    )
    choice = models.PositiveSmallIntegerField(choices=LIKERT_CHOICES)
    explanation = models.TextField(blank=True)

    class Meta:
        unique_together = ("assessment", "question")
        verbose_name = "Likert survey answer"

    def __str__(self):
        return f"{self.assessment} {self.question}"
