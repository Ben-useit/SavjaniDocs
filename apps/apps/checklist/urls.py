from __future__ import unicode_literals

from django.conf.urls import url
from .views import ( ChecklistListView, selectChecklist, ChecklistView,
        ChecklistPdf,open_pdf, ChecklistDeleteView, StatusPdf
)

urlpatterns = [
    #url(r'^list/$', ChecklistListView.as_view(), name='checklist_list'),
    url(r'^(?P<pk>\d+)/$', ChecklistListView.as_view(), name='checklist'),
    url(r'^(?P<pk>\d+)/select/$', selectChecklist, name='select'),
    url(r'^(?P<pk>\d+)/view/$', ChecklistView.as_view(), name='view'),
    url(r'^(?P<pk>\d+)/pdf/$', ChecklistPdf.as_view(), name='pdf'),
    url(r'^(?P<pk>\d+)/status/pdf/$', StatusPdf.as_view(), name='status_pdf'),
    url(r'^checklist_pdf/(?P<pdf>\w+)/(?P<title>[\w\d\/\&\,\;\:\(\)\ \_\.\-\]\[\+]+)$', open_pdf, name='checklist_pdf'),
    url(r'^(?P<pk>\d+)/delete/$', ChecklistDeleteView.as_view(), name='delete'),
]


