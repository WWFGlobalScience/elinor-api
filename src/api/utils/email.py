import datetime
import os

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def elinor_email(subject, template, to, context=None, from_email=None, reply_to=None):
    _subject = f"[Elinor] {subject}"
    path, _ = os.path.splitext(template)
    template_html = f"{path}.html"
    template_text = f"{path}.txt"

    context = context or {}
    context["timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
    text_content = render_to_string(template_text, context=context)
    html_content = render_to_string(template_html, context=context)
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    reply_to = reply_to or [settings.DEFAULT_FROM_EMAIL]

    msg = EmailMultiAlternatives(
        _subject, text_content, to=to, from_email=from_email, reply_to=reply_to
    )
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


def email_project_admins(project, subject, message, name, from_email):
    pass
