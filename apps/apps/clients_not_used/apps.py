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
    link_contact_create, link_contact_edit, link_contact_list,
)
from .menus import menu_clients
from .permissions import permission_client_create, permission_client_view

class ClientsApp(MayanAppConfig):
    #app_namespace = 'clients'
    #app_url = 'clients'
    has_rest_api = False
    #has_static_media = False
    has_tests = False
    name = 'clients'
    verbose_name = _('Clients')

    def ready(self):
        super(ClientsApp, self).ready()
        ClientA = apps.get_model(
            app_label='clients', model_name='ClientA'
        )
        #EventModelRegistry.register(model=Client)
        ModelEventType.register(
            model=ClientA, event_types=(
                event_client_created, event_client_edited
            )
        )
        ModelPermission.register(
            model=ClientA, permissions=(
                permission_client_create, permission_client_view,
            )
        )
        SourceColumn(
            source=ClientA, label=_('Client'),
            attribute='name'
        )
        menu_object.bind_links(
            links=(
                link_client_edit,
            ),
            sources=(ClientA,)
        )
        menu_clients.bind_links(
            links=(
                link_client_list, link_client_create,
                link_contact_list, link_contact_create,
            )
        )
        menu_main.bind_links(links=(menu_clients,), position=60)

