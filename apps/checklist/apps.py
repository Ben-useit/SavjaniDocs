from __future__ import absolute_import, unicode_literals

from django.apps import apps
from django.utils.translation import ugettext_lazy as _
from events import ModelEventType
from common import (
    MayanAppConfig, menu_main,menu_object, menu_multi_item
)
from common.classes import ModelAttribute
from navigation import SourceColumn
#from .menu import menu_checklist
from .links import link_checklist, link_select, link_status_report
from .menus import menu_checklist

class ChecklistApp(MayanAppConfig):
    has_rest_api = False
    has_tests = False
    name = 'checklist'
    verbose_name = _('Checklist')

    def ready(self):
        super(ChecklistApp, self).ready()

        # ~ from actstream import registry

        Checklist = self.get_model('Checklist')
        # ~ Quotation = self.get_model('Quotation')

        Register = apps.get_model(
            app_label='register', model_name='Register'
        )

        menu_object.bind_links(
            links=(
                link_status_report, link_checklist, 
            ),
            sources=(Register,)
        )
        menu_object.bind_links(
            links=(
                link_select,
            ),
            sources=(Checklist,)
        )


