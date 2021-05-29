from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from .base import LIKERT_CHOICES, BaseModel, ManagementArea, ProtectedArea


class Assessment(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Collaborator(BaseModel):
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

    def __str__(self):
        return f"{self.assessment} {self.user}"


class AssessmentPeriod(BaseModel):
    OPEN = 90
    TEST = 80
    PUBLISHED = 10
    STATUSES = ((OPEN, _("open")), (TEST, _("test")), (PUBLISHED, _("published")))

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

    status = models.PositiveSmallIntegerField(choices=STATUSES, default=OPEN)
    data_policy = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC
    )
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT, related_name="assessment_periods"
    )
    person_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="collaborator_aps"
    )
    person_responsible_role = models.PositiveSmallIntegerField(
        choices=PERSON_RESPONSIBLE_ROLES
    )
    year = models.PositiveSmallIntegerField()
    management_area = models.ForeignKey(
        ManagementArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ma_assessments",
    )
    count_manager = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("MA manager count")
    )
    count_personnel = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("MA personnel count")
    )
    count_government = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("government personnel count")
    )
    count_committee = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("local community/indigenous committee count")
    )
    count_community = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("community leader count")
    )
    specific_unit = models.BooleanField(default=False)
    focal_area = models.TextField(blank=True)
    protected_area = models.ForeignKey(ProtectedArea, on_delete=models.SET_NULL, blank=True, null=True)
    consent_given = models.BooleanField(default=False)
    management_plan_file = models.FileField(upload_to="upload", blank=True, null=True)

    # Survey questions - need to move to separate model if permissions are different
    stakeholder_defined_rights = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do local stakeholders have clearly defined rights to the natural resources found inside the MA?"
        ),
    )
    vulnerable_defined_rights = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do women or other vulnerable groups living in the local community have clearly defined rights to natural "
            "resources within the MA?"
        ),
    )
    legislation_exists = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Is there legislation in place to enable resource management by local communities?"
        ),
    )
    exercise_rights = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are local stakeholders able to exercise their rights to natural resources?"
        ),
    )
    benefits_shared = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Is there an effective strategy or guideline for ensuring benefits from the MA are shared equitably among "
            "local stakeholders?"
        ),
    )
    stakeholder_agency = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are stakeholders affected by the rules able to play a role in making changes to the rules?"
        ),
    )
    governance_accountable = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are those responsible for governance of the MA held to account if they do not perform their role?"
        ),
    )
    timely_information = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do stakeholders receive information from MA authorities in a timely manner?"
        ),
    )
    penalties_fair = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are the penalties for breaking resource use rules equal to the size of the offence?"
        ),
    )
    penalties_frequency = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "How often are the penalties for breaking resource use rules administered?"
        ),
    )
    multiple_knowledge_ecological = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do planning and management processes draw on multiple knowledge sources (scientific, experiential, "
            "local, and traditional knowledge) for monitoring the ecological impacts of the MA?"
        ),
    )
    multiple_knowledge_social = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do planning and management processes draw on multiple knowledge sources (scientific, experiential, "
            "local, and traditional knowledge) for monitoring the social impacts of the MA?"
        ),
    )
    conflict_resolution_access = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do stakeholders have access to effective conflict resolution mechanisms?"
        ),
    )
    management_levels_cohesive = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do different levels of management exist within the MA that function as a cohesive unit?"
        ),
    )
    supportive_networks = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do networks exist that develop social relations and support mutual learning among stakeholders?"
        ),
    )
    regulations_exist = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are appropriate regulations in place to control natural resource based activities in the MA?"
        ),
    )
    management_capacity = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do those responsible for managing the MA (e.g., staff/community associations/ management group) have the "
            "capacity to enforce the rules and regulations?"
        ),
    )
    boundary_known = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the boundary known by all stakeholder groups?"),
    )
    boundary_defined = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the boundary clearly defined?"),
    )
    management_plan = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Is there a management plan for the MA and is it being implemented?"
        ),
    )
    outcomes_achieved_ecological = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "To what extent do you feel the ecological outcomes are being achieved?"
        ),
    )
    outcomes_achieved_social = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "To what extent do you feel the social outcomes are being achieved?"
        ),
    )
    multiple_knowledge_integrated = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do those responsible for managing the MA integrate different types of knowledge into management decisions?"
        ),
    )
    monitoring_used = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are the results of monitoring, research and evaluation routinely incorporated into decisions and/or "
            "policies related to MA management?"
        ),
    )
    sufficient_staff = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are there enough people (e.g., staff) employed to manage the MA?"
        ),
    )
    staff_capacity = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do personnel have sufficient capacity to fulfill management objectives (e.g., enough information about "
            "the MA and adequate skills)?"
        ),
    )
    sufficient_budget = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the current budget sufficient?"),
    )
    budget_secure = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the budget secure?"),
    )
    sufficient_equipment = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is equipment sufficient for management needs?"),
    )
    climatechange_assessed = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Have observed and anticipated changes in climate, and their associated impacts on people and nature, "
            "been assessed, understood, and documented?"
        ),
    )
    climatechange_incorporated = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do MA management plans consciously incorporate measures to manage current and anticipated changes in "
            "climate and their social and ecological impacts?"
        ),
    )
    climatechange_monitored = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are systems in place to monitor and document changes in climate change and increased weather variability "
            "and their impacts on people and nature?"
        ),
    )

    class Meta:
        unique_together = ("assessment", "management_area", "year")

    @property
    def is_published(self):
        return self.status <= self.PUBLISHED

    def __str__(self):
        return f"{self.assessment.name} {self.year}"


class AssessmentPeriodChange(BaseModel):
    SUBMIT = 1
    UNSUBMIT = 2
    DATA_POLICY_PUBLIC = 5
    DATA_POLICY_PRIVATE = 6
    EDIT = 10

    EVENT_TYPES = (
        (SUBMIT, _("submit Assessment Period")),
        (UNSUBMIT, _("re-open Assessment Period")),
        (DATA_POLICY_PUBLIC, _("make Assessment Period public")),
        (DATA_POLICY_PRIVATE, _("make Assessment Period private")),
        (EDIT, _("edit Assessment Period")),
    )

    assessment_period = models.ForeignKey(
        AssessmentPeriod,
        related_name="assessment_period_changes",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="user_ap_changes",
        on_delete=models.CASCADE,
    )
    event_on = models.DateTimeField(auto_now_add=True)
    event_type = models.PositiveSmallIntegerField(choices=EVENT_TYPES)

    def __str__(self):
        return f"{self.event_on} {self.assessment_period} {self.event_type}"
