from __future__ import unicode_literals

from django.conf.urls import url

from .views import (
    UploadReportView,UploadReportPrintView,
    ActivityView, UserActivityView, EventsView, RegisterFilesReportView,
    LawyerActivity, RegisterTransferReportView, RegisterTransferPrintView,
    transfer_pdf
)

urlpatterns = [
    url(r'^upload/$', UploadReportView.as_view(), name='upload_report'),
    url(r'^upload/print/(?P<key>\w+)$', UploadReportPrintView.as_view(), name='upload_report_print'),

    url(r'^activity/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/$', ActivityView.as_view(), name='activity'),
    url(r'^activity/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<user_pk>\d+)/$', UserActivityView.as_view(), name='user_activity'),
    url(r'^activity/current/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/$', UserActivityView.as_view(), name='current_user_activity'),
    url(r'^activity/current/$', UserActivityView.as_view(), name='current_user_activity'),
    url(r'^activity/$', ActivityView.as_view(), name='activity'),
    url(r'^register/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<lawyer_ids>[\d,]+)/$', RegisterFilesReportView.as_view(), name='register_files_report'),
    url(r'^register/$', RegisterFilesReportView.as_view(), name='register_files_report'),
    url(r'^register/print/(?P<key>\w+)/$', RegisterFilesReportView.as_view(), name='register_files_report_print'),
    url(r'^actiyity/lawyer/$', LawyerActivity.as_view(), name='activity_lawyer'),
    url(r'^actiyity/lawyer/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<user_pk>\d+)/$', LawyerActivity.as_view(), name='activity_lawyer'),
    url(r'^events/(?P<object_pk>\d+)/$', EventsView.as_view(), name='events'),
    url(r'^transfers/$', RegisterTransferReportView.as_view(), name='register_transfer'),
    url(r'^transfers/print/(?P<key>\w+)$', RegisterTransferPrintView.as_view(), name='register_transfer_print'),
    url(r'^transfers/pdf/(?P<pdf>\w+)/(?P<title>\w+)$', transfer_pdf, name='transfer_pdf'),
]

