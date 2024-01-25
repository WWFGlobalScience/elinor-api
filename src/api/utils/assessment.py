from collections import defaultdict
from django.conf import settings
from ..models import Assessment, AssessmentChange, Attribute, SurveyAnswerLikert
from ..models.base import EXCELLENT
from ..models.assessment import SurveyQuestionLikert


def questionlikerts():
    return SurveyQuestionLikert.objects.select_related("attribute").order_by(
        "attribute__order", "attribute__name", "number"
    )


def attribute_scores(assessment):
    answers = (
        SurveyAnswerLikert.objects.filter(assessment=assessment)
        .select_related("question", "question__attribute")
        .order_by(
            "question__attribute__order",
            "question__attribute__name",
            "question__number",
        )
    )

    attributes = defaultdict(list)
    for a in answers:
        answer = {
            "question": a.question.key,
            "choice": a.choice,
            "explanation": a.explanation,
        }
        attributes[a.question.attribute.name].append(answer)

    output_attributes = []
    for attrib, answers in attributes.items():
        nonnull_answers = [a for a in answers if a["choice"] is not None]
        total_points = len(nonnull_answers) * EXCELLENT
        points = sum([a["choice"] for a in nonnull_answers])
        attribute = {"attribute": attrib, "score": None, "answers": answers}
        if total_points:
            score = points / total_points
            normalized_score = round(score * settings.ATTRIBUTE_NORMALIZER, 1)
            attribute["score"] = normalized_score
        output_attributes.append(attribute)

    return output_attributes


def get_answer_by_slug(attributes, slug):
    if attributes:
        for attribute in attributes:
            for answer in attribute["answers"]:
                if answer["question"] == slug:
                    return {
                        "score": attribute["score"],
                        "choice": answer["choice"],
                        "explanation": answer["explanation"],
                    }
    return None


def assessment_score(attributes):
    nonnull_attributes = [a for a in attributes if a["score"] is not None]
    total_attribs = len(nonnull_attributes) * settings.ATTRIBUTE_NORMALIZER
    scores_total = sum([a["score"] for a in nonnull_attributes])
    if not total_attribs:
        return None
    score_ratio = scores_total / total_attribs
    normalized_score = round(score_ratio * 100)
    return normalized_score


def _log_assessment_change(
    original_assessment, updated_assessment, field, change_dict, user
):
    original_val = getattr(original_assessment, field)
    updated_val = getattr(updated_assessment, field)
    if original_val != updated_val:
        event_type = change_dict.get(updated_val)
        if event_type:
            AssessmentChange.objects.create(
                assessment=updated_assessment, user=user, event_type=event_type
            )


def log_assessment_change(original_assessment, updated_assessment, user):
    if (
        original_assessment.status != updated_assessment.status
        or original_assessment.data_policy != updated_assessment.data_policy
    ):
        status_changes = {
            Assessment.FINALIZED: AssessmentChange.SUBMIT,
            Assessment.NOT_FINALIZED: AssessmentChange.UNSUBMIT,
        }
        _log_assessment_change(
            original_assessment, updated_assessment, "status", status_changes, user
        )

        data_policy_changes = {
            Assessment.PUBLIC: AssessmentChange.DATA_POLICY_PUBLIC,
            Assessment.PRIVATE: AssessmentChange.DATA_POLICY_PRIVATE,
        }
        _log_assessment_change(
            original_assessment,
            updated_assessment,
            "data_policy",
            data_policy_changes,
            user,
        )

    # uncomment if we want to track all edits (list could get long!)
    # else:
    #     AssessmentChange.objects.create(
    #         assessment=updated_assessment,
    #         user=user,
    #         event_type=AssessmentChange.EDIT
    #     )


def enforce_required_attributes(assessment):
    required_attributes = Attribute.objects.filter(required=True)
    missing_required = required_attributes.difference(assessment.attributes.all())
    if missing_required:
        assessment.attributes.add(*missing_required)
