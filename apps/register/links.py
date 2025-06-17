from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Link, get_cascade_condition

from .icons import (
    icon_register_create, icon_register_list, icon_register_edit,
    icon_register_documents, icon_active_tracking, icon_download
)
from .permissions import (
    permission_register_view, permission_register_edit, permission_register_list,
    permission_register_create
)
from mayan_statistics.icons import icon_view


def has_chart(context):
    try:
        return context['object'].has_chart()
    except KeyError:
        # Might not have permissions
        return False

link_transferred_register_file_list = Link(
    icon_class=icon_active_tracking,
    text=_('List Active Files Tracking Charts'), view='register:active_file_tracking_chart_list'
)
link_active_file_tracking_chart_create = Link(
    icon_class=icon_active_tracking,
    text=_('Create Active Files Tracking Chart'), view='register:active_file_tracking_chart_create'
)
link_active_file_tracking_chart_edit = Link(
    args='object.id', icon_class=icon_register_list,
    text=_('Edit'), view='register:active_file_tracking_chart_edit'
)
link_active_file_tracking_chart_add_file = Link(
    args='object.id', icon_class=icon_register_list,
    text=_('Add files'), view='register:active_file_tracking_chart_add_file'
)
link_active_file_tracking_chart_process_adding_file = Link(
    icon_class=icon_register_list,
    text=_('Add files'), view='register:active_file_tracking_chart_process_adding_file'
)
link_active_file_tracking_chart_list_files = Link(
    args='object.id',icon_class=icon_register_list,
    text=_('Details'), view='register:active_file_tracking_chart_details'
)
link_active_file = Link(
    icon_class=icon_active_tracking,
    condition = has_chart,
    description='aaa',
    args='object.id',
    html_extra_classes='None',
    text=_('File Tracking Chart'), view='register:register_active_file_tracking_chart_details'
)
link_register_create = Link(
    icon_class=icon_register_create,
    text=_('Create new register file'), view='register:register_create'
)
link_register_multiple_set_active = Link(
    icon_class=icon_register_list,
    text=_('Set Active'), view='register:register_multiple_activate'
)
link_register_multiple_set_not_active = Link(
    icon_class=icon_register_list,
    text=_('Set Not Active'), view='register:register_multiple_deactivate'
)
link_register_multiple_transfer_out = Link(
    icon_class=icon_register_list,
    text=_('Transfer out'), view='register:register_multiple_transfer_out'
)
link_register_multiple_request_close = Link(
    icon_class=icon_register_list,
    text=_('Request Close'), view='register:register_multiple_request_close'
)
link_register_multiple_print = Link(
    icon_class=icon_register_list,
    text=_('Print'), view='register:register_multiple_print'
)
link_register_multiple_request_transfer = Link(
    icon_class=icon_register_list,
    text=_('Request Transfer'), view='register:register_multiple_request_transfer'
)
link_register_multiple_transfer = Link(
    icon_class=icon_register_list,permissions=(permission_register_create,),
    text=_('Transfer'), view='register:register_multiple_transfer'
)
link_register_list = Link(
    icon_class=icon_register_list,
    text=_('Register files'), view='register:register_list'
)


link_register_audit_list = Link(
    icon_class=icon_register_list,
    text=_('Audit Files'), view='register:register_audit_list'
)
link_register_debt_collection_list = Link(
    icon_class=icon_register_list,
    text=_('Debt Collection Files'), view='register:register_debt_collection_list'
)
link_register_general_non_billable_list = Link(
    icon_class=icon_register_list,
    text=_('General & Non-billable Files'), view='register:register_general_non_billable_list'
)
link_register_probono_list = Link(
    icon_class=icon_register_list,
    text=_('Pro Bono Files'), view='register:register_probono_list'
)
link_register_edit_group = Link(
    icon_class=icon_register_list,
    text=_('Edit Group'), view='register:register_multiple_edit_group'
)

link_register_multiple_set_dormant = Link(
    icon_class=icon_register_list,
    text=_('Set Dormant'), view='register:register_multiple_dormant'
)

link_register_statistic = Link(
    icon_class=icon_view, permissions=(permission_register_edit,),
    text=_('View statistics'), view='register:register_statistics'
)

link_register_edit = Link(
    args='object.id', icon_class=icon_register_edit, permissions=(permission_register_edit,),
    text=_('Edit'), view='register:register_edit'
)

link_register_multiple_close = Link(
    icon_class=icon_register_list, permissions=(permission_register_create,),
    text=_('CloseX'), view='register:register_multiple_request_close'
)

link_register_documents= Link(
    icon_class=icon_register_documents,
    args='object.id',
    text=_('Documents'), view='register:register_list_documents',
)

link_register_list_documents= Link(
    args='object.id',
    text=_('Related documents'), view='register:register_list_file_no_documents',
)

link_register_quotation_create = Link(
    icon_class=icon_register_create,
    text=_('Create new quotations file'), view='register:register_quotation_create'
)
link_register_quotations_list = Link(
    icon_class=icon_register_list,
    text=_('List all quotations'), view='register:register_quotations_list'
)
link_register_quotation_edit = Link(
    args='object.id', icon_class=icon_register_list, permissions=(permission_register_edit,),
    text=_('Edit'), view='register:register_quotation_edit'
)

link_register_quotation_documents= Link(
    args='object.id',
    text=_('Documents'), view='register:register_quotation_list_documents',
)
link_register_quotation_multiple_set_active = Link(
    icon_class=icon_register_list,
    text=_('Set Active'), view='register:register_quotation_multiple_activate'
)
link_register_quotation_multiple_close = Link(
    icon_class=icon_register_list,
    text=_('Close'), view='register:register_quotation_multiple_close'
)
link_register_quotation_multiple_print = Link(
    icon_class=icon_register_list,
    text=_('Print'), view='register:register_quotation_multiple_print'
)

#Department related
link_department_create = Link(
    #icon_class=icon_register_create,
    text=_('Create new department'), view='register:department_create'
)
link_department_edit = Link(
    #icon_class=icon_register_create,
    args='object.id',
    text=_('Edit'), view='register:department_edit'
)
link_department_list = Link(
    #icon_class=icon_register_create,
    text=_('List departments'), view='register:department_list'
)
link_department_list_matters = Link(
    #icon_class=icon_register_create,
    args='object.id',
    text=_('Files'), view='register:department_list_matters'
)

link_register_download = Link(
    icon_class=icon_download,
    args='object.id',
    text=_('Download'), view='register:register_download',
)
