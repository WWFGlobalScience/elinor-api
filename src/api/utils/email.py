import datetime
import logging
import smtplib
import time
from pathlib import Path
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.exceptions import APIException
from ..models import Collaborator

logger = logging.getLogger(__name__)

# One retry after this delay. Runs inside the request on a sync gunicorn worker
# (4 workers, 300s timeout), so keep it short; longer back-off belongs in a queue.
TRANSIENT_RETRY_DELAY = 5  # seconds


class EmailSendFailed(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        "We couldn't send the email right now. Please try again in a few minutes."
    )
    default_code = "email_send_failed"


def _is_transient(e):
    """
    True only for temporary (4xx) failures where the server explicitly did not
    accept the message, so resending can't produce a duplicate. Deliberately
    excludes a bare SMTPResponseException and SMTPServerDisconnected, either of
    which can occur after the message was accepted.
    """
    if isinstance(e, smtplib.SMTPRecipientsRefused):
        return bool(e.recipients) and all(
            400 <= code < 500 for code, _ in e.recipients.values()
        )
    if isinstance(
        e, (smtplib.SMTPDataError, smtplib.SMTPSenderRefused, smtplib.SMTPConnectError)
    ):
        return 400 <= e.smtp_code < 500
    return False


def send_with_retry(send, description):
    """
    Call `send()`, retrying once after TRANSIENT_RETRY_DELAY if the SMTP server
    temporarily rejects the message (e.g. Gmail's "451 4.3.0 temporarily rejected").
    Any remaining SMTP or connection failure is logged and raised as EmailSendFailed.
    """
    try:
        try:
            send()
        except smtplib.SMTPException as e:
            if not _is_transient(e):
                raise
            logger.warning(
                "Transient SMTP error sending %r (%r); retrying once", description, e
            )
            time.sleep(TRANSIENT_RETRY_DELAY)
            send()
    except (smtplib.SMTPException, OSError) as e:
        logger.exception("Failed to send email %r", description)
        raise EmailSendFailed() from e


def elinor_email(
    subject,
    template,
    to,
    context=None,
    from_email=None,
    reply_to=None,
    raise_on_failure=False,
):
    """
    Send an Elinor email. Most callers send notifications as a side effect of a
    successful write, so by default a send failure is logged and swallowed rather
    than failing the request; pass raise_on_failure=True when the email is the
    point of the request.
    """
    _subject = f"[Elinor] {subject}"
    path = Path(template).parent / Path(template).stem
    template_dir = settings.TEMPLATES[0]["DIRS"][0]
    template_html = f"{path}.html"
    template_text = f"{path}.txt"

    context = context or {}
    context["frontend_domain"] = settings.FRONTEND_DOMAIN
    context["elinor_contact"] = settings.EMAIL_CONTACT
    context["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    text_content = render_to_string(template_text, context=context)
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    reply_to = reply_to or [settings.DEFAULT_FROM_EMAIL]

    msg = EmailMultiAlternatives(
        _subject, text_content, to=to, from_email=from_email, reply_to=reply_to
    )
    if (Path(template_dir) / template_html).is_file():
        html_content = render_to_string(template_html, context=context)
        msg.attach_alternative(html_content, "text/html")
    try:
        send_with_retry(msg.send, _subject)
    except EmailSendFailed:
        if raise_on_failure:
            raise


def email_elinor_admins(**kwargs):
    template = "emails/contact_elinor_admins.html"
    from_email = kwargs["from_email"]
    context = {
        "message": kwargs["message"],
        "name": kwargs["name"],
        "from_email": from_email,
    }

    elinor_email(
        kwargs["subject"],
        template,
        [settings.EMAIL_CONTACT],
        context=context,
        reply_to=[from_email],
        raise_on_failure=kwargs.get("raise_on_failure", False),
    )


def email_assessment_admins(**kwargs):
    template = "emails/contact_assessment_admins.html"
    from_email = kwargs["from_email"]
    assessment = kwargs["assessment"]
    context = {
        "message": kwargs["message"],
        "name": kwargs["name"],
        "from_email": from_email,
        "assessment": assessment,
    }
    admins = Collaborator.objects.filter(assessment=assessment, role=Collaborator.ADMIN)
    admin_emails = [admin.user.email for admin in admins]

    elinor_email(
        kwargs["subject"],
        template,
        admin_emails,
        context=context,
        reply_to=[from_email],
        raise_on_failure=kwargs.get("raise_on_failure", False),
    )


def notify_assessment_admins(**kwargs):
    template = "emails/notify_assessment_admins.html"
    assessment = kwargs["assessment"]
    context = {
        "message": kwargs["message"],
        "assessment": assessment,
    }
    admins = Collaborator.objects.filter(assessment=assessment, role=Collaborator.ADMIN)
    admin_emails = [admin.user.email for admin in admins]

    elinor_email(
        kwargs["subject"],
        template,
        admin_emails,
        context=context,
    )


def email_elinor_admins_flag(assessmentflag, admin_link):
    template = "emails/flag_elinor_admins.html"
    subject = f"Elinor assessment flagged: {assessmentflag}"
    context = {"assessmentflag": assessmentflag, "admin_link": admin_link}

    elinor_email(
        subject,
        template,
        [settings.EMAIL_CONTACT],
        context=context,
    )


def email_assessment_admins_flag(assessmentflag, admin_emails):
    template = "emails/flag_assessment_admins.html"
    subject = f"Elinor assessment flagged: {assessmentflag}"
    context = {"assessmentflag": assessmentflag}

    elinor_email(
        subject,
        template,
        admin_emails,
        context=context,
    )


def email_assessment_flagger(assessmentflag):
    template = "emails/flag_assessment_flagger.html"
    subject = f"Elinor assessment flagged: {assessmentflag}"
    context = {"assessmentflag": assessmentflag}

    elinor_email(
        subject,
        template,
        [assessmentflag.reporter.email],
        context=context,
    )


def notify_collaborator_change(**kwargs):
    template = "emails/notify_collaborator_change.html"
    assessment = kwargs["assessment"]
    user = kwargs["user"]
    context = {
        "message": kwargs["message"],
        "assessment": assessment,
        "user": user,
    }

    elinor_email(
        kwargs["subject"],
        template,
        [user.email],
        context=context,
    )


def notify_assessment_admins_collaborator_change(**kwargs):
    template = "emails/notify_assessment_admins_collaborator_change.html"
    assessment = kwargs["assessment"]
    user = kwargs["user"]
    context = {
        "message": kwargs["message"],
        "assessment": assessment,
        "user": user,
    }
    admins = Collaborator.objects.filter(assessment=assessment, role=Collaborator.ADMIN)
    # Exclude the affected user to avoid duplicate emails (they get their own notification)
    admin_emails = [admin.user.email for admin in admins if admin.user != user]

    if admin_emails:
        elinor_email(
            kwargs["subject"],
            template,
            admin_emails,
            context=context,
        )
