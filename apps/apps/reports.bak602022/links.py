from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Link, get_cascade_condition

from .permissions import permission_reports_view

link_reports_activity = Link(
    permissions=(permission_reports_view,),
    text=_('Upload report'), view='reports:activity'
)
link_reports_user_activity = Link(
    text=_('My upload report'), view='reports:current_user_activity'
)
link_reports_register_event = Link(
    args='object.id', text=_('Events'), view='reports:events'
)
link_reports_register_statistics = Link(
    text=_('Matter report'), view='reports:register_statistics'
)
link_reports_register_lawyer = Link(
    text=_('Lawyer report'), view='reports:activity_lawyer'
)
link_reports_transfers = Link(
    permissions=(permission_reports_view,),
    text=_('Transfer report'), view='reports:register_transfer'
)

