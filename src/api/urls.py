from .resources.base import (
    ElinorDefaultRouter,
    GovernanceTypeViewSet,
    ManagementAuthorityViewSet,
    OrganizationViewSet,
    ProtectedAreaViewSet,
    RegionViewSet,
    StakeholderGroupViewSet,
    SupportSourceViewSet,
    UserViewSet,
)
from .resources.management import (
    ManagementAreaViewSet,
    ManagementAreaZoneViewSet,
)
from .resources.assessment import (
    AssessmentViewSet,
    AssessmentChangeViewSet,
    CollaboratorViewSet,
)


router = ElinorDefaultRouter()

router.register(r"assessments", AssessmentViewSet, "assessment")
router.register(r"assessmentchanges", AssessmentChangeViewSet, "assessmentchange")
router.register(r"collaborators", CollaboratorViewSet, "collaborator")
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
router.register(r"users", UserViewSet, "user")

api_urls = router.urls
