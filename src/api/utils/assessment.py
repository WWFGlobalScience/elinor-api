from ..models import AssessmentPeriod, AssessmentPeriodChange


def _log_ap_change(original_ap, updated_ap, field, change_dict, user):
    original_val = getattr(original_ap, field)
    updated_val = getattr(updated_ap, field)
    if original_val != updated_val:
        event_type = change_dict.get(updated_val)
        if event_type:
            AssessmentPeriodChange.objects.create(
                assessment_period=updated_ap, user=user, event_type=event_type
            )


def log_ap_change(original_ap, updated_ap, user):
    if (
        original_ap.status != updated_ap.status
        or original_ap.data_policy != updated_ap.data_policy
    ):
        status_changes = {
            AssessmentPeriod.PUBLISHED: AssessmentPeriodChange.SUBMIT,
            AssessmentPeriod.OPEN: AssessmentPeriodChange.UNSUBMIT,
        }
        _log_ap_change(original_ap, updated_ap, "status", status_changes, user)

        data_policy_changes = {
            AssessmentPeriod.PUBLIC: AssessmentPeriodChange.DATA_POLICY_PUBLIC,
            AssessmentPeriod.PRIVATE: AssessmentPeriodChange.DATA_POLICY_PRIVATE,
        }
        _log_ap_change(
            original_ap, updated_ap, "data_policy", data_policy_changes, user
        )

    # uncomment if we want to track all edits (list could get long!)
    # else:
    #     AssessmentPeriodChange.objects.create(
    #         assessment_period=updated_ap,
    #         user=user,
    #         event_type=AssessmentPeriodChange.EDIT
    #     )
