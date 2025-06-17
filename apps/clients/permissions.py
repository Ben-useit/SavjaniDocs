from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext_lazy as _

from permissions import PermissionNamespace

namespace = PermissionNamespace(label=_('Clients'), name='clients')

permission_client_create = namespace.add_permission(
    label=_('Create client'), name='client_create'
)
permission_client_view = namespace.add_permission(
    label=_('View client'), name='client_view'
)

