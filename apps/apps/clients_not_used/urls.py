from django.conf.urls import url

from .views import (
    ContactCreateView,ContactListView, ContactEditView
    ClientCreateView, ClientListView, ClientEditView,
    ContactListView, ContactEditView
)


urlpatterns = [
    url(regex=r'^$', name='client_list', view=ClientListView.as_view()),
    url(regex=r'^create/$', name='client_create', view=ClientCreateView.as_view()),
    url(regex=r'^contact/create/$', name='contact_create', view=ContactCreateView.as_view()),
    url(regex=r'^contact/$', name='contact_list', view=ContactListView.as_view()),
    url(regex=r'^(?P<client_pk>\d+)/edit/$', name='client_edit', view=ClientEditView.as_view()),
    url(regex=r'^contact/(?P<contact_pk>\d+)/edit/$', name='client_edit', view=ContactEditView.as_view()),

]

