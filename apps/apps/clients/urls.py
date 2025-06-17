from __future__ import absolute_import, unicode_literals
from django.conf.urls import url

from .views import (
    ContactCreateView, ContactEditView, ContactDeleteView,
    ClientCreateView, ClientListView, ClientEditView, ClientDetailView,
    ClientListFilesView,
    contact
)


urlpatterns = [
    url(regex=r'^$', name='client_list', view=ClientListView.as_view()),
    url(regex=r'^external/$', name='client_list_ex', view=ClientListView.as_view()),
    url(regex=r'^print/(?P<key>\w+)/$', name='client_list_print', view=ClientListView.as_view()),
    url(regex=r'^create/$', name='client_create', view=ClientCreateView.as_view()),
    url(regex=r'^create/(?P<key>\w+)/$', name='client_create', view=ClientCreateView.as_view()),
    url(regex=r'^create/register/(?P<key>\w+)/$', name='client_create_from_register', view=ClientCreateView.as_view()),
    url(regex=r'^edit/(?P<client_pk>\d+)/$', name='client_edit', view=ClientEditView.as_view()),
    url(regex=r'^edit/(?P<client_pk>\d+)/(?P<key>\w+)/$', name='client_edit', view=ClientEditView.as_view()),
    url(regex=r'^detail/(?P<client_pk>\d+)/$', name='client_detail', view=ClientDetailView.as_view()),
    url(regex=r'^files/(?P<client_pk>\d+)/$', name='client_list_register_files', view=ClientListFilesView.as_view()),

    url(regex=r'^contact/create/$', name='contact_create', view=ContactCreateView.as_view()),
    url(regex=r'^contact/create/(?P<key>\w+)/$', name='contact_create', view=ContactCreateView.as_view()),
    url(regex=r'^contact/create/(?P<client_pk>\d+)/(?P<key>\w+)/$', name='contact_create', view=ContactCreateView.as_view()),
    url(regex=r'^contact/delete/(?P<client_pk>\d+)/(?P<contact_pk>\d+)/(?P<key>\w+)/$', name='contact_delete', view=ContactDeleteView.as_view()),
    url(regex=r'^contact/edit/(?P<contact_pk>\d+)/$', name='contact_edit', view=ContactEditView.as_view()),
    url(regex=r'^contact/edit/(?P<client_pk>\d+)/(?P<contact_pk>\d+)/(?P<key>\w+)/$', name='contact_edit', view=ContactEditView.as_view()),
    url(regex=r'^contact/$', name='contact', view=contact),

]

