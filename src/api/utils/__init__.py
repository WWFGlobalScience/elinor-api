import datetime
from django.apps import apps


def update_assessment_version(**kwargs):
    project_apps = apps  # running as part of lookup model instance save()
    AssessmentVersion = None
    if "apps" in kwargs:  # running post migration
        project_apps = kwargs["apps"]
    try:
        AssessmentVersion = project_apps.get_model(
            app_label="api", model_name="AssessmentVersion"
        )
    except LookupError:
        print("AssessmentVersion not yet defined")

    if AssessmentVersion:
        today = datetime.date.today()
        days_since_last = 1
        new_version_year = today.year
        new_major_version = 1

        current_version = AssessmentVersion.objects.order_by(
            "-year", "-major_version"
        ).first()
        if current_version:
            days_since_last = (today - current_version.updated_on.date()).days
            new_version_year = current_version.year
            if today.year == current_version.year:
                new_major_version = current_version.major_version + 1

        if days_since_last > 0:
            AssessmentVersion.objects.create(
                year=new_version_year, major_version=new_major_version
            )
