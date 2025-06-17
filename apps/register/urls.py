from __future__ import unicode_literals

from django.conf.urls import url

from .views.register_views import (
    RegisterListView, RegisterListPrintView,
    RegisterCreateView, RegisterEditView, RegisterListDocumentsView,
    RegisterStatisticResultView, RegisterResultView, RegisterRequestCloseManyView,
    register_detail_view, register_list_events_view, RegisterRequestTransferManyView,
    RegisterTransferManyView, RegisterStatisticView,
    RegisterPrintManyView, RegisterEditGroupManyView, RegisterSetDormantManyView,
    RegisterAuditListView,RegisterAuditListPrintView,
    RegisterDebtCollectionFilesListView,RegisterDebtCollectionFilesPrintView,
    RegisterGeneralNonBillableListView,RegisterGeneralNonBillableListPrintView,
    RegisterProBonoListView,RegisterProBonoListPrintView,
    RegisterActivateManyView,
    RegisterDeactivateManyView,
    RegisterTransferOutManyView,
    RegisterListPrintCSVView,
    RegisterDownloadDocumentsView,
    ActiveFileTrackingChartCreate,
    ActiveFileTrackingChartEdit,
    ActiveFileTrackingChartListView,ActiveFileTrackingChartAddFileView,
    ActiveFileTrackingChartProcessAddingView,
    ActiveFileTrackingChartListFilesView,
    ActiveFileTrackingChartDetailsView

)

from .views.quotation_views import (QuotationListView,QuotationCreateView,
    QuotationEditView, QuotationListDocumentsView, quotation_detail_view,
    QuotationResultView,QuotationActivateManyView,QuotationCloseManyView,
    QuotationPrintManyView,
    QuotationListPrintView,QuotationListPrintCSVView
)

from .views.department_views import (
    DepartmentListView,DepartmentCreateView,DepartmentEditView,DepartmentListPrintView
)

from .utils import open_pdf

urlpatterns = [
    url(r'^list/$', RegisterListView.as_view(), name='register_list'),
    url(r'^list/department/(?P<department_id>\d+)/$', RegisterListView.as_view(), name='department_list_matters'),
    url(r'^list/print/(?P<key>\w+)/$', RegisterListPrintView.as_view(), name='register_list_print'),
    url(r'^list/csv/(?P<key>\w+)/$', RegisterListPrintCSVView.as_view(), name='register_list_print_csv'),
    url(r'^list/debt/$', RegisterDebtCollectionFilesListView.as_view(), name='register_debt_collection_list'),
    url(r'^list/print/debt/(?P<key>\w+)/$', RegisterDebtCollectionFilesPrintView.as_view(), name='register_debt_collection_list_print'),

    url(r'^list/audit/$', RegisterAuditListView.as_view(), name='register_audit_list'),
    url(r'^list/print/audit/(?P<key>\w+)/$', RegisterAuditListPrintView.as_view(), name='register_audit_list_print'),
    url(r'^list/general/non-billable/$', RegisterGeneralNonBillableListView.as_view(), name='register_general_non_billable_list'),
    url(r'^list/print/general/non-billable/(?P<key>\w+)/$', RegisterGeneralNonBillableListPrintView.as_view(), name='register_general_non_billable_list_print'),
    url(r'^list/probono/$', RegisterProBonoListView.as_view(), name='register_probono_list'),
    url(r'^list/print/probono/(?P<key>\w+)/$', RegisterProBonoListPrintView.as_view(), name='register_probono_list_print'),

    url(r'^list/(?P<id_list>\w+)/$', RegisterListView.as_view(), name='register_list'),
    url(r'^(?P<pk>\d+)/edit/(?P<req_id>\d+)/$', RegisterEditView.as_view(), name='register_edit'),
    url(r'^(?P<register_pk>\d+)/edit/$', RegisterEditView.as_view(), name='register_edit'),
    url(r'^create/$', RegisterCreateView.as_view(), name='register_create'),
    url(r'^create/(?P<key>\w+)/$', RegisterCreateView.as_view(), name='register_create'),
    url(r'^statistics/$', RegisterStatisticView.as_view(), name='register_statistics'),
    #url(r'^statistics/(?P<lawyer_ids>\w+)/$', register_statistic_view , name='register_statistics_view'),
    #url(r'^statistics/(?P<lawyer_ids>\w+)/$', RegisterStatisticResultView.as_view() , name='register_statistics_view'),
    url(r'^statistics/(?P<lawyer_ids>\w+)/(?P<year_from>\d+)/(?P<month_from>\d+)/(?P<day_from>\d+)/(?P<year_to>\d+)/(?P<month_to>\d+)/(?P<day_to>\d+)/$', RegisterStatisticResultView.as_view(), name='register_statistics_view'),
    url(r'^statistics/print/$', RegisterStatisticResultView.as_view(), name='register_statistics_view'),

    url(r'^(?P<pk>\d+)/list/$', RegisterListDocumentsView.as_view(), name='register_list_documents'),
    url(r'^(?P<pk>\d+)/download/$', RegisterDownloadDocumentsView.as_view(), name='register_download'),
    url(r'^(?P<id>\d+)/register/list/$', RegisterListDocumentsView.as_view(), name='register_list_file_no_documents'),
    url(r'^register_search/', RegisterResultView.as_view(), name = 'register_search'),
    url(r'^quotation_search/', QuotationResultView.as_view(), name = 'quotation_search'),
    url(r'^(?P<pk>\d+)/detail/$', register_detail_view, name='register_detail'),
    url(r'^(?P<pk>\d+)/events/$', register_list_events_view, name='register_list_events_view'),
    url(r'^list/quotations$', QuotationListView.as_view(), name='register_quotations_list'),
    url(r'^list/quotations/print/(?P<key>\w+)/$', QuotationListPrintView.as_view(), name='register_quotations_print'),
    url(r'^list/quotations/csv/(?P<key>\w+)/$', QuotationListPrintCSVView.as_view(), name='register_quotations_print_csv'),

    url(r'^create/new/quotation/$', QuotationCreateView.as_view(), name='register_quotation_create'),
    url(r'^(?P<pk>\d+)/quotation/(?P<req_id>\d+)/edit/$', QuotationEditView.as_view(), name='register_quotation_edit'),
    url(r'^(?P<pk>\d+)/quotation/edit/$', QuotationEditView.as_view(), name='register_quotation_edit'),
    url(r'^(?P<pk>\d+)/quotation/list/$', QuotationListDocumentsView.as_view(), name='register_quotation_list_documents'),
    url(r'^(?P<pk>\d+)/quotation/detail/$', quotation_detail_view, name='register_quotation_detail'),
    # Register related
    url(r'^multiple/activate/$', RegisterActivateManyView.as_view(), name='register_multiple_activate'),
    url(r'^multiple/print/$', RegisterPrintManyView.as_view(), name='register_multiple_print'),
    url(r'^multiple/deactivate/$', RegisterDeactivateManyView.as_view(), name='register_multiple_deactivate'),
    url(r'^multiple/transfer_out/$', RegisterTransferOutManyView.as_view(), name='register_multiple_transfer_out'),
    url(r'^multiple/request_close/$', RegisterRequestCloseManyView.as_view(), name='register_multiple_request_close'),
    url(r'^multiple/request_transfer/$', RegisterRequestTransferManyView.as_view(), name='register_multiple_request_transfer'),
    url(r'^multiple/request_change_group/$', RegisterEditGroupManyView.as_view(), name='register_multiple_edit_group'),
    url(r'^multiple/request_dormant/$', RegisterSetDormantManyView.as_view(), name='register_multiple_dormant'),
    url(r'^multiple/transfer/(?P<id_list>\w+)/$', RegisterRequestTransferManyView.as_view(), name='register_multiple_transfer'),
    url(r'^multiple/transfer/$', RegisterTransferManyView.as_view(), name='register_multiple_transfer'),
    # ~ # Quotation related
    url(r'^multiple/quotation/activate/$', QuotationActivateManyView.as_view(), name='register_quotation_multiple_activate'),
    url(r'^multiple/quotation/close/$', QuotationCloseManyView.as_view(), name='register_quotation_multiple_close'),
    url(r'^report_pdf/(?P<pdf>\w+)/(?P<title>[-a-zA-Z0-9_&]+)/$', open_pdf, name='report_pdf'),
    url(r'^multiple/quotation/print/$', QuotationPrintManyView.as_view(), name='register_quotation_multiple_print'),

    # department related
    url(r'^department/list/$', DepartmentListView.as_view(), name='department_list'),
    url(r'^department/list/print/(?P<key>\w+)/$', DepartmentListPrintView.as_view(), name='department_list_print'),
    #url(r'^list/(?P<id_list>\w+)/$', RegisterListView.as_view(), name='register_list'),
    #url(r'^client/(?P<pk>\d+)/edit/(?P<req_id>\d+)/$', RegisterEditView.as_view(), name='register_edit'),
    url(r'^department/(?P<pk>\d+)/edit/$', DepartmentEditView.as_view(), name='department_edit'),
    url(r'^department/create/$', DepartmentCreateView.as_view(), name='department_create'),
    #url(r'^department/(?P<pk>\d+)/matters/$', DepartmentListMatterView.as_view(), name='department_list_matters'),
    #print
    #url(r'^client/list/print/(?P<key>\w+)$', ClientListPrintView.as_view(),name='client_list_print'),
    #url(r'^client/list/print/(?P<pdf>\w+)/(?P<title>\w+)$',client_list_print ,name='client_list_print'),

    # Transferred Files
    url(r'^aftc/list/$', ActiveFileTrackingChartListView.as_view(), name='active_file_tracking_chart_list'),
    url(r'^aftc/create/$', ActiveFileTrackingChartCreate.as_view(), name='active_file_tracking_chart_create'),
    url(r'^aftc/(?P<pk>\d+)/edit/$', ActiveFileTrackingChartEdit.as_view(), name='active_file_tracking_chart_edit'),
    url(r'^aftc/(?P<pk>\d+)/add/file/$', ActiveFileTrackingChartAddFileView.as_view(), name='active_file_tracking_chart_add_file'),
    url(r'^aftc/(?P<pk>\d+)/process/adding/file/$', ActiveFileTrackingChartProcessAddingView.as_view(), name='active_file_tracking_chart_process_adding_file'),
    url(r'^aftc/(?P<pk>\d+)/list/files/$',ActiveFileTrackingChartListFilesView.as_view(), name='active_file_tracking_chart_list_files'),
    url(r'^aftc/(?P<aftc_pk>\d+)/details/$',ActiveFileTrackingChartDetailsView.as_view(), name='active_file_tracking_chart_details'),
    url(r'^aftc/reg/(?P<reg_pk>\d+)/details/$',ActiveFileTrackingChartDetailsView.as_view(), name='register_active_file_tracking_chart_details')

]


