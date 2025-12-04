from allauth.account import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.forms import default_token_generator
from allauth.account.models import EmailAddress
from allauth.account.utils import (
    user_pk_to_url_str,
    user_username,
)
from dj_rest_auth.forms import AllAuthPasswordResetForm
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import PasswordResetSerializer
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Organization
from api.resources.base import User


class UserRegistrationSerializer(RegisterSerializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    affiliation = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=Organization.objects.all(),
    )
    accept_tor = serializers.BooleanField(
        label="Accept ToR",
    )

    def save(self, request):
        first_name = self.validated_data.get("first_name")
        last_name = self.validated_data.get("last_name")
        affiliation = self.validated_data.get("affiliation")
        accept_tor = self.validated_data.get("accept_tor", False)
        if not accept_tor:
            missing_tor_message = "The Terms of Reference must be accepted in order to register a new account"
            raise serializers.ValidationError(missing_tor_message)
        user = super().save(request)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        profile = user.profile
        profile.affiliation = affiliation
        profile.accept_tor = accept_tor
        profile.created_by = user
        profile.updated_by = user
        profile.save()

        return user


class NewEmailConfirmation(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = get_object_or_404(User, email=request.data["email"])
        emailAddress = EmailAddress.objects.filter(user=user, verified=True).exists()

        if emailAddress:
            return Response(
                {"message": "This email is already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            try:
                email_address = EmailAddress.objects.get_or_create(
                    user=user,
                    email=user.email,
                    defaults={'primary': True, 'verified': False}
                )[0]
                email_address.send_confirmation(request)
                return Response(
                    {"message": "Email confirmation sent"},
                    status=status.HTTP_201_CREATED,
                )
            except APIException:
                return Response(
                    {
                        "message": "This email does not exist, please create a new account"
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )


class FrontendURLPasswordResetForm(AllAuthPasswordResetForm):
    def save(self, request, **kwargs):
        current_site = get_current_site(request)
        email = self.cleaned_data["email"]
        token_generator = kwargs.get("token_generator", default_token_generator)

        for user in self.users:
            temp_key = token_generator.make_token(user)
            url = f"{settings.FRONTEND_DOMAIN}/reset-password/{user_pk_to_url_str(user)}/{temp_key}"

            context = {
                "current_site": current_site,
                "user": user,
                "password_reset_url": url,
                "request": request,
            }
            if (
                app_settings.AUTHENTICATION_METHOD
                != app_settings.AuthenticationMethod.EMAIL
            ):
                context["username"] = user_username(user)
            get_adapter(request).send_mail(
                "account/email/password_reset_key", email, context
            )
        return self.cleaned_data["email"]


class FrontendURLPasswordResetSerializer(PasswordResetSerializer):
    password_reset_form_class = FrontendURLPasswordResetForm
