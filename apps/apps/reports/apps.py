from __future__ import absolute_import, unicode_literals

from django.apps import apps
from django.db.models.signals import m2m_changed, pre_delete
from django.utils.translation import ugettext_lazy as _

from acls import ModelPermission
from acls.links import link_acl_list
from acls.permissions import permission_acl_edit, permission_acl_view
from common import (
    MayanAppConfig, menu_facet, menu_object, menu_main, menu_multi_item,
    menu_sidebar
)
from common.classes import ModelField
from documents.search import document_page_search, document_search
from events import ModelEventType
from events.links import (
    link_events_for_object, link_object_event_types_user_subcriptions_list,
)
from events.permissions import permission_events_view
from navigation import SourceColumn

from .links import (
    link_reports_activity, link_reports_user_activity, link_reports_register_statistics,
    link_reports_register_lawyer, link_reports_transfers
)
from .menus import menu_reports

class ReportsApp(MayanAppConfig):
    app_namespace = 'reports'
    app_url = 'reports'
    has_rest_api = False
    has_tests = False
    name = 'reports'
    verbose_name = _('Reports')

    def ready(self):
        super(ReportsApp, self).ready()

        Action = apps.get_model(app_label='actstream', model_name='Action')

        menu_reports.bind_links(
            links=(
                link_reports_activity,
                link_reports_register_statistics, link_reports_transfers
            )
        )

        menu_main.bind_links(links=(menu_reports,), position=98)


