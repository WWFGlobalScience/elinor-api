import logging

from allauth.account.adapter import DefaultAccountAdapter

from .utils.email import EmailSendFailed, send_with_retry

logger = logging.getLogger(__name__)


class ElinorAccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        """
        All allauth mail (password reset, signup/resend verification, email change)
        comes through here. Retry once on a transient SMTP rejection; otherwise
        raise EmailSendFailed (503) instead of letting SMTPException become a 500.
        """
        parent_send_mail = super().send_mail
        send_with_retry(
            lambda: parent_send_mail(template_prefix, email, context),
            template_prefix,
        )

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        At signup the user, profile and EmailAddress rows are already saved by the
        time the verification email is sent, so failing the request would report
        "registration failed" for an account that exists. Log and carry on; the
        user can request a new verification email via resend-verification-email.
        """
        try:
            super().send_confirmation_mail(request, emailconfirmation, signup)
        except EmailSendFailed:
            if not signup:
                raise
            logger.error(
                "Signup verification email not sent for user %s; "
                "user must use resend-verification-email",
                emailconfirmation.email_address.user_id,
            )
