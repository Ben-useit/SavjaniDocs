from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from navigation.classes import Link
#from navigation.utils import factory_condition_queryset_access

from .permissions import permission_client_create, permission_client_view


link_client_create = Link(
    permissions = (permission_client_create,),
    text=_('Create client'), view='clients:client_create'
)
link_client_edit = Link(
    args='object.id',
    permissions = (permission_client_create,),
    text=_('Edit'), view='clients:client_edit'
)
link_client_list = Link(
    permissions = (permission_client_view,),
    text=_('Clients'), view='clients:client_list'
)

link_contact_create = Link(
    permissions = (permission_client_create,),
    text=_('Create contact'), view='clients:contact_create'
)
link_contact_edit = Link(
    args='object.id',
    permissions = (permission_client_create,),
    text=_('Edit'), view='clients:contact_edit'
)
link_contact_list = Link(
    permissions = (permission_client_view,),
    text=_('Contacts'), view='clients:contact_list'
)
