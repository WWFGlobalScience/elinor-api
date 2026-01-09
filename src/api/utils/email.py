import datetime
from pathlib import Path
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from ..models import Collaborator


def elinor_email(subject, template, to, context=None, from_email=None, reply_to=None):
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
    msg.send()


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
