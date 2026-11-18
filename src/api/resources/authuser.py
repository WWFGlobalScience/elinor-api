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
from dj_rest_auth.serializers import LoginSerializer, PasswordResetSerializer
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.db import IntegrityError, transaction
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Organization
from api.resources.base import User


class IExactLoginSerializer(LoginSerializer):
    @staticmethod
    def validate_email_verification_status(user, email=None):
        """
        Override to use case-insensitive email matching.

        This is a minimal change from the original dj-rest-auth implementation:
        - Original: filter(email=user.email, verified=True)
        - Fixed:    filter(email__iexact=user.email, verified=True)

        Args:
            user: The authenticated user instance
            email: The email used for login (unused, kept for signature compatibility)

        Raises:
            ValidationError: If email is not verified when verification is mandatory
        """
        if (
            app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY
            and not user.emailaddress_set.filter(
                email__iexact=user.email, verified=True
            ).exists()
        ):
            raise serializers.ValidationError("E-mail is not verified.")


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
        # allauth validates username/email uniqueness before saving, but two
        # concurrent identical POSTs can both pass validation; the loser hits the
        # DB unique constraint. Roll back the whole user + profile and return a 400.
        try:
            with transaction.atomic():
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
        except IntegrityError:
            # The username is the only DB-unique field on signup (allauth's email
            # constraint covers verified addresses only). If it now exists, a
            # concurrent request won the race; anything else should surface.
            username = self.validated_data.get("username")
            if username and User.objects.filter(username=username).exists():
                raise serializers.ValidationError(
                    {"username": ["A user with that username already exists."]}
                )
            raise

        return user


class NewEmailConfirmation(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        if not email:
            return Response(
                {"message": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Match auth_user.email case-insensitively: that is the address login
        # requires to be verified and the one the confirmation is sent to.
        user_ids = set(
            User.objects.filter(email__iexact=email).values_list("id", flat=True)
        )

        if not user_ids:
            return Response(
                {"message": "This email does not exist, please create a new account"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if len(user_ids) > 1:
            return Response(
                {"message": "Multiple accounts found with this email. Please contact support."},
                status=status.HTTP_409_CONFLICT,
            )

        user = User.objects.get(pk=user_ids.pop())
        user_addresses = user.emailaddress_set.filter(email__iexact=user.email)

        if user_addresses.filter(verified=True).exists():
            return Response(
                {"message": "This email is already verified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email_address = user_addresses.first()
        if email_address is None:
            email_address = EmailAddress.objects.create(
                user=user, email=user.email, primary=True, verified=False
            )
        # On SMTP failure this raises EmailSendFailed (503) via ElinorAccountAdapter
        email_address.send_confirmation(request)
        return Response(
            {"message": "Email confirmation sent"},
            status=status.HTTP_201_CREATED,
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
