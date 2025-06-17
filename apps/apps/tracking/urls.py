from __future__ import unicode_literals

from django.conf.urls import url

from .views import (
    TrackingListView, TrackingListPrintView,
    StartTrackingManyView, TrackingEditView,
    RetainOrTransferEditManyView,
    ClosureLetterEditManyView,InstructionsEditManyView,
    ClientEditManyView, NoticeEditManyView, ReceiptEditManyView,
    CompletionEditManyView, TrackingDetailView,
    TrackingDeleteView, StopTrackingManyView
)


urlpatterns = [
    url(r'^list/(?P<key>\w+)/$', TrackingListView.as_view(), name='tracking_list'),
    url(r'^list/$', TrackingListView.as_view(), name='tracking_list'),
    url(r'^list/print/(?P<key>\w+)/$', TrackingListPrintView.as_view(), name='tracking_list_print'),
    url(r'^list/csv/(?P<key>\w+)/$', TrackingListView.as_view(), name='tracking_list_csv'),
    url(r'^(?P<pk>\d+)/edit/$', TrackingEditView.as_view(), name='tracking_edit'),
    url(r'^(?P<pk>\d+)/delete/$', TrackingDeleteView.as_view(), name='tracking_delete'),
    url(r'^(?P<pk>\d+)/detail/$', TrackingDetailView.as_view(), name='tracking_detail'),
    url(r'^list/(?P<id_list>\w+)/$', TrackingListView.as_view(), name='tracking_list'),
    url(r'^multiple/add_tracking/$', StartTrackingManyView.as_view(), name='track_file'),
    url(r'^multiple/retain_or_transfer/$', RetainOrTransferEditManyView.as_view(), name='retain_or_transfer'),
    url(r'^multiple/closure_letter/$', ClosureLetterEditManyView.as_view(), name='closure_letter'),
    url(r'^multiple/instructions/$', InstructionsEditManyView.as_view(), name='instructions'),
    url(r'^multiple/client/$', ClientEditManyView.as_view(), name='client'),
    url(r'^multiple/notice/$', NoticeEditManyView.as_view(), name='notice'),
    url(r'^multiple/receipt/$', ReceiptEditManyView.as_view(), name='receipt'),
    url(r'^multiple/completion/$', CompletionEditManyView.as_view(), name='completion'),
    url(r'^multiple/stop_tracking/$', StopTrackingManyView.as_view(), name='stop_tracking'),

]


