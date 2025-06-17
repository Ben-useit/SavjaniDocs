from __future__ import absolute_import, unicode_literals

from django.apps import apps
from django.utils.translation import ugettext_lazy as _
from events import ModelEventType
from common import (
    MayanAppConfig, menu_main,menu_object, menu_multi_item,
)
from common.classes import ModelAttribute
from navigation import SourceColumn
from reports.links import link_reports_register_event
from tracking.links import link_tracking_detail

from .links import ( link_register_list, link_register_create,
    link_register_edit, link_register_documents, link_register_list_documents,
    link_register_quotation_create,link_register_quotations_list,
    link_register_quotation_edit, link_register_quotation_documents, link_register_multiple_print,
    link_register_multiple_set_active, link_register_multiple_set_not_active,
    link_register_quotation_multiple_set_active, link_register_quotation_multiple_close,
    link_register_multiple_request_close,link_register_multiple_request_transfer,
    link_register_multiple_close, link_register_multiple_transfer, link_register_statistic,
    link_register_quotation_multiple_print,
    link_register_audit_list,link_register_general_non_billable_list,
    link_register_probono_list,
    link_register_edit_group, link_register_multiple_set_dormant,
    link_department_create,link_department_edit,link_department_list,link_department_list_matters,
    link_transferred_register_file_list,
    link_register_debt_collection_list,
    link_register_download
)
from clients.links import  link_client_list as  link_client_listF
from .classes import DocumentRegisterHelper,DocumentQuotationHelper
from .menus import menu_register, menu_quotation, menu_departments
from .events import ( event_file_no_activated, event_file_no_requested,
                event_file_no_created, event_file_no_document_added,
                event_file_no_transferred, event_file_no_closed, event_file_no_not_active,
                event_file_no_transferred_to_client  )
from .widgets import StatusWidget, CheckListWidget
from events.links import (
    link_events_for_object, link_object_event_types_user_subcriptions_list
)
from .settings import register_status_choices
from django.utils.dateformat import DateFormat
from django.utils import timezone
from dateutil.parser import parser


class RegisterApp(MayanAppConfig):
    has_rest_api = False
    has_tests = False
    name = 'register'
    verbose_name = _('Register')

    def ready(self):
        super(RegisterApp, self).ready()

        from actstream import registry

        Register = self.get_model('Register')
        Quotation = self.get_model('Quotation')
        Department = self.get_model('Department')
        ActiveFileTrackingChart = self.get_model('ActiveFileTrackingChart')
        Document = apps.get_model(
            app_label='documents', model_name='Document'
        )
        Document.add_to_class(
            'register_file_no', DocumentRegisterHelper.constructor
        )
        Document.add_to_class(
            'quotation_file_no', DocumentQuotationHelper.constructor
        )
        ModelAttribute(
            Document, 'register_file_no',
            description=_(
                'Return the file number of a specific document'
            ),
        )
        ModelAttribute(
            Document, 'quotation_file_no',
            description=_(
                'Return the quotation number of a specific document'
            ),
        )
        SourceColumn(
            source=Register, label=_('Opened'),
            func=lambda context: context['object'].get_open().strftime('%d.%m.%y')
        )
        SourceColumn(
            source=Register, label=_('File No.'),
            attribute='file_no'
        )
        SourceColumn(
            source=Register, label=_('Client'),
            func=lambda context: context['object'].get_client_name()
        )
        SourceColumn(
            source=Register, label=_('Parties'),
            func=lambda context: context['object'].parties.encode('utf-8')
        )
        SourceColumn(
            source=Register, label=_('Documents'),
            func=lambda context: context['object'].get_document_count(
                user=context['request'].user
            )
        )
        SourceColumn(
            source=Register, label=_('CL'),
            #attribute='status'
            func=lambda context: CheckListWidget(
                state=context['object'].has_checklist()
            ).render()
        )
        SourceColumn(
            source=Register, label=_('Status'),
            func=lambda context: StatusWidget(
                state=context['object'].status
            ).render()
        )
        # ~ SourceColumn(
            # ~ source=Register, label=_('Status'),
            # ~ attribute='status'
        # ~ )
        SourceColumn(
            source=Register, label=_('Group'),
            func=lambda context: context['object'].group
        )
        SourceColumn(
            source=Document, label=_('Register'),attribute='file_no'
        )
        #Quotations
#        SourceColumn(
#            source=Quotation, label=_('Opened'),
#            func=lambda context: context['object'].opened.strftime('%e. %B %Y')
#        )
        SourceColumn(
            source=Quotation, label=_('Opened'),
            func=lambda context: context['object'].get_open().strftime('%e. %B %Y')
        )

        SourceColumn(
            source=Quotation, label=_('File No.'),
            attribute='file_no'
        )
        SourceColumn(
            source=Quotation, label=_('Parties'),
            func=lambda context: context['object'].parties.encode('utf-8')
        )
        SourceColumn(
            source=Quotation, label=_('Status'),
            #attribute='status'
            func=lambda context: StatusWidget(
                state=context['object'].status
            ).render()
        )
        # Department related
        SourceColumn(
            source=Department, label=_('Department'),
            attribute='name'
        )

        SourceColumn(
            source=Department, label=_('Active'),
            func=lambda context: context['object'].get_no_matters(context['request'].user,'Active')
        )
        SourceColumn(
            source=Department, label=_('Not active'),
            func=lambda context: context['object'].get_no_matters(context['request'].user,'Not active')
        )
        SourceColumn(
            source=Department, label=_('Dormant'),
            func=lambda context: context['object'].get_no_matters(context['request'].user,'Dormant')
        )

        SourceColumn(
            source=Department, label=_('Total'),
            func=lambda context: context['object'].get_no_matters(context['request'].user,'AnAD')
        )
        # Active File Tracking Chart
        SourceColumn(
            source=ActiveFileTrackingChart,label='Retain/Transfer',
            attribute='retain_or_transfer'
        )
        SourceColumn(
            source=ActiveFileTrackingChart, label=_('Closure Letter'),
            func=lambda context: context['object'].get_date(context['object'].date_closure_letter)
        )
        SourceColumn(
            source=ActiveFileTrackingChart, label=_('Client'),
            func=lambda context: context['object'].get_client_file_transferrred_to()
        )
        SourceColumn(
            source=ActiveFileTrackingChart, label=_('Instructions received'),
            func=lambda context: context['object'].get_date(context['object'].instructions)
        )
        SourceColumn(
            source=ActiveFileTrackingChart, label=_('Notice'),
            func=lambda context: context['object'].get_date(context['object'].notice)
        )
        SourceColumn(
            source=ActiveFileTrackingChart, label=_('Receipt'),
            func=lambda context: context['object'].get_date(context['object'].receipt)
        )
        SourceColumn(
            source=ActiveFileTrackingChart, label=_('Completion'),
            func=lambda context: context['object'].get_date(context['object'].date_completion)
        )
        SourceColumn(
            source=ActiveFileTrackingChart, label=_('Files'),
            func=lambda context: context['object'].get_number_of_files()
        )
        menu_register.bind_links(
            links=(
                link_register_create,link_register_list,link_register_audit_list,
                link_register_debt_collection_list,
                link_register_general_non_billable_list,
                link_register_probono_list
            )
        )
        menu_quotation.bind_links(
            links=(
                link_register_quotation_create,link_register_quotations_list,
            )
        )
        menu_departments.bind_links(
            links=(
                link_department_create,link_department_list
            )
        )
        menu_main.bind_links(links=(menu_register,menu_quotation,menu_departments), position=80)

        menu_object.bind_links(
            links=(
                link_tracking_detail,link_reports_register_event,link_register_edit,
                link_register_documents,link_register_download
            ),
            sources=(Register,)
        )
        menu_object.bind_links(
            links=(
                link_register_quotation_edit, link_register_quotation_documents,
            ),
            sources=(Quotation,)
        )
        # ~ menu_object.bind_links(
            # ~ links=(
                # ~ link_client_list_matters, link_client_delete
            # ~ ),
            # ~ sources=(Client,)
        # ~ )
        menu_object.bind_links(
            links=(
                link_department_edit,link_department_list_matters
            ),
            sources=(Department,)
        )
        menu_object.bind_links(
            links=(
                link_register_list_documents,
            ),
            sources=('documents:document_preview',)
        )
        menu_multi_item.bind_links(
            links=(
                link_register_multiple_set_active,
                link_register_multiple_set_dormant,
                link_register_multiple_set_not_active,
                link_register_multiple_request_close,
                link_register_edit_group,
                link_register_multiple_request_transfer,
                link_register_multiple_close,
                link_register_multiple_transfer,
                link_register_multiple_print
            ), sources=('register:register_list',)
        )

        menu_multi_item.bind_links(
            links = (
                link_register_quotation_multiple_set_active,link_register_quotation_multiple_close,
                link_register_quotation_multiple_print
            ), sources=(Quotation,)
        )

        ModelEventType.register(
            model=Register, event_types=(
                event_file_no_activated, event_file_no_requested,
                event_file_no_created,
                event_file_no_document_added,event_file_no_transferred,
                event_file_no_closed, event_file_no_not_active,
                event_file_no_transferred_to_client
            )
        )

        registry.register(Register)
        registry.register(Quotation)

