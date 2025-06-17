from __future__ import absolute_import, unicode_literals
from django.apps import apps
from django.utils.translation import ugettext_lazy as _

from acls.classes import ModelPermission
from common.apps import MayanAppConfig
from common.menus import (
    menu_main, menu_object
)
from events import ModelEventType
from navigation.classes import SourceColumn

from .events import event_client_created, event_client_edited
from .links import (
    link_client_create, link_client_edit, link_client_list,
    link_client_ex_list, link_client_detail,
    link_client_list_register_files,
    link_contact_create
)
from .menus import menu_clients
from .permissions import permission_client_create, permission_client_view
from documents.links import link_document_list

class ClientsApp(MayanAppConfig):
    app_namespace = 'clients'
    app_url = 'clients'
    has_rest_api = False
    has_static_media = False
    has_tests = False
    name = 'clients'
    verbose_name = _('Clients')

    def ready(self):
        super(ClientsApp,self).ready()
        Client = apps.get_model(
            app_label='clients', model_name='Client'
        )
        Register = apps.get_model(
            app_label='register', model_name='Register'
        )
        ModelEventType.register(
            model=Client, event_types=(
                event_client_created, event_client_edited
            )
        )
        ModelPermission.register(
            model=Client, permissions=(
                permission_client_create, permission_client_view,
            )
        )
        SourceColumn(
            attribute='name',
            source=Client
        )
        SourceColumn(
            source=Client, label=_('Active'),
            func=lambda context: context['object'].get_no_matters(status='Active')
        )
        SourceColumn(
            source=Client, label=_('Not active'),
            func=lambda context: context['object'].get_no_matters(status='Not active')
        )
        SourceColumn(
            source=Client, label=_('Dormant'),
            func=lambda context: context['object'].get_no_matters(status='Dormant')
        )
        SourceColumn(
            source=Client, label=_('Closed'),
            func=lambda context: context['object'].get_no_matters(status='Closed')
        )
        SourceColumn(
            source=Client, label=_('Misc'),
            func=lambda context: context['object'].get_no_matters(status='Misc')
        )
        SourceColumn(
            source=Client, label=_('Total'),
            func=lambda context: context['object'].get_no_matters()
        )

        menu_object.bind_links(
            links=(
                link_client_edit,link_client_detail,link_client_list_register_files
            ),
            sources=(Client,)
        )
        menu_clients.bind_links(
            links=(
                link_client_list, link_client_create
            )
        )
        menu_main.bind_links(links=(menu_clients,), position=60)

