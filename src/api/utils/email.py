import datetime
import os
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def elinor_email(subject, template, to, context=None, from_email=None, reply_to=None):
    _subject = f"[Elinor] {subject}"
    path, _ = os.path.splitext(template)
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


def email_elinor_admins(subject, message, name, from_email):
    template = "emails/contact_elinor_admins.html"
    context = {"message": message, "name": name, "from_email": from_email}

    elinor_email(
        subject,
        template,
        [settings.EMAIL_CONTACT],
        context=context,
        reply_to=[from_email],
    )


def email_assessment_admins(assessment, subject, message, name, from_email):
    pass


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
