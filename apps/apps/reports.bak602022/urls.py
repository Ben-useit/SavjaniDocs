from __future__ import unicode_literals

from django.conf.urls import url

from .views import (
    ActivityView, UserActivityView, EventsView, RegisterStatisticView,
    LawyerActivity, RegisterTransferReportView, RegisterTransferPrintReportView
)

urlpatterns = [
    url(r'^activity/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/$', ActivityView.as_view(), name='activity'),
    url(r'^activity/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<user_pk>\d+)/$', UserActivityView.as_view(), name='user_activity'),
    url(r'^activity/current/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/$', UserActivityView.as_view(), name='current_user_activity'),
    url(r'^activity/current/$', UserActivityView.as_view(), name='current_user_activity'),
    url(r'^activity/$', ActivityView.as_view(), name='activity'),
    url(r'^register/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<lawyer_ids>[\d,]+)/$', RegisterStatisticView.as_view(), name='register_statistics'),
    url(r'^register/$', RegisterStatisticView.as_view(), name='register_statistics'),
    url(r'^actiyity/lawyer/$', LawyerActivity.as_view(), name='activity_lawyer'),
    url(r'^actiyity/lawyer/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<user_pk>\d+)/$', LawyerActivity.as_view(), name='activity_lawyer'),
    url(r'^events/(?P<object_pk>\d+)/$', EventsView.as_view(), name='events'),
    url(r'^actiyity/transfers/$', RegisterTransferReportView.as_view(), name='register_transfer'),
    url(r'^actiyity/transfers/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<lawyer_ids>[\d,]+)/$', RegisterTransferReportView.as_view(), name='register_transfer'),
    url(r'^actiyity/transfers/(?P<date_from>\d{2}.\d{2}.\d{4})/(?P<date_to>\d{2}.\d{2}.\d{4})/(?P<lawyer_ids>[\d,]+)/print/$', RegisterTransferPrintReportView.as_view(), name='register_transfer_print'),
]
    # ~ url(r'^create/$', TagCreateView.as_view(), name='tag_create'),
    # ~ url(
        # ~ r'^(?P<pk>\d+)/delete/$', TagDeleteActionView.as_view(),
        # ~ name='tag_delete'
    # ~ ),
    # ~ url(r'^(?P<pk>\d+)/edit/$', TagEditView.as_view(), name='tag_edit'),
    # ~ url(
        # ~ r'^(?P<pk>\d+)/documents/$', TagTaggedItemListView.as_view(),
        # ~ name='tag_tagged_item_list'
    # ~ ),
    # ~ url(
        # ~ r'^multiple/delete/$', TagDeleteActionView.as_view(),
        # ~ name='tag_multiple_delete'
    # ~ ),

    # ~ url(
        # ~ r'^multiple/remove/document/(?P<pk>\d+)/$',
        # ~ TagRemoveActionView.as_view(),
        # ~ name='single_document_multiple_tag_remove'
    # ~ ),
    # ~ url(
        # ~ r'^multiple/remove/document/multiple/$',
        # ~ TagRemoveActionView.as_view(),
        # ~ name='multiple_documents_selection_tag_remove'
    # ~ ),

    # ~ url(
        # ~ r'^selection/attach/document/(?P<pk>\d+)/$',
        # ~ TagAttachActionView.as_view(), name='tag_attach'
    # ~ ),
    # ~ url(
        # ~ r'^selection/attach/document/multiple/$',
        # ~ TagAttachActionView.as_view(), name='multiple_documents_tag_attach'
    # ~ ),

    # ~ url(
        # ~ r'^document/(?P<pk>\d+)/tags/$', DocumentTagListView.as_view(),
        # ~ name='document_tags'
    # ~ ),
# ~ ]

# ~ api_urls = [
    # ~ url(
        # ~ r'^tags/(?P<pk>[0-9]+)/documents/$', APITagDocumentListView.as_view(),
        # ~ name='tag-document-list'
    # ~ ),
    # ~ url(r'^tags/(?P<pk>[0-9]+)/$', APITagView.as_view(), name='tag-detail'),
    # ~ url(r'^tags/$', APITagListView.as_view(), name='tag-list'),
    # ~ url(
        # ~ r'^documents/(?P<document_pk>[0-9]+)/tags/$',
        # ~ APIDocumentTagListView.as_view(), name='document-tag-list'
    # ~ ),
    # ~ url(
        # ~ r'^documents/(?P<document_pk>[0-9]+)/tags/(?P<pk>[0-9]+)/$',
        # ~ APIDocumentTagView.as_view(), name='document-tag-detail'
    # ~ ),
# ~ ]
