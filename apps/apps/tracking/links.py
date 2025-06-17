from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Link, get_cascade_condition

from .icons import icon_tracking, icon_tracking_edit, icon_tracking_delete

def is_tracked(context):
    try:
        return context['object'].is_tracked()
    except KeyError:
        # Might not have permissions
        return False

link_tracking_list = Link(
    icon_class=icon_tracking,
    text=_('List tracked files'), view='tracking:tracking_list'
)
link_tracking_delete = Link(
    args='object.id',
    icon_class=icon_tracking_delete,
    description='aaa',
    html_extra_classes='None',
    text=_('Delete'), view='tracking:tracking_delete'
)
link_tracking_edit = Link(
    args='object.id',
    icon_class=icon_tracking_edit,
    description='aaa',
    html_extra_classes='None',
    text=_('Edit'), view='tracking:tracking_edit'
)
link_tracking_start_tracking = Link(
    icon_class=icon_tracking,
    text=_('Track File'), view='tracking:track_file'
)
link_tracking_retain_or_transfer = Link(
    icon_class=icon_tracking,
    text=_('1. Retain file or transfer required'), view='tracking:retain_or_transfer'
)
link_tracking_closure_letter = Link(
    icon_class=icon_tracking,
    text=_('2. Date of closure Letter'), view='tracking:closure_letter'
)
link_tracking_instructions = Link(
    icon_class=icon_tracking,
    text=_('3. Date of instructions received regarding file transfer'), view='tracking:instructions'
)
link_tracking_client = Link(
    icon_class=icon_tracking,
    text=_('4. File sent to new lawyer or client'), view='tracking:client'
)
link_tracking_notice = Link(
    icon_class=icon_tracking,
    text=_('5. Date of notice of change of legal practitioners'), view='tracking:notice'
)
link_tracking_receipt = Link(
    icon_class=icon_tracking,
    text=_('6. Date of receipt of file acknowledgement'), view='tracking:receipt'
)
link_tracking_completion = Link(
    icon_class=icon_tracking,
    text=_('7. Date of completion'), view='tracking:completion'
)
link_tracking_stop_tracking = Link(
    icon_class=icon_tracking,
    text=_('Stop tracking'), view='tracking:stop_tracking'
)




link_tracking_detail = Link(
    icon_class=icon_tracking,
    condition = is_tracked,
    description='aaa',
    args='object.id',
    html_extra_classes='None',
    text=_('Tracking Chart'), view='tracking:tracking_detail'
)



