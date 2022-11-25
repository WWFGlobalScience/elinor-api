from django.urls import path, re_path
from .resources.base import (
    health,
    ElinorDefaultRouter,
    assessmentversion,
    AttributeViewSet,
    DocumentViewSet,
    GovernanceTypeViewSet,
    ManagementAuthorityViewSet,
    OrganizationViewSet,
    ProtectedAreaViewSet,
    RegionViewSet,
    StakeholderGroupViewSet,
    SupportSourceViewSet,
    UserViewSet,
)
from .resources.contact import contact_assessment_admins, contact_elinor_admins
from .resources.management import (
    ManagementAreaViewSet,
    ManagementAreaZoneViewSet,
)
from .resources.assessment import (
    AssessmentViewSet,
    AssessmentChangeViewSet,
    AssessmentFlagViewSet,
    CollaboratorViewSet,
    SurveyQuestionLikertViewSet,
    SurveyAnswerLikertViewSet,
)
from .resources.reports.assessment import AssessmentReportView


router = ElinorDefaultRouter()

# Base resources
router.register(r"assessments", AssessmentViewSet, "assessment")
router.register(r"attributes", AttributeViewSet, "attribute")
router.register(r"assessmentchanges", AssessmentChangeViewSet, "assessmentchange")
router.register(r"assessmentflags", AssessmentFlagViewSet, "assessmentflag")
router.register(r"collaborators", CollaboratorViewSet, "collaborator")
router.register(r"documents", DocumentViewSet, "document")
router.register(r"governancetypes", GovernanceTypeViewSet, "governancetype")
router.register(r"managementareas", ManagementAreaViewSet, "managementarea")
router.register(r"managementareazones", ManagementAreaZoneViewSet, "managementareazone")
router.register(
    r"managementauthorities", ManagementAuthorityViewSet, "managementauthority"
)
router.register(r"organizations", OrganizationViewSet, "organization")
router.register(r"protectedareas", ProtectedAreaViewSet, "protectedarea")
router.register(r"regions", RegionViewSet, "region")
router.register(r"stakeholdergroups", StakeholderGroupViewSet, "stakeholder")
router.register(r"supportsources", SupportSourceViewSet, "supportsource")
router.register(
    r"surveyquestionlikerts", SurveyQuestionLikertViewSet, "surveyquestionlikert"
)
router.register(r"surveyanswerlikerts", SurveyAnswerLikertViewSet, "surveyanswerlikert")
router.register(r"users", UserViewSet, "user")

# Reporting resources (read-only)
router.register(f"reports/assessments", AssessmentReportView, "assessmentreport")

api_urls = router.urls + [
    re_path(r"^health/$", health),
    path("assessmentversion", assessmentversion, name="assessmentversion"),
    path(
        "contactassessmentadmins",
        contact_assessment_admins,
        name="contactassessmentadmin",
    ),
    path("contactelinoradmins", contact_elinor_admins, name="contactelinoradmin"),
]
