from ..models import Assessment, AssessmentChange


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
            Assessment.PUBLISHED: AssessmentChange.SUBMIT,
            Assessment.OPEN: AssessmentChange.UNSUBMIT,
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
