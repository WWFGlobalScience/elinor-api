from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from .base import LIKERT_CHOICES, BaseModel, Organization
from .management import ManagementArea


class Assessment(BaseModel):
    assessment_lookup = ""

    ALLOWED_PUBLISHED_NULLFIELDS = ("created_by", "updated_by")

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

    PERSON_RESPONSIBLE = 10
    PERSON_RESPONSIBLE_AND_EXTERNAL = 20
    INTERVIEWS = 30
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
                "Through knowledge of the person(s) responsible for filling our assessment  and acquired external input from informal conversations and secondary documents"
            ),
        ),
        (INTERVIEWS, _("Through semi-structured interviews and/or focus groups")),
    )

    name = models.CharField(max_length=255)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, blank=True, null=True
    )
    status = models.PositiveSmallIntegerField(choices=STATUSES, default=OPEN)
    data_policy = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC
    )
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

    stakeholder_harvest_rights = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are there formal or informal rules that clearly define the rights "
            "of local stakeholders to harvest resources within the MA?"
        ),
    )
    stakeholder_harvest_rights_text = models.TextField(blank=True)
    stakeholder_develop_rules = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are there formal or informal rules that clearly define the rights "
            "of local stakeholders to develop rules for the use of resources within the MA?"
        ),
    )
    stakeholder_develop_rules_text = models.TextField(blank=True)
    stakeholder_exclude_others = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are there formal or informal rules that clearly define the rights "
            "of local stakeholders to exclude other groups from harvesting resources within the MA?"
        ),
    )
    stakeholder_exclude_others_text = models.TextField(blank=True)
    vulnerable_defined_rights = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do women or other vulnerable groups living in the local community have clearly defined rights to natural "
            "resources within the MA?"
        ),
    )
    vulnerable_defined_rights_text = models.TextField(blank=True)
    legislation_exists = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Is there legislation in place to enable resource management by local communities?"
        ),
    )
    legislation_exists_text = models.TextField(blank=True)
    rights_governance = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are rights to harvest or benefit from resources within the MA related to the contributions "
            "of local stakeholders to the governance of the MA (in terms of time and/or resources contributed)?"
        ),
    )
    rights_governance_text = models.TextField(blank=True)
    exercise_rights = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are local stakeholders able to exercise their rights to natural resources?"
        ),
    )
    exercise_rights_text = models.TextField(blank=True)
    benefits_shared = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Is there an effective strategy or guideline for ensuring benefits from the MA are shared equitably among "
            "local stakeholders?"
        ),
    )
    benefits_shared_text = models.TextField(blank=True)
    stakeholder_agency = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "To what extent are local stakeholders affected by the rules "
            "able to play a role in making changes to the rules?"
        ),
    )
    stakeholder_agency_text = models.TextField(blank=True)
    governance_accountable = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are those responsible for governance of the MA held to account if they do not perform their role?"
        ),
    )
    governance_accountable_text = models.TextField(blank=True)
    timely_information = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do stakeholders receive information from MA authorities in a timely manner?"
        ),
    )
    timely_information_text = models.TextField(blank=True)
    penalties_fair = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Formally, are the penalties for breaking resource use rules equal to the size of the offence?"
        ),
    )
    penalties_fair_text = models.TextField(blank=True)
    penalties_frequency = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "How often are the penalties for breaking resource use rules administered?"
        ),
    )
    penalties_frequency_text = models.TextField(blank=True)
    multiple_knowledge_ecological = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do planning and management processes draw on multiple knowledge sources (scientific, experiential, "
            "local, and traditional knowledge) for monitoring the ecological impacts of the MA?"
        ),
    )
    multiple_knowledge_ecological_text = models.TextField(blank=True)
    multiple_knowledge_social = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do planning and management processes draw on multiple knowledge sources (scientific, experiential, "
            "local, and traditional knowledge) for monitoring the social impacts of the MA?"
        ),
    )
    multiple_knowledge_social_text = models.TextField(blank=True)
    conflict_resolution_access = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do stakeholders have access to effective conflict resolution mechanisms?"
        ),
    )
    conflict_resolution_access_text = models.TextField(blank=True)
    management_levels_cohesive = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do different levels of management exist within the MA that function as a cohesive unit?"
        ),
    )
    management_levels_cohesive_text = models.TextField(blank=True)
    supportive_networks = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do networks exist that develop social relations and support mutual learning among stakeholders?"
        ),
    )
    supportive_networks_text = models.TextField(blank=True)
    regulations_exist = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are appropriate regulations in place to control natural resource based activities in the MA?"
        ),
    )
    regulations_exist_text = models.TextField(blank=True)
    management_capacity = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do those responsible for managing the MA (e.g., staff/community associations/ management group) have the "
            "capacity to enforce the rules and regulations?"
        ),
    )
    management_capacity_text = models.TextField(blank=True)
    boundary_known = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the boundary known by all stakeholder groups?"),
    )
    boundary_known_text = models.TextField(blank=True)
    boundary_defined = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the boundary clearly defined?"),
    )
    boundary_defined_text = models.TextField(blank=True)
    management_plan = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Is there a management plan for the MA and is it being implemented?"
        ),
    )
    management_plan_text = models.TextField(blank=True)
    outcomes_achieved_ecological = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "To what extent do you feel the ecological outcomes are being achieved?"
        ),
    )
    outcomes_achieved_ecological_text = models.TextField(blank=True)
    outcomes_achieved_social = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "To what extent do you feel the social outcomes are being achieved?"
        ),
    )
    outcomes_achieved_social_text = models.TextField(blank=True)
    multiple_knowledge_integrated = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do those responsible for managing the MA integrate different types of knowledge into management decisions?"
        ),
    )
    multiple_knowledge_integrated_text = models.TextField(blank=True)
    monitoring_used = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are the results of monitoring, research and evaluation routinely incorporated into decisions and/or "
            "policies related to MA management?"
        ),
    )
    monitoring_used_text = models.TextField(blank=True)
    sufficient_staff = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Are there enough people employed or engaged to manage the MA?"),
    )
    sufficient_staff_text = models.TextField(blank=True)
    staff_capacity = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Do those responsible for managing the MA have sufficient capacity "
            "(e.g., information and adequate skills) to fulfill management objectives?"
        ),
    )
    staff_capacity_text = models.TextField(blank=True)
    sufficient_budget = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the current budget sufficient?"),
    )
    sufficient_budget_text = models.TextField(blank=True)
    budget_secure = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the budget secure?"),
    )
    budget_secure_text = models.TextField(blank=True)
    sufficient_equipment = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is equipment sufficient for management needs?"),
    )
    sufficient_equipment_text = models.TextField(blank=True)
    climatechange_assessed = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Have observed and anticipated changes in climate, and their associated impacts on people and nature, "
            "been assessed, understood, and documented?"
        ),
    )
    climatechange_assessed_text = models.TextField(blank=True)
    climatechange_incorporated = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Is information on climate change being used to inform strategies "
            "to build resilience to climate change for local stakeholders?"
        ),
    )
    climatechange_incorporated_text = models.TextField(blank=True)
    climatechange_managed = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_("Is the MA consciously managed to adapt to climate change?"),
    )
    climatechange_managed_text = models.TextField(blank=True)
    climatechange_monitored = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES,
        null=True,
        blank=True,
        verbose_name=_(
            "Are systems in place to monitor and document changes in climate change and increased weather variability "
            "and their impacts on people and nature?"
        ),
    )
    climatechange_monitored_text = models.TextField(blank=True)

    # Disallow publishing if any fields are null. Does not check non-nullable fields with default values.
    def clean(self):
        if self.status == self.PUBLISHED:
            nullfields = []
            for field in self._meta.get_fields():
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("management_area", "year")
        ordering = ["name", "year"]

    @property
    def is_published(self):
        return self.status <= self.PUBLISHED

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
