from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from drf_recaptcha.fields import ReCaptchaV3Field
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from ..models import Assessment
from ..utils.email import email_assessment_admins, email_elinor_admins


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    subject = serializers.CharField()
    message = serializers.CharField()


class ContactElinorAdminsSerializer(ContactSerializer):
    recaptcha = ReCaptchaV3Field(action="contact_elinor_admins")


class ContactAssessmentAdminsSerializer(ContactSerializer):
    recaptcha = ReCaptchaV3Field(action="contact_assessment_admins")
    assessment = serializers.IntegerField()


def _process_contact_request(serializer, email_function):
    serializer.is_valid(raise_exception=True)
    assessment_id = serializer.validated_data.get("assessment")
    assessment = None
    if assessment_id:
        try:
            assessment = Assessment.objects.get(pk=assessment_id)
        except Assessment.DoesNotExist:
            return Response(
                f"assessment {assessment_id} does not exist",
                status=status.HTTP_400_BAD_REQUEST,
            )

    kwargs = {
        "name": serializer.validated_data.get("name"),
        "from_email": serializer.validated_data.get("email"),
        "subject": serializer.validated_data.get("subject"),
        "message": serializer.validated_data.get("message"),
        "assessment": assessment,
    }
    email_function(**kwargs)

    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny,))
def contact_elinor_admins(request):
    serializer = ContactElinorAdminsSerializer(
        data=request.data, context={"request": request}
    )
    return _process_contact_request(serializer, email_elinor_admins)


@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny,))
def contact_assessment_admins(request):
    serializer = ContactAssessmentAdminsSerializer(
        data=request.data, context={"request": request}
    )
    return _process_contact_request(serializer, email_assessment_admins)
