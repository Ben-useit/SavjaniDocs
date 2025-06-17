from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Menu, get_cascade_condition

from .icons import icon_menu_reports
from .permissions import permission_reports_view

menu_reports = Menu(
    # ~ condition=get_cascade_condition(
        # ~ app_label='reports',
        # ~ object_permission=permission_reports_view,
        # ~ view_permission=permission_reports_view,
    # ~ ),
    icon_class=icon_menu_reports, label=_('Reports'), name='reports menu'
)
