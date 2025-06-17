from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy as _

from permissions import PermissionNamespace

namespace = PermissionNamespace('register', _('Register'))

permission_register_view = namespace.add_permission(
    name='register_view', label=_('View register entries')
)
permission_register_edit= namespace.add_permission(
    name='register_edit', label=_('Edit register entries')
)
permission_register_list= namespace.add_permission(
    name='register_list', label=_('List register entries')
)
permission_register_create= namespace.add_permission(
    name='register_create', label=_('Create register entries')
)
