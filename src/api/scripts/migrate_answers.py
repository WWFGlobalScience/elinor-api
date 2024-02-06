import csv
from ..models.assessment import Assessment
from ..models.survey import SurveyQuestionLikert, SurveyAnswerLikert

TEXT_SUFFIX = "_text"
NON_QUESTION_FIELDS = [
    "id",
    "created_on",
    "updated_on",
    "name",
    "status",
    "data_policy",
    "person_responsible_role",
    "person_responsible_role_other",
    "year",
    "count_community",
    "count_ngo",
    "count_academic",
    "count_government",
    "count_private",
    "count_indigenous",
    "consent_given",
    "consent_given_written",
    "management_plan_file",
    "collection_method",
    "collection_method_text",
]


def run():
    with open("/var/projects/webapp/answers_without_questions.csv", "w") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(
            ["assessment_id", "assessment_name", "fieldname", "value", "value_text"]
        )

        legacy_questions = [
            field.name
            for field in Assessment._meta.get_fields()
            if not field.is_relation
            and field.name not in NON_QUESTION_FIELDS
            and not field.name.endswith(TEXT_SUFFIX)
        ]

        assessments = Assessment.objects.all()
        for assessment in assessments:
            counter = 0
            for slug in legacy_questions:
                try:
                    new_question = SurveyQuestionLikert.objects.get(key=slug)
                    choice = getattr(assessment, slug)
                    explanation = getattr(assessment, f"{slug}{TEXT_SUFFIX}")

                    if choice is not None:
                        answer = SurveyAnswerLikert.objects.create(
                            assessment=assessment,
                            created_by=assessment.created_by,
                            updated_by=assessment.updated_by,
                            question=new_question,
                            choice=choice,
                            explanation=explanation,
                        )
                        answer.created_on = assessment.created_on
                        # can't (and shouldn't) transfer updated_on
                        answer.save()
                        counter += 1
                        # print(counter, answer)
                except SurveyQuestionLikert.DoesNotExist:
                    # print(f"no question for {slug}")
                    csvwriter.writerow(
                        [assessment.pk, assessment.name, slug, choice, explanation]
                    )
