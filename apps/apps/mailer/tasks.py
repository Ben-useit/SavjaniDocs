from __future__ import unicode_literals

from django.apps import apps
from django.utils.html import mark_safe
from mayan.celery import app
import logging
logger = logging.getLogger(__name__)

@app.task(ignore_result=True)
def task_send_document(body, sender, subject, recipient, user_mailer_id, as_attachment=False, document_id=None):
    Document = apps.get_model(
        app_label='documents', model_name='Document'
    )
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )

    if document_id:
        document = Document.objects.get(pk=document_id)
    else:
        document = None

    user_mailer = UserMailer.objects.get(pk=user_mailer_id)
    #add signature
    body = mark_safe("<html>"+body + "\n"+user_mailer.signature+"</html>")
    user_mailer.send_document(
        as_attachment=as_attachment, body=body, document=document,
        subject=subject, to=recipient
    )

@app.task(ignore_result=True)
def task_send(body, sender, subject, recipient, user_mailer_id, as_attachment=False, document_id=None, signature=False):
    UserMailer = apps.get_model(
        app_label='mailer', model_name='UserMailer'
    )

    user_mailer = UserMailer.objects.get(pk=user_mailer_id)
    
    #add signature
    if signature:
        body = body + "\n"+user_mailer.signature

    user_mailer.send(
        body=body,
        subject=subject, to=recipient
    )



  
