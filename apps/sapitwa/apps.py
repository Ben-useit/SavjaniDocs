from django.utils.translation import ugettext_lazy as _
from mayan.celery import app
from django.apps import apps
from kombu import Exchange, Queue

from acls.links import link_acl_delete
from common.menus import menu_object, menu_secondary
from common.apps import MayanAppConfig
from common import (
    menu_main,menu_object, menu_multi_item
)
from .links import link_permissions_edit, link_permissions_create, link_document_multiple_delete_signature_images

class SapitwaApp(MayanAppConfig):
    app_namespace = 'sapitwa'
    app_url = 'sapitwa'
    has_rest_api = False
    has_tests = False
    name = 'sapitwa'
    verbose_name = _('Saptiwa')

    def ready(self):
        super(SapitwaApp, self).ready()

        Document = apps.get_model(
            app_label='documents', model_name='Document'
        )

        menu_secondary.bind_links(
            links=(link_permissions_create,), sources=('sapitwa:permissions_list',)
        )
        app.conf.CELERY_QUEUES.extend(
            (
                Queue('sapitwa', Exchange('sapitwa'), routing_key='sapitwa'),
            )
        )


        app.conf.CELERY_ROUTES.update(
            {
                'sapitwa.tasks.task_post_upload_process': {
                    'queue': 'sapitwa'
                },
                'sapitwa.tasks.task_post_web_upload_process': {
                    'queue': 'sapitwa'
                },
            }
        )
        menu_multi_item.bind_links(
            links=(
                link_document_multiple_delete_signature_images,
            ), sources=(Document,)
        )
