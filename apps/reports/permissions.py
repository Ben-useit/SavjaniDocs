from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy as _

from permissions import PermissionNamespace

namespace = PermissionNamespace('reports', _('Reports'))

permission_reports_view = namespace.add_permission(
    name='reports_view', label=_('View reports')
)
