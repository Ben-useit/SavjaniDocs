from __future__ import absolute_import, unicode_literals

import logging
import time
import datetime
import operator
import uuid

from django.db.models import Q
from dynamic_search.icons import icon_search_submit
from dynamic_search.settings import setting_limit
import shlex

from django.http import Http404
from django.views.generic import (
    DetailView,
)
from django.db.models import Count
from django.core.cache import cache
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _, ungettext
from django.views.generic.edit import CreateView
from django.views.generic import TemplateView
from django.template import RequestContext
from acls.models import AccessControlList
from common.forms import ChoiceForm
from common.icons import icon_assign_remove_add, icon_assign_remove_remove
from common.generics import ConfirmView, SimpleView
from common.views import (
    SingleObjectCreateView, SingleObjectListView, SingleObjectEditView,
    SingleObjectDeleteView
)


from dynamic_search.mixins import SearchModelMixin
from .settings import ( register_status_choices, access_choices )

from django.http import QueryDict
from urlparse import urlparse, urlunparse
from dateutil.parser import parse

from common.utils import get_aware_str_from_unaware
from user_management.views import GroupMembersView
from common.mixins import ( ObjectNameMixin,ViewPermissionCheckMixin,ExtraContextMixin,RedirectionMixin,FormExtraKwargsMixin,
    ObjectPermissionCheckMixin )
from permissions.models import Permission, StoredPermission, Role
from documents.models import Document
from documents.permissions import permission_document_view
from .models import Register, Quotation, Client, Department, Contact
from register.permissions import (
    permission_register_view, permission_register_edit, permission_register_create,
    permission_client_create, permission_client_view
)
from .forms import ( RegisterEntryCreateForm, RegisterEntryEditForm, RegisterSearchForm,
    QuotationEntryCreateForm, QuotationEntryEditForm, QuotationSearchForm, FilterForm,
    RegisterRequestTransferForm, RegisterStatisticForm, RegisterEditGroupForm,
    ClientFilterForm, ContactCreateForm)
from .tasks import ( send_register_request_mail,send_register_request_confirmation_mail,
    send_quotation_request_mail,send_quotation_request_confirmation_mail,
    send_register_request_transfer_mail, send_register_request_close_mail )
from .links import link_register_create, link_register_quotation_create
from .icons import icon_document_list, icon_register
from .events import ( event_file_no_created,event_file_no_requested,event_file_no_activated,
    event_file_no_transferred, event_file_no_closed, event_file_no_not_active,
    event_file_no_transferred_to_client, event_file_no_dormant )

from sapitwa.tasks import add_entry_to_option_list, remove_entry_from_option_list
from sapitwa.utils import get_now
from django.urls import reverse
import dateutil.parser
import json
from .tasks import create_report, create_statistic_report, create_client_report
from django.http import FileResponse

logger = logging.getLogger(__name__)
from register.settings import abbr
from sapitwa.tasks import task_add_rw_permissions
# Contact
class ContactCreateView(SingleObjectCreateView):
    #fields = ('name', 'address', 'city', 'phone', 'email','client')
    extra_context = {'title': _('Create Contact')}
    model = Contact
    form_class = ContactCreateForm
    view_permission = permission_client_create
    post_action_redirect = reverse_lazy(viewname='register:contact_list')

    # ~ def get_instance_extra_data(self):
        # ~ return {
            # ~ '_event_actor': self.request.user
        # ~ }

class ContactEditView(SingleObjectCreateView):
    fields = ('name', 'phone', 'email')#,'client')
    extra_context = {'title': _('Create Contact')}
    model = Contact
    view_permission = permission_client_create
    post_action_redirect = reverse_lazy(viewname='register:contact_list')

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


#Department
class DepartmentCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create new department')}
    model = Department
    fields = ['name']
    post_action_redirect = reverse_lazy('register:department_list')

class DepartmentListView(SearchModelMixin,SingleObjectListView):

    template_name = 'register/client_list.html'
    def get_object_list(self):
        return Department.objects.all().order_by('name')

    def get_extra_context(self):
        regs = Register.objects.exclude(department=None)
        return {
            'hide_object' : True,
            'hide_link': True,
            'no_results_title': _('No departments.'),
            'title': _('Departments:'),
            'total_matters' : regs.count(),
            'total_active' : regs.filter(status='Active').count(),
            'total_not_active' : regs.filter(status='Not active').count(),
            'total_dormant' : regs.filter(status='Dormant').count(),
            'total_closed' : regs.filter(status='Closed').count(),
            'total_transferred_to_client' : regs.filter(status='Transferred to client').count(),
        }

class DepartmentEditView(SingleObjectEditView):
    model = Department
    fields = ['name']


class DeleteDepartmentListMatterView(SingleObjectListView):
    queryset_slice = None
    def dispatch(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            department = Department.objects.get(pk=kwargs['pk'])
        elif 'id' in kwargs:
            document =  get_object_or_404(Document,pk=kwargs['id'])
            register_entry = document.register.first()
            if not register_entry:
                #search for quotations
                register_entry = document.quotation_set.first()
                self.base_object = 'Quotation Number'
                if not register_entry:
                    self.queryset = Document.objects.none()
                    #raise Http404
                    self.base_object = None
                    return super(
                        RegisterListDocumentsView, self
                    ).dispatch(request, *args, **kwargs)
        self.department = department
        queryset = self.department.register_set.all()
        self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):

        try:
            return super(ClientListMatterView, self).get_context_data(**kwargs)
        except Exception as exception:
            messages.error(
                self.request, _(
                    'Error retrieving document list: %(exception)s.'
                ) % {
                    'exception': exception
                }
            )
            self.object_list = Register.objects.none()
            return super(self.departmenttListMatterView, self).get_context_data(**kwargs)

    def get_extra_context(self):
        title = _('Matters')
        return {
            'hide_links': True,
            'list_as_items': True,
            'no_results_icon': icon_document_list,
            'no_results_text': _(
                'This could mean that no documents have been uploaded or '
                'that your user account has not been granted the view '
                'permission for any document or document type.'
            ),
            'no_results_title': _('No matters available'),
            'title': title,
        }

    def get_success_url(self):
        matters =','.join([str(int) for int in self.queryset.values_list('id', flat=True)])
        return reverse_lazy('register:register_list', kwargs={'id_list': matters.replace(',','_')})


# Client
class ClientCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create new client')}
    model = Client
    #form_class = RegisterEntryCreateForm
    fields = ['name']
    post_action_redirect = reverse_lazy('register:client_list')

class ClientListView1(SearchModelMixin,SingleObjectListView):
    template_name = 'register/client_list.html'

    def get_object_list(self):
        self.total = Client.objects.all().count()
        return Client.objects.all().order_by('name')

    def get_extra_context(self):
        regs = Register.objects.exclude(client=None)
        return {
            'hide_object' : True,
            'hide_link': True,
            'no_results_title': _('No clients.'),
            'title': _('Clients:'),
            'total' : self.total,
            'timestamp' : timezone.now(),
            'total_matters' : regs.count(),
            'total_active' : regs.filter(status='Active').count(),
            'total_not_active' : regs.filter(status='Not active').count(),
            'total_dormant' : regs.filter(status='Dormant').count(),
            'total_closed' : regs.filter(status='Closed').count(),
            'total_transferred_to_client' : regs.filter(status='Transferred to client').count(),
        }

class ClientListPrintView(SimpleView):

    def dispatch(self,request,*args,**kwargs):
        key = kwargs.pop('key', None)
        data = cache.get(key)
        title = 'List of clients'
        pdf =create_client_report(data, title)
        return HttpResponseRedirect(reverse('register:client_list_print', kwargs={'pdf':pdf,'title':title.replace(' ','_')}))

from django.http import FileResponse
def client_list_print(response,pdf,title):
    pdf = open('/tmp/'+pdf, 'rb')
    response = FileResponse(pdf)
    title = title.replace('_',' ')+".pdf"
    response['Content-Disposition'] = "attachment; filename=\""+title+"\""
    return response

class ClientListView(SearchModelMixin,SingleObjectListView):
    filter_dic = {}
    total = 0
    query_request = None
    print_result = False
    id_list = None
    form = ClientFilterForm
    register_edit_permission = False
    clients_for = ''
    has_permission_register_edit = False
    template_name = 'register/client_list.html'

    def dispatch(self, request, *args, **kwargs):
        self.query_dict = self.request.GET.copy()
        self.search_q = self.query_dict.get('search_q', uuid.uuid4().hex)
        self.items = self.request.GET
        self.form = ClientFilterForm(user = self.request.user)
        self.has_permission_register_edit = permission_register_edit.stored_permission.user_has_this(user=self.request.user)
        if 'id_list' in kwargs:
            self.id_list = kwargs['id_list'].split('_')

        return super(ClientListView, self).dispatch(request, *args, **kwargs)

    def get_paginate_by(self, queryset):
        return 500

    def get_extra_context(self):
        if len(self.qs) == 1:
            title = _('Client')
        else:
            title = _('Clients')


        return {
            'search_q' : self.search_q,
            'print_url': reverse_lazy('register:client_list_print', kwargs={'key': self.search_q }),
            'total' : len(self.qs),
            'form' : self.form,
            'hide_object' : True,
            'hide_link': True,
            'no_results_icon': icon_register,
            'no_results_title': _('No clients.'),
            'title': title,
            'clients' : self.qs,
            'totals' : self.totals,
            'clients_for' : self.clients_for,
            'permission_edit' : self.has_permission_register_edit,
            # ~ 'total_matters' : self.totals[0], #self.regs.filter(contacts__in=self.contacts).count(),
            # ~ 'total_active' : self.totals[1], #self.regs.filter(status='Active',contacts__in=self.contacts).count(),
            # ~ 'total_not_active' : self.totals[2], #self.regs.filter(status='Not active',contacts__in=self.contacts).count(),
            # ~ 'total_dormant' : self.totals[3], #self.regs.filter(status='Dormant',contacts__in=self.contacts).count(),
            # ~ 'total_closed' : self.totals[4], #self.regs.filter(status='Closed',contacts__in=self.contacts).count(),
            # ~ 'total_transferred_to_client' : self.totals[5], #self.regs.filter(status='Transferred to client',contacts__in=self.contacts).count(),

        }

    def get_object_list(self):
        lawyers = self.request.GET.getlist('lawyers')
        user = self.request.user
        regs = AccessControlList.objects.filter_by_access(permission=permission_register_view,
            user=user, queryset=Register.objects.exclude(contacts=None))
        if lawyers:
            users = []
            filtered_regs = Register.objects.none()
            for lawyer in lawyers:
                user = User.objects.filter(first_name=lawyer.split(' ')[0],last_name=lawyer.split(' ')[1]).first()
                users.append(user)
                regs_acl = AccessControlList.objects.filter_by_access(permission=permission_register_view,
                    user=user, queryset=regs)
                filtered_regs = filtered_regs | regs_acl
            regs = filtered_regs
            self.clients_for = '; '.join(u.get_full_name() for u in users)
        # ~ '''
        # ~ Get the name of the lawyer in case no lawyers have been selected
        # ~ If user is superuser: All
        # ~ If user has global register_view_permissions: All
        # ~ If normal user, display reg.lawyers.first()
        # ~ '''
        else:
            if self.has_permission_register_edit:
                self.has_permission_register_edit = True
                self.clients_for = 'All'
            else:
                if regs:
                    reg = regs.exclude(lawyers = None).first()
                    if reg:
                        self.clients_for = reg.lawyers.first().get_full_name()
            users = [user,]





        contacts = Contact.objects.filter(register__in=regs).distinct()
        clients = Client.objects.filter(contact__in=contacts).distinct()
        has_filter = False
        if 'name' in self.request.GET:
            has_filter = True
            query = self.request.GET['name'].split(' ')
            clients =clients.filter(reduce(operator.or_, (Q(name__icontains=x) for x in query)))
            contacts = contacts.filter(client__in=clients)
            regs = regs.filter(contacts__in=contacts)
        status = []
        #return self.queryset.order_by('name') # These are clients
        for k, v in self.items.iteritems():
            has_filter = True
            if k!= 'lawyers' and k != 'name' and k!= 'search_q' and k != 'csrfmiddlewaretoken' and k != 'submit':
                status.append(k)

        if status:
            regs = regs.filter(reduce(operator.or_, (Q(status__contains=x) for x in status ))).distinct()
            contacts = Contact.objects.filter(register__in=regs).distinct()
            clients = Client.objects.filter(contact__in=contacts).distinct()

        self.qs = []
        self.totals = [ 'Total: ',0,0,0,0,0,0]
        for client in clients.order_by('name'):
            total = client.get_no_matters_filtered(users)
            active = client.get_no_matters_filtered(users,status="Active")
            not_active = client.get_no_matters_filtered(users,status="Not active")
            dormant = client.get_no_matters_filtered(users,status="Dormant")
            closed = client.get_no_matters_filtered(users,status="Closed")
            misc = client.get_no_misc_matters(users)
            self.qs.append([client,total,active,not_active,dormant,closed,misc])
            self.totals[1] += total
            self.totals[2] += active
            self.totals[3] += not_active
            self.totals[4] += dormant
            self.totals[5] += closed
            self.totals[6] += misc
        cache.set(self.search_q,[self.qs,self.totals,self.clients_for])
        return self.qs

        if self.request.user.is_superuser:
            if lawyers:
                regs = Register.objects.exclude(contacts=None)
                filtered_regs = Register.objects.none()
                for lawyer in lawyers:
                    user = User.objects.filter(first_name=lawyer.split(' ')[0],last_name=lawyer.split(' ')[1]).first()
                    regs = AccessControlList.objects.filter_by_access(permission=permission_register_view,
                        user=user, queryset=regs)
                    filtered_regs = filtered_regs | regs
                contacts = Contact.objects.filter(register__in=filtered_regs).distinct()
                clients = Client.objects.filter(contact__in=contacts).distinct()
                regs = filtered_regs
            else:
                clients = Client.objects.all()
                regs = Register.objects.exclude(contacts=None)
                contacts = Contact.objects.filter(register__in=regs).distinct()
        else:
            regs = AccessControlList.objects.filter_by_access(permission=permission_register_view,
                user=self.request.user, queryset=Register.objects.exclude(contacts=None))
            contacts = Contact.objects.filter(register__in=regs).distinct()
            clients = Client.objects.filter(contact__in=contacts).distinct()
        has_filter = False
        self.all_regs = regs
        if 'name' in self.request.GET:
            has_filter = True
            query = self.request.GET['name'].split(' ')
            clients =clients.filter(reduce(operator.or_, (Q(name__icontains=x) for x in query)))
            contacts = contacts.filter(client__in=clients)
            regs = regs.filter(contacts__in=contacts)
        status = []
        #return self.queryset.order_by('name') # These are clients
        for k, v in self.items.iteritems():
            has_filter = True
            if k!= 'lawyers' and k != 'name' and k!= 'search_q' and k != 'csrfmiddlewaretoken' and k != 'submit':
                status.append(k)

        if status:
            regs = regs.filter(reduce(operator.or_, (Q(status__contains=x) for x in status ))).distinct()
            contacts = Contact.objects.filter(register__in=regs).distinct()
            clients = Client.objects.filter(contact__in=contacts).distinct()
        #if has_filter:
        self.form = ClientFilterForm(self.request.GET, user=self.request.user )
        # totals are calculated on basis client
        contacts = Contact.objects.filter(client__in=clients).distinct()
        regs = self.all_regs.filter(contacts__in=contacts)
        self.totals = []
        self.totals.append(regs.count())
        self.totals.append(regs.filter(status='Active').count())
        self.totals.append(regs.filter(status='Not active').count())
        self.totals.append(regs.filter(status='Dormant').count())
        self.totals.append(regs.filter(status='Closed').count())
        self.totals.append(self.totals[0]-self.totals[1]-self.totals[2]-self.totals[3]-self.totals[4])
        cache.set(self.search_q,[clients.order_by('name'),self.totals])
        self.total = clients.count()
        self.contacts = contacts
        self.regs = regs
        return clients.order_by('name')

class ClientEditView(SingleObjectEditView):
    model = Client
    fields = ['name','contact','phone','email','clients']
    post_action_redirect = reverse_lazy('register:client_list')

class ClientDeleteView(SingleObjectDeleteView):
    model = Client
    object_permission = permission_register_create
    post_action_redirect = reverse_lazy('register:client_list')

    def get_extra_context(self):
        return {
            'delete_view': True,
            'object': self.get_object(),
            'title': _('Delete the client: %s?') % self.get_object(),
        }

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        registers = Register.objects.filter(clients=self.object)
        for r in registers:
            r.client = None
            r.save()
        context = self.get_context_data()
        object_name = self.get_object_name(context=context)

        try:
            result = super(SingleObjectDeleteView, self).delete(request, *args, **kwargs)
        except Exception as exception:
            messages.error(
                self.request,
                _('%(object)s not deleted, error: %(error)s.') % {
                    'object': object_name,
                    'error': exception
                }
            )

            raise exception
        else:
            messages.success(
                self.request,
                _(
                    '%(object)s deleted successfully.'
                ) % {'object': object_name}
            )

            return result

class ClientListMatterView(SingleObjectListView):
    queryset_slice = None
    #base_object = 'File Number'
    def dispatch(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            client = Client.objects.get(pk=kwargs['pk'])
        elif 'id' in kwargs:
            document =  get_object_or_404(Document,pk=kwargs['id'])
            register_entry = document.register.first()
            if not register_entry:
                #search for quotations
                register_entry = document.quotation_set.first()
                self.base_object = 'Quotation Number'
                if not register_entry:
                    self.queryset = Document.objects.none()
                    #raise Http404
                    self.base_object = None
                    return super(
                        RegisterListDocumentsView, self
                    ).dispatch(request, *args, **kwargs)
        self.client = client
        contacts = self.client.contact_set.all()
        queryset = Register.objects.filter(contacts__in=contacts)
        self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):

        try:
            return super(ClientListMatterView, self).get_context_data(**kwargs)
        except Exception as exception:
            messages.error(
                self.request, _(
                    'Error retrieving document list: %(exception)s.'
                ) % {
                    'exception': exception
                }
            )
            self.object_list = Register.objects.none()
            return super(ClientListMatterView, self).get_context_data(**kwargs)

    def get_extra_context(self):
        title = _('Matters')
        return {
            'hide_links': True,
            'list_as_items': True,
            'no_results_icon': icon_document_list,
            'no_results_text': _(
                'This could mean that no documents have been uploaded or '
                'that your user account has not been granted the view '
                'permission for any document or document type.'
            ),
            'no_results_title': _('No matters available'),
            'title': title,
        }

    def get_success_url(self):
        matters =','.join([str(int) for int in self.queryset.values_list('id', flat=True)])
        return reverse_lazy('register:register_list', kwargs={'id_list': matters.replace(',','_')})

class RegisterRequestCloseManyView(ConfirmView):
    success_message = 'Sent request to close selected File numbers.'
    success_message_plural = 'Sent request to close all selected File numbers.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_list'
    )
    id_list = 'None'

    def dispatch(self, request, *args, **kwargs):
        try:
            self.permission_register_create = Permission.check_permissions(self.request.user,permission_register_create)
            self.title = _('Close selected files?')
            self.message_success = _('All selected files closed.')
        except PermissionDenied:
            self.permission_register_create = False
            self.title = _('Send request to close selected files?')
            self.message_success = _('Sent request to close all selected files.')
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        self.post_action_redirect = reverse_lazy('register:register_list', kwargs={'id_list': id_list.replace(',','_') })
        return super(RegisterRequestCloseManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': self.title,
            'next' : self.post_action_redirect
        }

    def view_action(self):
        self.id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )

        regs = Register.objects.filter(pk__in=self.id_list.split(','))

        for r in regs:
            if self.permission_register_create:
                r.status = "Closed"
                r.save()
                event_file_no_closed.commit(actor=self.request.user, action_object=r )

            else:
                r.status = "Request to close"
                r.save()
        if not self.permission_register_create:
            send_register_request_close_mail(self.request.user,r,self.id_list)
        messages.success(
            self.request,  self.message_success
        )

class RegisterTransferManyView(ConfirmView):
    success_message = 'Selected file transferred.'
    success_message_plural = 'Selected files transferred.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_list'
    )
    id_list = 'None'

    def dispatch(self, request, *args, **kwargs):
        self.id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        regs = Register.objects.filter(pk__in=self.id_list.split(','))
        if not regs:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        status = regs[0].status
        for r in regs:
            if r.status != status:
                messages.error(
                    self.request, _('Please select files with the same status.')
                )
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        if r.transfer_to != "":
            self.transfer_to = json.loads(r.transfer_to)
            self.title = "Transfer file(s) to " + ", ".join(self.transfer_to) + " ?"
        else:
            return HttpResponseRedirect(reverse_lazy('register:register_multiple_transfer', kwargs={'id_list': self.id_list.replace(',','_') }))
        return super(RegisterTransferManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': self.title,
            'next' : self.post_action_redirect
        }

    def view_action(self):

        regs = Register.objects.filter(pk__in=self.id_list.split(','))
        roles = Role.objects.all()

        for r in regs:
            acls = AccessControlList.objects.filter(object_id=r.pk)
            for a in acls:
                a.delete()
            for role in roles:
                remove_entry_from_option_list('Register',role,r)

            r.status = r.last_status
            file_number = r.file_no[:r.file_no.rfind('/')]+'/'+abbr.value[self.transfer_to[0]]
            r.file_no = file_number
            if self.transfer_to:
                a = self.transfer_to[0]
                user = User.objects.filter(first_name=a.split(' ')[0],last_name=a.split(' ')[1]).first()
                if user:
                    r.lawyers.clear()
                    r.lawyers.add(user)

            for a in self.transfer_to:
                role = Role.objects.get(label=a.split(' ')[1])
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=r.pk,content_type=ContentType.objects.get_for_model(r), role=role
                )
                acl.permissions.add(StoredPermission.objects.get(name='register_view'))
                add_entry_to_option_list('Register',role,r)
                event_file_no_transferred.commit(actor=self.request.user, action_object=r, target=role )
            r.last_status = ""
            r.save()
            #remove permissions from old and apply to new one
            for doc in r.documents.all():
                acl = AccessControlList.objects.filter(object_id=doc.pk,content_type=ContentType.objects.get_for_model(doc))
                for a in acl:
                    a.delete()

                acl, created = AccessControlList.objects.get_or_create(
                           object_id=doc.pk,content_type=ContentType.objects.get_for_model(doc), role=role
                        )
                task_add_rw_permissions(acl)
        messages.success(
            self.request,  'File(s) transferred.'
        )

class RegisterRequestTransferManyView(SingleObjectCreateView):
    extra_context = {'title': _('Transfer File Number(s)')}
    model = Register
    form_class = RegisterRequestTransferForm
    access = None
    id_list = 'None'
    transfer = False

    def dispatch(self, request, *args, **kwargs):
        if 'id_list' in kwargs:
            self.id_list = kwargs['id_list'].replace('_',',')
            self.transfer = True
        else:
            self.id_list = self.request.GET.get(
                'id_list', self.request.POST.get('id_list', '')
            )
        self.post_action_redirect = reverse_lazy('register:register_list', kwargs={'id_list': self.id_list.replace(',','_') })
        regs = Register.objects.filter(pk__in=self.id_list.split(','))
        status = regs[0].status
        path = self.request.path
        for r in regs:
             if r.status != status:
                messages.error(
                    self.request, _('Please select files with the same status.')
                )
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        return super(RegisterRequestTransferManyView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(RegisterRequestTransferManyView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            if 'access' in form.cleaned_data:
                access = form.cleaned_data['access']
                regs = Register.objects.filter(pk__in=self.id_list.split(','))
                if not self.transfer:
                    for r in regs:
                        r.last_status = r.status
                        r.status = "Request to transfer"
                        r.transfer_to = json.dumps(access)
                        r.save()
                    send_register_request_transfer_mail(self.request.user,r,self.id_list)
                    messages.success(
                        self.request, _('Request has been sent.')
                    )
                else:
                    roles = Role.objects.all()
                    for r in regs:
                        acls = AccessControlList.objects.filter(object_id=r.pk)
                        for a in acls:
                            a.delete()
                        for role in roles:
                            remove_entry_from_option_list('Register',role,r)

                        file_number = r.file_no[:r.file_no.rfind('/')]+'/'+abbr.value[access[0]]
                        r.file_no = file_number

                        #for a in access:
                        a = access[0]
                        user = User.objects.filter(first_name=a.split(' ')[0],last_name=a.split(' ')[1]).first()
                        if user:
                            r.lawyers.clear()
                            r.lawyers.add(user)
                        role = Role.objects.get(label=a.split(' ')[1])
                        acl, created = AccessControlList.objects.get_or_create(
                           object_id=r.pk,content_type=ContentType.objects.get_for_model(r), role=role
                        )
                        acl.permissions.add(StoredPermission.objects.get(name='register_view'))
                        add_entry_to_option_list('Register',role,r)
                        event_file_no_transferred.commit(actor=self.request.user, action_object=r, target=role )
                        r.last_status = ""
                        r.save()
                        #remove permissions from old and apply to new one
                        for doc in r.documents.all():
                            acl = AccessControlList.objects.filter(object_id=doc.pk,content_type=ContentType.objects.get_for_model(doc))
                            for a in acl:
                                a.delete()

                            acl, created = AccessControlList.objects.get_or_create(
                                       object_id=doc.pk,content_type=ContentType.objects.get_for_model(doc), role=role
                                    )
                            task_add_rw_permissions(acl)
                    messages.success(
                        self.request,  'File(s) transferred.'
                    )

        return HttpResponseRedirect(self.post_action_redirect)

class RegisterEditGroupManyView(SingleObjectCreateView):
    extra_context = {'title': _('Edit Group of File Number(s)')}
    model = Register
    form_class = RegisterEditGroupForm
    group = None
    id_list = 'None'
    transfer = False

    def dispatch(self, request, *args, **kwargs):
        if 'id_list' in kwargs:
            self.id_list = kwargs['id_list'].replace('_',',')
            self.transfer = True
        else:
            self.id_list = self.request.GET.get(
                'id_list', self.request.POST.get('id_list', '')
            )
        self.post_action_redirect = reverse_lazy('register:register_list', kwargs={'id_list': self.id_list.replace(',','_') })
        # ~ regs = Register.objects.filter(pk__in=self.id_list.split(','))
        # ~ status = regs[0].status
        # ~ path = self.request.path
        # ~ for r in regs:
             # ~ if r.status != status:
                # ~ messages.error(
                    # ~ self.request, _('Please select files with the same status.')
                # ~ )
                # ~ return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        return super(RegisterEditGroupManyView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(RegisterEditGroupManyView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            if 'group' in form.cleaned_data:
                group = form.cleaned_data['group']
                regs = Register.objects.filter(pk__in=self.id_list.split(','))
                for r in regs:
                    r.group = group[0]
                    r.save()
                messages.success(
                    self.request, _('Field group has been changed.')
                )

        return HttpResponseRedirect(self.post_action_redirect)

class RegisterActivateManyView(ConfirmView):

    success_message = 'Activated all File numbers.'
    success_message_plural = 'Activated all File numbers.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_list'
    )

    def dispatch(self, request, *args, **kwargs):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        self.post_action_redirect = reverse_lazy('register:register_list', kwargs={'id_list': id_list.replace(',','_') })
        return super(RegisterActivateManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': _('Activate all selected File numbers?'),
            'next': self.post_action_redirect
        }

    def get_post_action_redirect(self):
        return reverse('register:register_list')

    def view_action(self):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        regs = Register.objects.filter(pk__in=id_list.split(','))
        for r in regs:
            r.status = "Active"
            r.save()
            event_file_no_activated.commit(
                actor=self.request.user, action_object=r, target=r
            )
        messages.success(
            self.request, _('All selected File numbers have status active now.')
        )

class RegisterSetDormantManyView(ConfirmView):

    success_message = 'Made all File numbers dormant.'
    success_message_plural = 'Made all File numbers dormant.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_list'
    )

    def dispatch(self, request, *args, **kwargs):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        self.post_action_redirect = reverse_lazy('register:register_list', kwargs={'id_list': id_list.replace(',','_') })
        return super(RegisterSetDormantManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': _('Make all selected File numbers dormant?'),
            'next': self.post_action_redirect
        }

    def get_post_action_redirect(self):
        return reverse('register:register_list')

    def view_action(self):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        regs = Register.objects.filter(pk__in=id_list.split(','))
        for r in regs:
            r.status = "Dormant"
            r.save()
            event_file_no_dormant.commit(
                actor=self.request.user, action_object=r, target=r
            )
        messages.success(
            self.request, _('All selected File numbers have status dormant now.')
        )

class RegisterPrintManyView(SingleObjectListView):

    form = None
    query_request = None
    print_result = False
    opened_from = ''
    opened_to = ''
    id_list = None
    register_search_form = None
    register_edit_permission = False

    def dispatch(self, request, *args, **kwargs):
        self.items = self.request.GET
        id_list =self.items['id_list']
        if id_list:
            self.id_list = id_list.split(',')
            #self.items = json.loads(self.request.GET['print'])
            queryset = self.get_object_list()
            pdf =create_report(queryset, 'Statusreport File Numbers', self.opened_from+' - '+self.opened_to, get_now(True),True,user=self.request.user)
            return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Statusreport_File_Numbers'}))

        try:
            self.register_edit_permission = Permission.check_permissions(self.request.user,permission_register_edit)
        except PermissionDenied:
            self.register_edit_permission = False
        return super(RegisterPrintManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'register_search_form' : self.register_search_form,
            'search_q' : self.search_q,
            'form' : self.form,
            'query_request': json.dumps(self.query_request),
            'hide_object' : True,
            'hide_link': True,
            'register_filter': self.register_filter,
            'permission_register_edit' : self.register_edit_permission,
            'no_results_icon': icon_register,
            'no_results_main_link': link_register_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Nix'
            ),
            'no_results_title': _('There are no files.'),
            'title': _('File Numbers:'),
        }

    def get_object_list(self):
        self.register_search_form = RegisterSearchForm(user=self.request.user, queryset = self.queryset)
        self.queryset = None
        self.search_q = ''
        self.register_filter = {}
        if self.id_list:
            queryset = Register.objects.filter(pk__in=self.id_list)
            #self.register_search_form = None
            return AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)

        if permission_register_edit.stored_permission.requester_has_this(self.request.user):
            self.queryset = Register.objects.all()# TODO Remove.order_by('opened').reverse()
        else:
            queryset = Register.objects.all().exclude(file_no__startswith="TEMP__")#.order_by('opened').reverse()
            self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        if not self.queryset:
            return self.queryset
        self.opened_from = self.queryset.last().opened.strftime("%d. %B %Y").lstrip('0')
        self.opened_to = get_now(True)
        filter_query = {}

        for k, v in self.items.iteritems():
            if k == 'Number of uploaded documents':
                if v != '---':
                    qs = self.queryset.annotate(count = Count('documents') )
                    self.queryset = qs.filter(count=v)
            elif v != '0':
                filter_query[str(k)] = v
        for k,v in filter_query.iteritems():
            if ( k == 'q' and v != 0 ) or ( k == 'search_q' and v is not 'None' ):
                queries = shlex.split(v)
                q_all = Q() # Create an empty Q object to start with
                for q in queries:
                    q_objects = Q()
                    q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                    q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                    q_all.add(q_objects,Q.AND)
                self.queryset =  self.queryset.filter(q_all)
                self.search_q = v
            elif k=='from' and v !='':
                v = v.replace('%20',' ')
                self.opened_from = v
                self.queryset = self.queryset.filter(opened__date__gte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k=='to' and v != '':
                v = v.replace('%20',' ')
                self.opened_to = v
                self.queryset = self.queryset.filter(opened__date__lte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k == 'Status' and v != '':
                self.queryset = self.queryset.filter(status = v)
            elif k == 'Group' and v != '':
                self.queryset = self.queryset.filter(group = v)
            elif k == 'Lawyers' and v != '':
                lawyer = get_user_model().objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                if lawyer:
                    self.queryset = self.queryset.filter(lawyers = lawyer)

        self.register_filter = {}
        for reg in self.queryset:
            if 'Status' in self.register_filter:
                self.register_filter['Status'].add(reg.status)
            else:
                self.register_filter['Status'] = set()
                self.register_filter['Status'].add(reg.status)
            if 'Group' in self.register_filter:
                self.register_filter['Group'].add(reg.group)
            else:
                self.register_filter['Group'] = set()
                self.register_filter['Group'].add(reg.group)
        if self.register_edit_permission:
            self.register_filter['Lawyers'] = set()
            for a in access_choices.value:
                self.register_filter['Lawyers'].add(a[0])
        #count
        self.register_filter['Number of uploaded documents'] = set()
        self.register_filter['Number of uploaded documents'].add(0)
        self.form = FilterForm(self.request.GET, user=self.request.user, register_filter = self.register_filter,)
        self.query_request = self.request.GET
        return self.queryset


class QuotationPrintManyView(SingleObjectListView):

    form = None
    query_request = None
    print_result = False
    opened_from = ''
    opened_to = ''
    id_list = None
    register_search_form = None
    register_edit_permission = False

    def dispatch(self, request, *args, **kwargs):
        self.items = self.request.GET
        id_list =self.items['id_list']
        if id_list:
            self.id_list = id_list.split(',')
            #self.items = json.loads(self.request.GET['print'])
            queryset = self.get_object_list()
            pdf =create_report(queryset, 'Statusreport Quotations', self.opened_from+' - '+self.opened_to, get_now(True))
            return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Statusreport_Quotations'}))
        try:
            self.register_edit_permission = Permission.check_permissions(self.request.user,permission_register_edit)
        except PermissionDenied:
            self.register_edit_permission = False
        return super(QuotationPrintManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'register_search_form' : self.register_search_form,
            'search_q' : self.search_q,
            'form' : self.form,
            'query_request': json.dumps(self.query_request),
            'hide_object' : True,
            'hide_link': True,
            'register_filter': self.register_filter,
            'permission_register_edit' : self.register_edit_permission,
            'no_results_icon': icon_register,
            'no_results_main_link': link_register_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Nix'
            ),
            'no_results_title': _('There are no files.'),
            'title': _('File Numbers:'),
        }

    def get_object_list(self):
        self.register_search_form = RegisterSearchForm(user=self.request.user, queryset = self.queryset)
        self.queryset = None
        self.search_q = ''
        self.register_filter = {}
        if self.id_list:
            queryset = Quotation.objects.filter(pk__in=self.id_list)
            #self.register_search_form = None
            return AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)

        if permission_register_edit.stored_permission.requester_has_this(self.request.user):
            self.queryset = Quotation.objects.all()# TODO Remove.order_by('opened').reverse()
        else:
            queryset = Quotation.objects.all().exclude(file_no__startswith="TEMP__")#.order_by('opened').reverse()
            self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        if not self.queryset:
            return self.queryset
        self.opened_from = self.queryset.last().opened.strftime("%d. %B %Y").lstrip('0')
        self.opened_to = get_now(True)
        filter_query = {}

        for k, v in self.items.iteritems():
            if v != '0':
                filter_query[str(k)] = v
        for k,v in filter_query.iteritems():
            if ( k == 'q' and v != 0 ) or ( k == 'search_q' and v is not 'None' ):
                queries = shlex.split(v)
                q_all = Q() # Create an empty Q object to start with
                for q in queries:
                    q_objects = Q()
                    q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                    q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                    q_all.add(q_objects,Q.AND)
                self.queryset =  self.queryset.filter(q_all)
                self.search_q = v
            elif k=='from' and v !='':
                v = v.replace('%20',' ')
                self.opened_from = v
                self.queryset = self.queryset.filter(opened__date__gte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k=='to' and v != '':
                v = v.replace('%20',' ')
                self.opened_to = v
                self.queryset = self.queryset.filter(opened__date__lte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k == 'Status' and v != '':
                self.queryset = self.queryset.filter(status = v)
            elif k == 'Group' and v != '':
                self.queryset = self.queryset.filter(group = v)
            elif k == 'Lawyers' and v != '':
                lawyer = get_user_model().objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                if lawyer:
                    self.queryset = self.queryset.filter(lawyers = lawyer)

        self.register_filter = {}
        for reg in self.queryset:
            if 'Status' in self.register_filter:
                self.register_filter['Status'].add(reg.status)
            else:
                self.register_filter['Status'] = set()
                self.register_filter['Status'].add(reg.status)
            # ~ if 'Group' in self.register_filter:
                # ~ self.register_filter['Group'].add(reg.group)
            # ~ else:
                # ~ self.register_filter['Group'] = set()
                # ~ self.register_filter['Group'].add(reg.group)
        if self.register_edit_permission:
            self.register_filter['Lawyers'] = set()
            for a in access_choices.value:
                self.register_filter['Lawyers'].add(a[0])
        self.form = FilterForm(self.request.GET, user=self.request.user, register_filter = self.register_filter,)
        self.query_request = self.request.GET
        return self.queryset
class QuotationActivateManyView(ConfirmView):

    success_message = 'Activated all quotations.'
    success_message_plural = 'Activated all quotations.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_quotations_list'
    )


    def get_extra_context(self):
        return {
            'title': _('Activate all selected quotations?')
        }

    def get_post_action_redirect(self):
        return reverse('register:register_quotations_list')

    def view_action(self):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        regs = Quotation.objects.filter(pk__in=id_list.split(','))
        for r in regs:
            r.status = "Active"
            r.save()
        messages.success(
            self.request, _('All selected quotations have status active now.')
        )

class RegisterDeactivateManyView(ConfirmView):

    success_message = 'Set the status to not active.'
    success_message_plural = 'Set the status to not active.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_list'
    )
    def dispatch(self, request, *args, **kwargs):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        self.post_action_redirect = reverse_lazy('register:register_list', kwargs={'id_list': id_list.replace(',','_') })
        return super(RegisterDeactivateManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': _('Set the status of all selected File numbers to not active?'),
            'next' : self.post_action_redirect
        }

    def get_post_action_redirect(self):
        return reverse('register:register_list')

    def view_action(self):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        regs = Register.objects.filter(pk__in=id_list.split(','))
        for r in regs:
            r.status = 'Not active'
            r.save()
            event_file_no_not_active.commit(
                actor=self.request.user, action_object=r, target=r
            )
        messages.success(
            self.request, _('All selected File numbers have status not active now.')
        )

class QuotationCloseManyView(ConfirmView):

    success_message = 'Close this quotation.'
    success_message_plural = 'Close this quotations.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_quotations_list'
    )
    def get_extra_context(self):
        return {
            'title': _('Close all selected quotations?')
        }

    def get_post_action_redirect(self):
        return reverse('register:register_quotations_list')

    def view_action(self):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        regs = Quotation.objects.filter(pk__in=id_list.split(','))
        for r in regs:
            r.status = "Closed"
            r.save()
            event_file_no_closed.commit(actor=self.request.user, action_object=r )

        messages.success(
            self.request, _('All selected quotations have been closed.')
        )

class RegisterCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create new File No.')}
    model = Register
    form_class = RegisterEntryCreateForm
    post_action_redirect = reverse_lazy('register:register_list')

    def dispatch(self, request, *args, **kwargs):
        return super(RegisterCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(RegisterCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            file_no = group = status = access = ''
            if 'file_no' in form.cleaned_data:
                file_no = form.cleaned_data['file_no']
            #opened = get_aware_str_from_unaware(form.cleaned_data['opened'])
            opened = datetime.datetime.strptime(form.cleaned_data['opened'], "%d.%m.%Y").date()
            parties = form.cleaned_data['parties']
            parties = parties.replace(u"\u2019", "'")
            parties = parties.replace(u"\u2013","-")
            parties = parties.replace(u'\u201c','"')
            parties = parties.replace(u'\u201d','"')
            parties = parties.replace(u'\xa3','GBP')
            parties = parties.replace(u'\xe9','e')
            if 'clients' in form.cleaned_data:
                clients = form.cleaned_data['clients']
            if 'department' in form.cleaned_data:
                department = form.cleaned_data['department']
            if 'group' in form.cleaned_data:
                group = form.cleaned_data['group']
            if 'status' in form.cleaned_data:
                status = form.cleaned_data['status']
            if 'access' in form.cleaned_data:
                access = form.cleaned_data['access']
            if file_no == '':
                file_no = "TEMP__"+str(time.time())
            if status == '':
                status = 'Not active'
            register = Register(file_no=file_no,opened=opened,parties=parties,status=status, group=group, department=department)
            register.save()
            # ~ for client in clients:
                # ~ register.clients.add(client)


            # ~ # Add to option list of all roles with register_view permission

            sp = StoredPermission.objects.get(name="register_view")
            roles = Role.objects.all()
            for r in roles:
                if sp in  r.permissions.all():
                    add_entry_to_option_list('Register',r,register)

            for a in access:
                role = Role.objects.get(label=a.split(' ')[1])
                role_user = User.objects.filter(first_name=a.split(' ')[0],last_name=a.split(' ')[1]).first()
                register.lawyers.add(role_user)
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=register.pk,content_type=ContentType.objects.get_for_model(register), role=role
                )
                acl.permissions.add(StoredPermission.objects.get(name='register_view'))
                add_entry_to_option_list('Register',role,register)
            register.save()
            if file_no.startswith('TEMP__'):
                send_register_request_mail(self.request.user,register)
                messages.success(
                    self.request, _('File number request has been sent.')
                )
                event_file_no_requested.commit(
                    actor=self.request.user, action_object=register, target=register
                )
            else:
                event_file_no_created.commit(
                    actor=self.request.user, action_object=register
                )
                if register.status == "Active":
                    event_file_no_activated.commit(
                        actor=self.request.user, action_object=register, target=register
                    )
        return HttpResponseRedirect(self.get_success_url())

class RegisterEditView(SingleObjectEditView):
    model = Register
    form_class = RegisterEntryEditForm
    object_permission = permission_register_edit

    def dispatch(self, request, *args, **kwargs):
        Permission.check_permissions(self.request.user,permission_register_edit)
        try:
            self.register_entry = Register.objects.get(pk=kwargs['pk'])
        except Register.DoesNotExist:
            return HttpResponseRedirect("/")
        self.post_action_redirect = reverse_lazy('register:register_list')
        self.is_active = self.register_entry.status == 'Active'
        self.req_id = kwargs.pop('req_id',None)
        self.reg_id = kwargs.pop('pk', None)
        return super(RegisterEditView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(RegisterEditView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['req_id'] = self.req_id
        kwargs['reg_id'] = self.reg_id
        kwargs['request_path'] = self.request.path
        return kwargs

    def get_extra_context(self):
        label = self.get_object().file_no
        title = _('Edit File Number: %s') % label
        if self.get_object().file_no.startswith("TEMP__"):
            label = ''
        if self.get_object().transfer_to != '' and self.get_object().status == 'Request to transfer':
            title = title + '<br / >Request to transfer the file to: '+ ', '.join(json.loads(self.get_object().transfer_to))
        return {
            'object': self.get_object(),
            'title': title,
        }

    def form_valid(self, form):
        if form.is_valid():
            old_entry = str(self.register_entry)
            old_status = self.register_entry.status
            old_lawyer = self.register_entry.lawyers.first()
            if old_lawyer:
                old_lawyer = old_lawyer.first_name+' '+old_lawyer.last_name
            self.register_entry.file_no = form.cleaned_data['file_no']
            self.register_entry.opened = datetime.datetime.strptime(form.cleaned_data['opened'], "%d.%m.%Y").date()
            parties = form.cleaned_data['parties']
            parties = parties.replace(u"\u2019", "'")
            parties = parties.replace(u"\u2013","-")
            parties = parties.replace(u'\u201c','"')
            parties = parties.replace(u'\u201d','"')
            parties = parties.replace(u'\xa3','GBP')
            parties = parties.replace(u'\xe9','e')
            self.register_entry.parties = parties


            self.register_entry.department = form.cleaned_data['department']
            self.register_entry.group = form.cleaned_data['group']
            self.register_entry.statusdepartment = form.cleaned_data['status']
            if form.cleaned_data['status'] != "Request to transfer":
                self.register_entry.transfer_to = ''
            if form.cleaned_data['status'] == "Closed":
                event_file_no_closed.commit(
                    actor=self.request.user, action_object=self.register_entry, target=self.register_entry
                )
            if form.cleaned_data['status'] == "Not active":
                event_file_no_not_active.commit(
                    actor=self.request.user, action_object=self.register_entry, target=self.register_entry
                )
            if form.cleaned_data['status'] == "Transferred to client":
                event_file_no_transferred_to_client.commit(
                    actor=self.request.user, action_object=self.register_entry, target=self.register_entry
                )
            sp = StoredPermission.objects.get(name="register_view")
            roles = Role.objects.all()
            access = form.cleaned_data['access']
            new = ''
            if len(access) > 0:
                new = access[0]
            if new == old_lawyer:
                changed = False
            else:
                changed = True
            if changed:
                acls = AccessControlList.objects.filter(object_id=self.register_entry.pk)
                for a in acls:
                    remove_entry_from_option_list('Register',a.role,old_entry)
                    a.delete()
                self.register_entry.lawyers.clear()
                for r in roles:
                    if sp in  r.permissions.all():
                        remove_entry_from_option_list('Register',r,old_entry)
                # Add to option list of all roles with register_view permission

                for r in roles:
                    if sp in  r.permissions.all():
                        add_entry_to_option_list('Register',r,self.register_entry)

                for a in access:
                    role = Role.objects.get(label=a.split(' ')[1])
                    acl, created = AccessControlList.objects.get_or_create(
                       object_id=self.register_entry.pk,content_type=ContentType.objects.get_for_model(self.register_entry), role=role
                    )
                    role_user = User.objects.filter(first_name=a.split(' ')[0],last_name=a.split(' ')[1]).first()
                    self.register_entry.lawyers.add(role_user)
                    acl.permissions.add(StoredPermission.objects.get(name='register_view'))
                    add_entry_to_option_list('Register',role,self.register_entry)
                    if form.cleaned_data['status'] != "Request to transfer":
                        if old_status == "Request to transfer":
                            event_file_no_transferred.commit(
                                actor=self.request.user, action_object=self.register_entry, target=role
                            )
                    for doc in self.register_entry.documents.all():
                        acl = AccessControlList.objects.filter(object_id=doc.pk,content_type=ContentType.objects.get_for_model(doc))
                        for a in acl:
                            a.delete()

                        acl, created = AccessControlList.objects.get_or_create(
                                   object_id=doc.pk,content_type=ContentType.objects.get_for_model(doc), role=role
                                )
                        task_add_rw_permissions(acl)
            self.register_entry.save()
            # ~ clients = form.cleaned_data['clients']
            # ~ self.register_entry.clients.clear()
            # ~ for client in clients:
                # ~ self.register_entry.clients.add(client)
            if self.req_id:
                send_register_request_confirmation_mail(self.request.user, self.req_id, self.register_entry )
                messages.success(
                    self.request, _('File number creation confirmation has been sent.')
                )
            if self.register_entry.status == "Active" and not self.is_active:
                event_file_no_activated.commit(
                    actor=self.request.user, action_object=self.register_entry, target=self.register_entry
                )

        return HttpResponseRedirect(self.get_success_url())


class RegisterStatisticView(SingleObjectCreateView):
    model = Register
    form_class = RegisterStatisticForm

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        return super(RegisterStatisticView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': _('Create Statistics'),
        }
    def get_success_url(self):
        self.lawyers = [str(int) for int in self.lawyers]
        if self.date_from:
            from_dt = datetime.datetime.strptime(self.date_from, "%d.%m.%Y").date() #parse(self.date_from)
        else:
            from_dt = Register.objects.all().last().opened
        if self.date_to:
            to_dt = datetime.datetime.strptime(self.date_to, "%d.%m.%Y").date() #parse(self.date_to)
        else:
            to_dt = timezone.now()
        return reverse_lazy('register:register_statistics_view', args = ('_'.join(self.lawyers),
            from_dt.year,from_dt.month,from_dt.day,to_dt.year,to_dt.month,to_dt.day))

    def form_valid(self, form):
        if form.is_valid():
            self.data_from = self.date_to= None
            if 'from' in form.cleaned_data:
                self.date_from = form.cleaned_data['from']
            if 'to' in form.cleaned_data:
                self.date_to = form.cleaned_data['to']
            if 'lawyers' in form.cleaned_data:
                user_ids = []
                if not 'All' in form.cleaned_data['lawyers']:
                    for lawyer in form.cleaned_data['lawyers']:
                        user_ids.append(User.objects.filter(first_name=lawyer.split(' ')[0],last_name=lawyer.split(' ')[1]).first().pk)
                else:
                    for lawyer in access_choices.value:
                        user_ids.append(User.objects.filter(first_name=lawyer[0].split(' ')[0],last_name=lawyer[0].split(' ')[1]).first().pk)

                self.lawyers = user_ids

        return HttpResponseRedirect(self.get_success_url())

class RegisterListView(SearchModelMixin,SingleObjectListView):

    form = None
    query_request = None
    print_result = False
    opened_from = ''
    opened_to = ''
    id_list = None
    register_search_form = None
    register_edit_permission = False

    def dispatch(self, request, *args, **kwargs):
        self.items = self.request.GET
        if 'id_list' in kwargs:
            self.id_list = kwargs['id_list'].split('_')
        if 'print' in self.request.GET:
            self.items = json.loads(self.request.GET['print'])
            queryset = self.get_object_list()
            pdf =create_report(queryset, 'Statusreport File Numbers', self.opened_from+' - '+self.opened_to, get_now(True),True,user=self.request.user)
            return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Statusreport_File_Numbers'}))

        try:
            self.register_edit_permission = Permission.check_permissions(self.request.user,permission_register_edit)
        except PermissionDenied:
            self.register_edit_permission = False
        return super(RegisterListView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'register_search_form' : self.register_search_form,
            'search_q' : self.search_q,
            'form' : self.form,
            'query_request': json.dumps(self.query_request),
            'hide_object' : True,
            'hide_link': True,
            'register_filter': self.register_filter,
            'permission_register_edit' : self.register_edit_permission,
            'no_results_icon': icon_register,
            'no_results_main_link': link_register_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Nix'
            ),
            'no_results_title': _('There are no files.'),
            'title': _('File Numbers:'),
        }

    def get_object_list(self):
        self.register_search_form = RegisterSearchForm(user=self.request.user, queryset = self.queryset)
        self.queryset = None
        self.search_q = ''
        self.register_filter = {}
        if self.id_list:
            queryset = Register.objects.filter(pk__in=self.id_list)
            #self.register_search_form = None
            return AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)

        if permission_register_edit.stored_permission.requester_has_this(self.request.user):
            self.queryset = Register.objects.all().exclude(group='General and Non-Billable Files').exclude(group='Audit Reports')# TODO Remove.order_by('opened').reverse()
        else:
            queryset = Register.objects.all().exclude(group='General and Non-Billable Files').exclude(file_no__startswith="TEMP__").exclude(group='Audit Reports')#.order_by('opened').reverse()
            self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        if not self.queryset:
            return self.queryset
        self.opened_from = self.queryset.last().opened.strftime("%d. %B %Y").lstrip('0')
        self.opened_to = get_now(True)
        filter_query = {}

        for k, v in self.items.iteritems():
            if k == 'Number of uploaded documents':
                if v != '---':
                    qs = self.queryset.annotate(count = Count('documents') )
                    self.queryset = qs.filter(count=v)
            elif v != '0':
                filter_query[str(k)] = v
        for k,v in filter_query.iteritems():
            if ( k == 'q' and v != 0 ) or ( k == 'search_q' and v is not 'None' ):
                queries = shlex.split(v)
                q_all = Q() # Create an empty Q object to start with
                for q in queries:
                    q_objects = Q()
                    q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                    q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                    q_all.add(q_objects,Q.AND)
                self.queryset =  self.queryset.filter(q_all)
                self.search_q = v
            elif k=='from' and v !='':
                v = v.replace('%20',' ')
                self.opened_from = v # dateutil.parser.parse(v).strftime("%d. %B %Y").lstrip('0')
                self.queryset = self.queryset.filter(opened__date__gte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k=='to' and v != '':
                v = v.replace('%20',' ')
                self.opened_to = v
                self.queryset = self.queryset.filter(opened__date__lte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k == 'Client' and v != '':
                client = Client.objects.get(name=v)
                self.queryset = self.queryset.filter(clients = client)
            elif k == 'Department' and v != '':
                department = Department.objects.get(name=v)
                self.queryset = self.queryset.filter(department = department)
            elif k == 'Status' and v != '':
                self.queryset = self.queryset.filter(status = v)
            elif k == 'Group' and v != '':
                self.queryset = self.queryset.filter(group = v)
            elif k == 'Has checklist' and v != '':
                if v == 'Yes':
                    self.queryset = self.queryset.exclude(registerchecklist=None)
                elif v == 'No':
                    self.queryset = self.queryset.filter(registerchecklist=None)

            elif k == 'Lawyers' and v != '':
                lawyer = get_user_model().objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                if lawyer:
                    self.queryset = self.queryset.filter(lawyers = lawyer)


        self.register_filter = {}
        for reg in self.queryset:
            if reg.client:
                if 'Client' in self.register_filter:
                    self.register_filter['Client'].add(reg.client)
                else:
                    self.register_filter['Client'] = set()
                    self.register_filter['Client'].add(reg.client)
            if reg.department:
                if 'Department' in self.register_filter:
                    self.register_filter['Department'].add(reg.department)
                else:
                    self.register_filter['Department'] = set()
                    self.register_filter['Department'].add(reg.department)
            if 'Status' in self.register_filter:
                self.register_filter['Status'].add(reg.status)
            else:
                self.register_filter['Status'] = set()
                self.register_filter['Status'].add(reg.status)
            if 'Group' in self.register_filter:
                self.register_filter['Group'].add(reg.group)
            else:
                self.register_filter['Group'] = set()
                self.register_filter['Group'].add(reg.group)
        self.register_filter['Lawyers'] = set()
        for a in access_choices.value:
            self.register_filter['Lawyers'].add(a[0])
        #count
        self.register_filter['Number of uploaded documents'] = set()
        self.register_filter['Number of uploaded documents'].add(0)
        #has checklist
        self.register_filter['Has checklist'] = set()
        self.register_filter['Has checklist'].add('Yes')
        self.register_filter['Has checklist'].add('No')

        self.form = FilterForm(self.request.GET, user=self.request.user, register_filter = self.register_filter,)
        self.query_request = self.request.GET
        return self.queryset

class RegisterAuditListView(RegisterListView):

    def get_object_list(self):
        self.register_search_form = RegisterSearchForm(user=self.request.user, queryset = self.queryset)
        self.queryset = None
        self.search_q = ''
        self.register_filter = {}
        if self.id_list:
            queryset = Register.objects.filter(pk__in=self.id_list)
            #self.register_search_form = None
            return AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)

        if permission_register_edit.stored_permission.requester_has_this(self.request.user):
            self.queryset = Register.objects.filter(group='Audit Reports')# TODO Remove.order_by('opened').reverse()
        else:
            queryset = Register.objects.all().filter(group='Audit Reports').exclude(file_no__startswith="TEMP__")#.order_by('opened').reverse()
            self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        if not self.queryset:
            return self.queryset
        self.opened_from = self.queryset.last().opened.strftime("%d. %B %Y").lstrip('0')
        self.opened_to = get_now(True)
        filter_query = {}

        for k, v in self.items.iteritems():
            if k == 'Number of uploaded documents':
                if v != '---':
                    qs = self.queryset.annotate(count = Count('documents') )
                    self.queryset = qs.filter(count=v)
            elif v != '0':
                filter_query[str(k)] = v
        for k,v in filter_query.iteritems():
            if ( k == 'q' and v != 0 ) or ( k == 'search_q' and v is not 'None' ):
                queries = shlex.split(v)
                q_all = Q() # Create an empty Q object to start with
                for q in queries:
                    q_objects = Q()
                    q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                    q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                    q_all.add(q_objects,Q.AND)
                self.queryset =  self.queryset.filter(q_all)
                self.search_q = v
            elif k=='from' and v !='':
                v = v.replace('%20',' ')
                self.opened_from = v # dateutil.parser.parse(v).strftime("%d. %B %Y").lstrip('0')
                self.queryset = self.queryset.filter(opened__date__gte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k=='to' and v != '':
                v = v.replace('%20',' ')
                self.opened_to = v
                self.queryset = self.queryset.filter(opened__date__lte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k == 'Client' and v != '':
                client = Client.objects.get(name=v)
                self.queryset = self.queryset.filter(clients = client)
            elif k == 'Department' and v != '':
                department = Department.objects.get(name=v)
                self.queryset = self.queryset.filter(department = department)
            elif k == 'Status' and v != '':
                self.queryset = self.queryset.filter(status = v)
            elif k == 'Group' and v != '':
                self.queryset = self.queryset.filter(group = v)
            elif k == 'Has checklist' and v != '':
                if v == 'Yes':
                    self.queryset = self.queryset.exclude(registerchecklist=None)
                elif v == 'No':
                    self.queryset = self.queryset.filter(registerchecklist=None)

            elif k == 'Lawyers' and v != '':
                lawyer = get_user_model().objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                if lawyer:
                    self.queryset = self.queryset.filter(lawyers = lawyer)


        self.register_filter = {}
        for reg in self.queryset:
            if reg.client:
                if 'Client' in self.register_filter:
                    self.register_filter['Client'].add(reg.client)
                else:
                    self.register_filter['Client'] = set()
                    self.register_filter['Client'].add(reg.client)
            if reg.department:
                if 'Department' in self.register_filter:
                    self.register_filter['Department'].add(reg.department)
                else:
                    self.register_filter['Department'] = set()
                    self.register_filter['Department'].add(reg.department)
            if 'Status' in self.register_filter:
                self.register_filter['Status'].add(reg.status)
            else:
                self.register_filter['Status'] = set()
                self.register_filter['Status'].add(reg.status)
            if 'Group' in self.register_filter:
                self.register_filter['Group'].add(reg.group)
            else:
                self.register_filter['Group'] = set()
                self.register_filter['Group'].add(reg.group)
        self.register_filter['Lawyers'] = set()
        for a in access_choices.value:
            self.register_filter['Lawyers'].add(a[0])
        #count
        self.register_filter['Number of uploaded documents'] = set()
        self.register_filter['Number of uploaded documents'].add(0)
        #has checklist
        self.register_filter['Has checklist'] = set()
        self.register_filter['Has checklist'].add('Yes')
        self.register_filter['Has checklist'].add('No')

        self.form = FilterForm(self.request.GET, user=self.request.user, register_filter = self.register_filter,)
        self.query_request = self.request.GET
        return self.queryset

class RegisterGeneralNonBillingListView(RegisterListView):

    def get_object_list(self):
        self.register_search_form = RegisterSearchForm(user=self.request.user, queryset = self.queryset)
        self.queryset = None
        self.search_q = ''
        self.register_filter = {}
        if self.id_list:
            queryset = Register.objects.filter(pk__in=self.id_list)
            #self.register_search_form = None
            return AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)

        if permission_register_edit.stored_permission.requester_has_this(self.request.user):
            self.queryset = Register.objects.filter(group='General and Non-Billable Files')# TODO Remove.order_by('opened').reverse()
        else:
            queryset = Register.objects.all().filter(group='General and Non-Billable Files').exclude(file_no__startswith="TEMP__")#.order_by('opened').reverse()
            self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        if not self.queryset:
            return self.queryset
        self.opened_from = self.queryset.last().opened.strftime("%d. %B %Y").lstrip('0')
        self.opened_to = get_now(True)
        filter_query = {}

        for k, v in self.items.iteritems():
            if k == 'Number of uploaded documents':
                if v != '---':
                    qs = self.queryset.annotate(count = Count('documents') )
                    self.queryset = qs.filter(count=v)
            elif v != '0':
                filter_query[str(k)] = v
        for k,v in filter_query.iteritems():
            if ( k == 'q' and v != 0 ) or ( k == 'search_q' and v is not 'None' ):
                queries = shlex.split(v)
                q_all = Q() # Create an empty Q object to start with
                for q in queries:
                    q_objects = Q()
                    q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                    q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                    q_all.add(q_objects,Q.AND)
                self.queryset =  self.queryset.filter(q_all)
                self.search_q = v
            elif k=='from' and v !='':
                v = v.replace('%20',' ')
                self.opened_from = v # dateutil.parser.parse(v).strftime("%d. %B %Y").lstrip('0')
                self.queryset = self.queryset.filter(opened__date__gte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k=='to' and v != '':
                v = v.replace('%20',' ')
                self.opened_to = v
                self.queryset = self.queryset.filter(opened__date__lte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k == 'Client' and v != '':
                client = Client.objects.get(name=v)
                self.queryset = self.queryset.filter(clients = client)
            elif k == 'Department' and v != '':
                department = Department.objects.get(name=v)
                self.queryset = self.queryset.filter(department = department)
            elif k == 'Status' and v != '':
                self.queryset = self.queryset.filter(status = v)
            elif k == 'Group' and v != '':
                self.queryset = self.queryset.filter(group = v)
            elif k == 'Has checklist' and v != '':
                if v == 'Yes':
                    self.queryset = self.queryset.exclude(registerchecklist=None)
                elif v == 'No':
                    self.queryset = self.queryset.filter(registerchecklist=None)

            elif k == 'Lawyers' and v != '':
                lawyer = get_user_model().objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                if lawyer:
                    self.queryset = self.queryset.filter(lawyers = lawyer)


        self.register_filter = {}
        for reg in self.queryset:
            if reg.client:
                if 'Client' in self.register_filter:
                    self.register_filter['Client'].add(reg.client)
                else:
                    self.register_filter['Client'] = set()
                    self.register_filter['Client'].add(reg.client)
            if reg.department:
                if 'Department' in self.register_filter:
                    self.register_filter['Department'].add(reg.department)
                else:
                    self.register_filter['Department'] = set()
                    self.register_filter['Department'].add(reg.department)
            if 'Status' in self.register_filter:
                self.register_filter['Status'].add(reg.status)
            else:
                self.register_filter['Status'] = set()
                self.register_filter['Status'].add(reg.status)
            if 'Group' in self.register_filter:
                self.register_filter['Group'].add(reg.group)
            else:
                self.register_filter['Group'] = set()
                self.register_filter['Group'].add(reg.group)
        self.register_filter['Lawyers'] = set()
        for a in access_choices.value:
            self.register_filter['Lawyers'].add(a[0])
        #count
        self.register_filter['Number of uploaded documents'] = set()
        self.register_filter['Number of uploaded documents'].add(0)
        #has checklist
        self.register_filter['Has checklist'] = set()
        self.register_filter['Has checklist'].add('Yes')
        self.register_filter['Has checklist'].add('No')

        self.form = FilterForm(self.request.GET, user=self.request.user, register_filter = self.register_filter,)
        self.query_request = self.request.GET
        return self.queryset



class RegisterListDocumentsView(SingleObjectListView):
    queryset_slice = None
    base_object = 'File Number'
    def dispatch(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            register_entry = Register.objects.get(pk=kwargs['pk'])
        elif 'id' in kwargs:
            document =  get_object_or_404(Document,pk=kwargs['id'])
            register_entry = document.register.first()
            if not register_entry:
                #search for quotations
                register_entry = document.quotation_set.first()
                self.base_object = 'Quotation Number'
                if not register_entry:
                    self.queryset = Document.objects.none()
                    #raise Http404
                    self.base_object = None
                    return super(
                        RegisterListDocumentsView, self
                    ).dispatch(request, *args, **kwargs)
        self.file_no = register_entry
        queryset = register_entry.documents.all()
        self.queryset = AccessControlList.objects.filter_by_access(permission=permission_document_view, user=self.request.user, queryset=queryset)
        return super(
            RegisterListDocumentsView, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        try:
            return super(RegisterListDocumentsView, self).get_context_data(**kwargs)
        except Exception as exception:
            messages.error(
                self.request, _(
                    'Error retrieving document list: %(exception)s.'
                ) % {
                    'exception': exception
                }
            )
            self.object_list = Register.objects.none()
            return super(RegisterListDocumentsView, self).get_context_data(**kwargs)

    def get_extra_context(self):
        title = _('No documents available')
        if self.base_object:
            title = 'All documents for '+self.base_object+': <b>'+self.file_no.file_no+'</b><br />Parties: <b>'+ self.file_no.parties+'</b>'
        return {
            'hide_links': True,
            'list_as_items': True,
            'no_results_icon': icon_document_list,
            'no_results_text': _(
                'This could mean that no documents have been uploaded or '
                'that your user account has not been granted the view '
                'permission for any document or document type.'
            ),
            'no_results_title': _('No documents available'),
            'title': title,
        }


def register_list_events_view(request,pk):
    target = '/events/for/register/register/'+pk+'/'
    return redirect(target)

def register_detail_view(request,pk):
    try:
        file_no = Register.objects.get(pk=pk)
    except Register.DoesNotExist:
        return HttpResponse("/")
    AccessControlList.objects.check_access(permission_register_view, request.user, file_no, related=None)
    context = {'file_no': file_no,
        'title' : 'Details of File No.: '+file_no.file_no,
         'permission_register_edit' :permission_register_edit.stored_permission.requester_has_this(request.user) #Permission.check_permissions(request.user,permission_register_edit)
    }
    return render(request, 'appearance/generic_form.html', context)

def client_detail_view(request,pk):
    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        return HttpResponse("/")
    AccessControlList.objects.check_access(permission_register_view, request.user, client, related=None)
    context = {'client': client,
        'title' : 'Details of client: '+client.name,
         'permission_register_edit' :permission_register_edit.stored_permission.requester_has_this(request.user) #Permission.check_permissions(request.user,permission_register_edit)
    }
    return render(request, 'register/client_detail.html', context)

def quotation_detail_view(request,pk):
    try:
        file_no = Quotation.objects.get(pk=pk)
    except Quotation.DoesNotExist:
        return HttpResponse("/")
    AccessControlList.objects.check_access(permission_register_view, request.user, file_no, related=None)
    context = {'quotation_no': file_no,
        'title' : 'Details of Quotation number: '+file_no.file_no,
         'permission_register_edit' :permission_register_edit.stored_permission.requester_has_this(request.user) #Permission.check_permissions(request.user,permission_register_edit)
    }
    return render(request, 'appearance/generic_form.html', context)

class RegisterStatisticResultView(SimpleView):
    model = Register
    template_name = 'register/statistics.html'
    def dispatch(self, request, *args, **kwargs):
        lawyer_ids = kwargs.pop('lawyer_ids', None)
        from_year= kwargs.pop('year_from', None)
        from_month=kwargs.pop('month_from', None)
        from_day=kwargs.pop('day_from', None)
        to_year=kwargs.pop('year_to', None)
        to_month=kwargs.pop('month_to', None)
        to_day=kwargs.pop('day_to', None)
        self.date_from = datetime.datetime(int(from_year),int(from_month),int(from_day))
        self.date_to = datetime.datetime(int(to_year),int(to_month),int(to_day))
        regs = Register.objects.filter(opened__gte=self.date_from,opened__lte=self.date_to)
        lawyers = []
        for id in lawyer_ids.split('_'):
            lawyers.append(User.objects.get(pk=id))
        self.data = []
        for obj in lawyers:
            self.data.append([obj.get_full_name(),
                regs.filter(lawyers=obj).filter(status='Active').count(),
                regs.filter(lawyers=obj).filter(status='Not active').count(),
                regs.filter(lawyers=obj).filter(status='Dormant').count(),
                regs.filter(lawyers=obj).filter(status='Closed').count(),
                regs.filter(lawyers=obj).count()
                ])
        if 'print' in self.request.GET:
            period = self.date_from.strftime("%d. %B %Y").lstrip('0')+' - '+self.date_to.strftime("%d. %B %Y").lstrip('0')
            pdf =create_statistic_report(self.data, 'Statistics Files', period, get_now(True))
            return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Report_Statistic_Register_Files'}))

        return super(RegisterStatisticResultView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        context = {
            'hide_object': True,
            'result' : self.data,
            'data' : self.data,
            'no_results_title': _('No results'),
            'query_request': self.request.GET,
            'title': _('Statistics for period: %s.%s %s - %s.%s %s') %
            (self.date_from.day,self.date_from.month,self.date_from.year,self.date_to.day,self.date_to.month,self.date_to.year),
        }

        return context


class RegisterResultView(SingleObjectListView):
    form = None
    q = None

    def get_extra_context(self):
        context = {
            'hide_object' : True,
            'hide_link': True,
            'list_as_items': False,
            'form' : self.form,
            'q': self.q,
            'no_results_icon': icon_search_submit,
            'no_results_text': _(
                'Try again using different terms. '
            ),
            'no_results_title': _('No search results'),
            #'search_model': self.search_model,
            'search_results_limit': setting_limit.value,
            'title': _('Search results for query: %s') % self.request.GET.copy()['q'],
        }

        return context

    def get_context_data(self, **kwargs):
        context = super(RegisterResultView, self).get_context_data(**kwargs)
        return context

    def get_object_list(self):
        if self.request.GET:
            query_string = self.request.GET.copy()['q']
            queries = shlex.split(query_string)
            q_all = Q() # Create an empty Q object to start with
            for q in queries:
                q_objects = Q()
                q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                q_all.add(q_objects,Q.AND)
            queryset =  Register.objects.filter(q_all)
            return queryset

class QuotationResultView(SingleObjectListView):
    form = None
    q = None

    def get_extra_context(self):
        context = {
            'hide_object' : True,
            'hide_link': True,
            'list_as_items': False,
            'form' : self.form,
            'q': self.q,
            'no_results_icon': icon_search_submit,
            'no_results_text': _(
                'Try again using different terms. '
            ),
            'no_results_title': _('No search results'),
            #'search_model': self.search_model,
            'search_results_limit': setting_limit.value,
            'title': _('Search results for query: %s') % self.request.GET.copy()['q'],
        }

        return context

    def get_context_data(self, **kwargs):
        context = super(QuotationResultView, self).get_context_data(**kwargs)
        return context

    def get_object_list(self):
        if self.request.GET:
            query_string = self.request.GET.copy()['q']
            queries = shlex.split(query_string)
            q_all = Q() # Create an empty Q object to start with
            for q in queries:
                q_objects = Q()
                q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                q_all.add(q_objects,Q.AND)
            queryset =  Quotation.objects.filter(q_all)
            return queryset

class QuotationListView1(SingleObjectListView):
    form = None
    query_request = None
    print_result = False
    opened_from = ''
    opened_to = ''
    def dispatch(self, request, *args, **kwargs):
        self.items = self.request.GET
        if 'print' in self.request.GET:
            self.items = json.loads(self.request.GET['print'])
            queryset = self.get_object_list()
            pdf =create_report(queryset, 'Statusreport Quotations', self.opened_from+' - '+self.opened_to, get_now(True))
            return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Statusreport_Quotations'}))
        try:
            self.permission_register_edit = Permission.check_permissions(self.request.user,permission_register_edit)
        except PermissionDenied:
            self.permission_register_edit = False
        return super(QuotationListView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'quotation_search_form' : QuotationSearchForm(user=self.request.user, queryset = self.queryset),
            'search_q' : self.search_q,
            'hide_object' : True,
            'hide_link': True,
            'form' : self.form,
            'query_request': json.dumps(self.query_request),
            'quotation_filter': self.register_filter,
            'permission_register_edit' : self.permission_register_edit,
            'no_results_icon': icon_register,
            'no_results_main_link': link_register_quotation_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                ''
            ),
            'no_results_title': _('There are no quotations.'),
            'title': _('Quotation Numbers'),
        }

    def get_object_list(self):
        self.queryset = None
        self.search_q = ''
        self.register_filter = {}
        if permission_register_edit.stored_permission.requester_has_this(self.request.user):
            self.queryset = Quotation.objects.all()#.order_by('opened').reverse()
        else:
            queryset = Quotation.objects.all().exclude(file_no__startswith="TEMP__")#.order_by('opened').reverse()
            self.queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        if not self.queryset:
            return self.queryset
        self.opened_from = self.queryset.last().opened.strftime("%d. %B %Y").lstrip('0')
        self.opened_to = get_now(True)
        filter_query = {}

        for k, v in self.items.iteritems():
            if v != '0':
                filter_query[str(k)] = v
        for k,v in filter_query.iteritems():
            if ( k == 'q' and v != 0 ) or ( k == 'search_q' and v is not 'None' ):
                queries = shlex.split(v)
                q_all = Q() # Create an empty Q object to start with
                for q in queries:
                    q_objects = Q()
                    q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                    q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                    q_all.add(q_objects,Q.AND)
                self.queryset =  self.queryset.filter(q_all)
                self.search_q = v
            elif k=='from' and v !='':
                v = v.replace('%20',' ')
                self.opened_from = v
                self.queryset = self.queryset.filter(opened__date__gte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k=='to' and v != '':
                v = v.replace('%20',' ')
                self.opened_to = v
                self.queryset = self.queryset.filter(opened__date__lte=datetime.datetime.strptime(v, "%d.%m.%Y").date())
            elif k == 'Status':
                self.queryset = self.queryset.filter(status = v)
            elif k == 'Lawyers':
                lawyer = get_user_model().objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                if lawyer:
                    self.queryset = self.queryset.filter(lawyers = lawyer)

        for reg in self.queryset:
            if 'Status' in self.register_filter:
                self.register_filter['Status'].add(reg.status)
            else:
                self.register_filter['Status'] = set()
                self.register_filter['Status'].add(reg.status)
            #if reg.lawyers.first():
            # ~ if 'Lawyers' in self.register_filter and len(self.register_filter['Lawyers']) < 2:
                # ~ lawyer = reg.lawyers.first()
                # ~ if lawyer:
                    # ~ if 'Lawyers' in self.register_filter:
                        # ~ self.register_filter['Lawyers'].add(lawyer.first_name+' '+lawyer.last_name)
                    # ~ else:
                        # ~ self.register_filter['Lawyers'] = set()
                        # ~ self.register_filter['Lawyers'].add(lawyer.first_name+' '+lawyer.last_name)
        # ~ self.register_filter['Lawyers'] = lawyers
        self.form = FilterForm(self.request.GET, user=self.request.user, register_filter = self.register_filter,)
        self.query_request = self.request.GET
        return self.queryset

class QuotationCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create new Quotation File No.')}
    model = Register
    form_class = QuotationEntryCreateForm
    post_action_redirect = reverse_lazy('register:register_quotations_list')

    def dispatch(self, request, *args, **kwargs):
        return super(QuotationCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(QuotationCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            file_no = status = access = ''
            if 'file_no' in form.cleaned_data:
                file_no = form.cleaned_data['file_no']
            opened = datetime.datetime.strptime(form.cleaned_data['opened'], "%d.%m.%Y").date()
            parties = form.cleaned_data['parties']
            parties = parties.replace(u"\u2019", "'")
            parties = parties.replace(u"\u2013","-")
            parties = parties.replace(u'\u201c','"')
            parties = parties.replace(u'\u201d','"')
            parties = parties.replace(u'\xa3','GBP')
            parties = parties.replace(u'\xe9','e')
            if 'status' in form.cleaned_data:
                status = form.cleaned_data['status']
            if 'access' in form.cleaned_data:
                access = form.cleaned_data['access']
            if file_no == '':
                file_no = "TEMP__"+str(time.time())
            if status == '':
                status = 'Not active'
            register = Quotation(file_no=file_no,opened=opened,parties=parties,status=status)
            register.save()

            # Add to option list of all roles with register_view permission
            sp = StoredPermission.objects.get(name="register_view")
            roles = Role.objects.all()
            for r in roles:
                if sp in  r.permissions.all():
                    add_entry_to_option_list('Quotation',r,register)

            # Add to all roles listed in the access field
            for a in access:
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=register.pk,content_type=ContentType.objects.get_for_model(register), role=a
                )
                acl.permissions.add(StoredPermission.objects.get(name='register_view'))
                add_entry_to_option_list('Quotation',a,register)
            if file_no.startswith('TEMP__'):
                send_quotation_request_mail(self.request.user,register)
                messages.success(
                    self.request, _('Quotation number request has been sent.')
                )
                event_file_no_requested.commit(
                    actor=self.request.user, action_object=register, target=register
                )
            else:
                event_file_no_created.commit(
                    actor=self.request.user, action_object=register
                )
                if register.status == "Active":
                    event_file_no_activated.commit(
                        actor=self.request.user, action_object=register, target=register
                    )
        return HttpResponseRedirect(self.get_success_url())


class QuotationEditView(SingleObjectEditView):
    model = Quotation
    form_class = QuotationEntryEditForm
    object_permission = permission_register_edit

    def dispatch(self, request, *args, **kwargs):
        Permission.check_permissions(self.request.user,permission_register_edit)
        try:
            self.register_entry = Quotation.objects.get(pk=kwargs['pk'])
        except Quotation.DoesNotExist:
            return HttpResponseRedirect("/")
        self.post_action_redirect = reverse_lazy('register:register_quotation_detail', kwargs={'pk': self.register_entry.id})
        self.is_active = self.register_entry.status == 'Active'
        self.req_id = kwargs.pop('req_id',None)
        self.reg_id = kwargs.pop('pk', None)
        return super(QuotationEditView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(QuotationEditView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['req_id'] = self.req_id
        kwargs['reg_id'] = self.reg_id
        return kwargs

    def get_extra_context(self):
        label = self.get_object().file_no
        if self.get_object().file_no.startswith("TEMP__"):
            label = ''
        return {
            'object': self.get_object(),
            'title': _('Edit Quotation Number: %s') % label,
        }

    def form_valid(self, form):
        if form.is_valid():

            self.register_entry.file_no = form.cleaned_data['file_no']
            self.register_entry.opened = datetime.datetime.strptime(form.cleaned_data['opened'], "%d.%m.%Y").date()
            parties = form.cleaned_data['parties']
            parties = parties.replace(u"\u2019", "'")
            parties = parties.replace(u"\u2013","-")
            parties = parties.replace(u'\u201c','"')
            parties = parties.replace(u'\u201d','"')
            parties = parties.replace(u'\xa3','GBP')
            parties = parties.replace(u'\xe9','e')
            self.register_entry.parties = parties
            self.register_entry.status = form.cleaned_data['status']
            access = form.cleaned_data['access']
            acls = AccessControlList.objects.filter(object_id=self.register_entry.pk)
            for a in acls:
                remove_entry_from_option_list('Quotation',a.role,self.register_entry)
                a.delete()
            self.register_entry.save()

            # Add to option list of all roles with register_view permission

            sp = StoredPermission.objects.get(name="register_view")
            roles = Role.objects.all()
            for r in roles:
                if sp in  r.permissions.all():
                    add_entry_to_option_list('Quotation',r,self.register_entry)

            # Add to all roles listed in the access field
            for a in access:
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=self.register_entry.pk,content_type=ContentType.objects.get_for_model(self.register_entry), role=a
                )
                acl.permissions.add(StoredPermission.objects.get(name='register_view'))
                add_entry_to_option_list('Quotation',a,self.register_entry)

            if self.req_id:
                send_quotation_request_confirmation_mail(self.request.user, self.req_id, self.register_entry )
                messages.success(
                    self.request, _('Quotation number creation confirmation has been sent.')
                )
            if self.register_entry.status == "Active" and not self.is_active:
                event_file_no_activated.commit(
                    actor=self.request.user, action_object=self.register_entry, target=self.register_entry
                )

        return HttpResponseRedirect(self.get_success_url())


class QuotationListDocumentsView(SingleObjectListView):
    queryset_slice = None

    def dispatch(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            register_entry = Quotation.objects.get(pk=kwargs['pk'])
        else:
            document =  get_object_or_404(Document,pk=kwargs['id'])
            register_entry = document.register.first()
            if not register_entry:
                raise Http404

        self.file_no = register_entry
        queryset = register_entry.documents.all()
        self.queryset = AccessControlList.objects.filter_by_access(permission=permission_document_view, user=self.request.user, queryset=queryset)
        return super(
            QuotationListDocumentsView, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        try:
            return super(QuotationListDocumentsView, self).get_context_data(**kwargs)
        except Exception as exception:
            messages.error(
                self.request, _(
                    'Error retrieving document list: %(exception)s.'
                ) % {
                    'exception': exception
                }
            )
            self.object_list = Quotation.objects.none()
            return super(QuotationListDocumentsView, self).get_context_data(**kwargs)

    def get_extra_context(self):
        title = 'All documents for Quotation Number.: <b>'+self.file_no.file_no+'</b><br />Parties: <b>'+ self.file_no.parties+'</b>'
        return {
            'hide_links': True,
            'list_as_items': True,
            'no_results_icon': icon_document_list,
            'no_results_text': _(
                'This could mean that no documents have been uploaded or '
                'that your user account has not been granted the view '
                'permission for any document or document type.'
            ),
            'no_results_title': _('No documents available'),
            'title': title,
        }




def open_pdf(response,pdf,title):
    pdf = open('/tmp/'+pdf, 'rb')
    response = FileResponse(pdf)
    title = title.replace('_',' ')
    title += ".pdf"
    response['Content-Disposition'] = "attachment; filename=\""+title+"\""
    return response
