from django.utils.translation import ugettext_lazy as _

from navigation import Link
from .permissions import permission_client_create, permission_client_view


link_client_create = Link(
    text=_('Create Client'), view='clients:client_create'
)
link_client_edit = Link(
    args='object.id',
    text=_('Edit'), view='clients:client_edit'
)
link_client_detail = Link(
    args='object.id',
    text=_('Detail'), view='clients:client_detail'
)
link_client_list = Link(
    text=_('List'), view='clients:client_list'
)
link_client_ex_list = Link(
    text=_('List external lawyers'), view='clients:client_list_ex'
)
link_client_list_register_files = Link(
    args='object.id',
    text=_('Files'), view='clients:client_list_register_files'
)
link_contact_create = Link(
    text=_('Create Contact'), view='clients:contact_create'
)
