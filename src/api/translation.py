from modeltranslation.translator import register, TranslationOptions
from .models import (
    Assessment,
    AssessmentVersion,
    Attribute,
    Document,
    GovernanceType,
    ManagementArea,
    ManagementAreaZone,
    ManagementAuthority,
    Organization,
    ProtectedArea,
    Region,
    StakeholderGroup,
    SupportSource,
    SurveyAnswerLikert,
    SurveyQuestionLikert,
)


class ChoiceTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Assessment)
class AssessmentTranslationOptions(TranslationOptions):
    fields = ("name", "collection_method_text")


@register(AssessmentVersion)
class AssessmentVersionTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Attribute)
class AttributeTranslationOptions(ChoiceTranslationOptions):
    fields = ("description",)


@register(Document)
class DocumentTranslationOptions(TranslationOptions):
    fields = ("name", "description")
    empty_values = "both"


@register(GovernanceType)
class GovernanceTypeTranslationOptions(ChoiceTranslationOptions):
    pass


@register(ManagementArea)
class ManagementAreaTranslationOptions(TranslationOptions):
    fields = ("name", "geospatial_sources", "objectives")


@register(ManagementAreaZone)
class ManagementAreaZoneTranslationOptions(TranslationOptions):
    fields = ("name", "description")


@register(ManagementAuthority)
class ManagementAuthorityTranslationOptions(ChoiceTranslationOptions):
    pass


@register(Organization)
class OrganizationTranslationOptions(ChoiceTranslationOptions):
    pass


@register(ProtectedArea)
class ProtectedAreaTranslationOptions(ChoiceTranslationOptions):
    pass


@register(Region)
class RegionTranslationOptions(ChoiceTranslationOptions):
    pass


@register(StakeholderGroup)
class StakeholderGroupTranslationOptions(ChoiceTranslationOptions):
    pass


@register(SupportSource)
class SupportSourceTranslationOptions(ChoiceTranslationOptions):
    pass


@register(SurveyAnswerLikert)
class SurveyAnswerLikertTranslationOptions(TranslationOptions):
    fields = ("explanation",)


@register(SurveyQuestionLikert)
class SurveyQuestionLikertTranslationOptions(TranslationOptions):
    fields = (
        "text",
        "rationale",
        "information",
        "guidance",
        "dontknow_10",
        "poor_20",
        "average_30",
        "good_40",
        "excellent_50",
    )
