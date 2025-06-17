from __future__ import absolute_import, unicode_literals
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from common.views import (
    SingleObjectListView, SingleObjectCreateView,
    SingleObjectEditView
)
from register.forms import RegisterEntryCreateForm
from .forms import ContactCreateForm
#from .models import Client, Contact
from .models import ClientA, Contact
from .permissions import permission_client_create, permission_client_view

class ContactCreateView(SingleObjectCreateView):
    #fields = ('name', 'address', 'city', 'phone', 'email','client')
    extra_context = {'title': _('Create Contact')}
    model = Contact
    form_class = ContactCreateForm
    view_permission = permission_client_create
    post_action_redirect = reverse_lazy(viewname='clients:contact_list')

    # ~ def get_instance_extra_data(self):
        # ~ return {
            # ~ '_event_actor': self.request.user
        # ~ }

class ContactEditView(SingleObjectCreateView):
    fields = ('name', 'address', 'city', 'phone', 'email','client')
    extra_context = {'title': _('Create Contact')}
    model = Contact
    view_permission = permission_client_create
    post_action_redirect = reverse_lazy(viewname='clients:contact_list')

class ContactListView(SingleObjectListView):
    object_permission = permission_client_view
    client_model = Contact

    def get_extra_context(self):
        return {
            'hide_link': True,
            'hide_object': True,
            'no_results_text': _(
                ''
            ),
            'no_results_title': _('No contacts available'),
            'title': _('Contacts'),
        }

    def get_object_list(self):
        return Contact.objects.all()


class ClientCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create Client')}
    fields = ('name',)
    model = ClientA
    post_action_redirect = reverse_lazy(viewname='clients:client_list')
    view_permission = permission_client_create
    #template_name = 'clients/generic_form.html'

    def get_instance_extra_data(self):
        return {
            '_event_actor': self.request.user
        }

class ClientEditView(SingleObjectEditView):
    fields = ('name',)
    model = ClientA
    pk_url_kwarg = 'client_pk'
    post_action_redirect = reverse_lazy(viewname='clients:client_list')
    view_permission = permission_client_create

    def get_extra_context(self):
        return {
            'title': _('Edit client: %s') % self.object,
        }
    def get_instance_extra_data(self):
        return {
            '_event_actor': self.request.user
        }

class ClientListView(SingleObjectListView):
    object_permission = permission_client_view
    client_model = ClientA

    def get_extra_context(self):
        return {
            'hide_link': True,
            'hide_object': True,
            'no_results_text': _(
                ''
            ),
            'no_results_title': _('No clients available'),
            'title': _('Clients'),
        }

    def get_object_list(self):
        return Client.objects.all()
