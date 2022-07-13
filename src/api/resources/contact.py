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
from ..utils.email import email_elinor_admins


class ContactElinorAdminsSerializer(serializers.Serializer):
    recaptcha = ReCaptchaV3Field(action="contact_elinor_admins")
    name = serializers.CharField()
    email = serializers.EmailField()
    subject = serializers.CharField()
    message = serializers.CharField()


@api_view(["POST"])
@authentication_classes([])
@permission_classes((AllowAny,))
def contact_elinor_admins(request):
    serializer = ContactElinorAdminsSerializer(
        data=request.data, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)

    name = serializer.validated_data.get("name")
    email = serializer.validated_data.get("email")
    subject = serializer.validated_data.get("subject")
    message = serializer.validated_data.get("message")
    email_elinor_admins(subject, message, name, email)

    return Response(status=status.HTTP_200_OK)
