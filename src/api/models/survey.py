from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from .base import Attribute, BaseModel


POOR = 0
AVERAGE = 1
GOOD = 2
EXCELLENT = 3
LIKERT_CHOICES = (
    (POOR, _(f"poor [{POOR}]")),
    (AVERAGE, _(f"average [{AVERAGE}]")),
    (GOOD, _(f"good [{GOOD}]")),
    (EXCELLENT, _(f"excellent [{EXCELLENT}]")),
)


class SurveyQuestion(BaseModel):
    attribute = models.ForeignKey(
        Attribute, related_name="attribute_questions", on_delete=models.PROTECT
    )
    key = models.CharField(max_length=255, unique=True)
    number = models.PositiveSmallIntegerField()
    text = models.TextField()
    rationale = models.TextField()
    information = models.TextField()
    guidance = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.key}"


class SurveyQuestionLikert(SurveyQuestion):
    poor_0 = models.TextField()
    average_1 = models.TextField()
    good_2 = models.TextField()
    excellent_3 = models.TextField()

    class Meta:
        ordering = ["attribute", "number"]
        verbose_name = "Likert survey question"


class SurveyAnswer(BaseModel):
    assessment_lookup = "assessment"

    assessment = models.ForeignKey(
        "Assessment", related_name="survey_answer_likerts", on_delete=models.CASCADE
    )

    class Meta:
        abstract = True


class SurveyAnswerLikert(SurveyAnswer):
    question = models.ForeignKey(
        SurveyQuestionLikert,
        related_name="questionlikert_answers",
        on_delete=models.PROTECT,
    )
    choice = models.PositiveSmallIntegerField(
        choices=LIKERT_CHOICES, null=True, blank=True
    )
    explanation = models.TextField(blank=True)

    class Meta:
        unique_together = ("assessment", "question")
        verbose_name = "Likert survey answer"
        ordering = ["question__attribute__order", "question__number"]

    def __str__(self):
        return f"{self.assessment} {self.question}"
