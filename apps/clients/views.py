from __future__ import absolute_import, unicode_literals
import uuid
import json
from django.db.models import Count, Q
from django.core.cache import cache
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from bootstrap_modal_forms.generic import BSModalCreateView
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from common.generics import (
    SingleObjectListView, SingleObjectCreateView, SingleObjectDeleteView,
    SingleObjectEditView, SingleObjectDetailView
)
from register.models import Register, Department, Status, Group
from register.permissions import permission_register_view
from register.settings import access_choices
from sapitwa.utils import get_now
from .forms import ContactCreateForm, ClientFilterForm, ClientCreateForm, ClientEditForm, ClientListFilesFilterForm
from .models import Client, Contact
from .permissions import permission_client_create, permission_client_view
from .tasks import create_report


def contact(request):
    data = dict()
    if request.method == 'GET':
        contact = Contact.objects.last()
        return HttpResponseRedirect(reverse_lazy(viewname='clients:client_create'))


class ClientCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create Client')}
    #form_class = ClientCreateForm
    post_action_redirect = reverse_lazy(viewname='clients:client_list')
    view_permission = permission_client_create
    model = Client
    fields = ('name', 'address', 'city','is_ex_lawyer')
    template_name = 'clients/client_create.html'
    data = None

    def dispatch(self, request, *args, **kwargs):
        self.cache_key = kwargs.pop('key',None)
        self.data = cache.get(self.cache_key)
        if request.resolver_match.url_name == 'client_create_from_register':
            self.post_action_redirect = reverse_lazy(viewname='register:register_create', kwargs={'key':self.cache_key})
        return super(ClientCreateView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        context = super(ClientCreateView,self).get_extra_context()
        if self.data:
            context['form'] = ClientCreateForm(data = self.data)
            if 'contacts' in self.data:
                context['contacts'] = self.data['contacts']
        return context

    def form_valid(self, form):
        if 'add_contact' in self.request.POST:
            # Cache form data and display create contact form
            if self.cache_key:
                data['client'] = form.save(commit=False)
                cache.set(self.cache_key,data)
            else:
                self.cache_key = force_text(uuid.uuid4()).replace('-','')
                data = {}
                data['client'] = form.save(commit=False)
                cache.set(self.cache_key,data)
            return HttpResponseRedirect(reverse_lazy(viewname='clients:contact_create', kwargs={'key': self.cache_key }))
        else:
            if self.cache_key:
                #data = cache.get(self.cache_key)
                client = form.save()
                client.save()
                if 'contacts' in self.data:
                    contacts = self.data['contacts']
                    for contact in contacts:
                        contact.save()
                        contact.clients.add(client)
            else:
                form.save()
        return HttpResponseRedirect(self.get_success_url())

class ClientDetailView(SingleObjectDetailView):
    fields = ('name', 'address','city')
    model = Client
    pk_url_kwarg = 'client_pk'
    post_action_redirect = reverse_lazy(viewname='clients:client_list')
    view_permission = permission_client_view
    template_name = 'clients/client_create.html'

    def get_extra_context(self):
        client = get_object_or_404(Client, pk=self.kwargs['client_pk'])
        context = {}
        context['contacts'] = client.clients.all()
        context['object'] = client
        context['title'] = 'Details for client : '+ client.name
        return context

    def get_object(self):
        return get_object_or_404(Client, pk=self.kwargs['client_pk'])

class ClientEditView(SingleObjectEditView):
    fields = ('name', 'address','city','is_ex_lawyer')
    model = Client
    pk_url_kwarg = 'client_pk'
    post_action_redirect = reverse_lazy(viewname='clients:client_list')
    view_permission = permission_client_create
    template_name = 'clients/client_edit.html'
    cache_key = None

    def dispatch(self, request, *args, **kwargs):
        self.cache_key = kwargs.pop('key',None)
        self.object = get_object_or_404(Client, pk=self.kwargs['client_pk'])
        self.contacts = list(self.object.clients.all())
        return super(ClientEditView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        context = super(ClientEditView, self).get_extra_context()
        context['title'] = _('Edit client: %s') % self.object
        context['contacts'] = self.contacts
        if self.cache_key:
            context['form'] = ClientEditForm(data = cache.get(self.cache_key))
        return context

    def form_valid(self, form):
        '''
        Submit: > Save form and cached data
        Edit contact > ContactEditView
        Delete contact > ContactDeleteView
        Add contact > ContactCreateView
        '''
        if not self.cache_key:
            self.cache_key = force_text(uuid.uuid4()).replace('-','')
            data = {}
        else:
            data = cache.get(self.cache_key)
        data['client'] = form.save(commit=False)
        cache.set(self.cache_key,data)

        if 'add_contact' in self.request.POST:
            # Cache form data and display create contact form
            return HttpResponseRedirect(reverse_lazy(viewname='clients:contact_create', kwargs={'client_pk' : self.object.pk, 'key': self.cache_key }))

        delete_contact = [key for key, value in self.request.POST.items() if 'delete_contact' in key.lower()]
        if delete_contact:
            contact_pk = delete_contact[0].split('_')[2]
            return HttpResponseRedirect(reverse_lazy(viewname='clients:contact_delete', kwargs={'client_pk': self.object.pk, 'contact_pk': contact_pk, 'key': self.cache_key }))

        edit_contact = [key for key, value in self.request.POST.items() if 'edit_contact' in key.lower()]
        if edit_contact:
            contact_pk = edit_contact[0].split('_')[2]
            return HttpResponseRedirect(reverse_lazy(viewname='clients:contact_edit', kwargs={'client_pk': self.object.pk, 'contact_pk': contact_pk, 'key': self.cache_key }))

        #Submit
        client = data['client']
        client.save()
        return HttpResponseRedirect(reverse_lazy(viewname='clients:client_list'))

    def get_object(self):
        return get_object_or_404(Client, pk=self.kwargs['client_pk'])

class ClientListFilesView(SingleObjectListView):
    object_permission = permission_register_view
    template_name = 'clients/client_list_files.html'
    http_method_names = ['get','post']
    filter_active = False

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Client, pk=self.kwargs['client_pk'])
        self.items = self.request.POST
        return super(ClientListFilesView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty:
            # When pagination is enabled and object_list is a queryset,
            # it's better to do a cheap query than to load the unpaginated
            # queryset in memory.
            if self.get_paginate_by(self.object_list) is not None and hasattr(self.object_list, 'exists'):
                is_empty = not self.object_list.exists()
            else:
                is_empty = not self.object_list
            if is_empty:
                raise Http404(_('Empty list and "%(class_name)s.allow_empty"     is False.') % {
                    'class_name': self.__class__.__name__,
                })
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_extra_context(self):
        return {
            'form':self.form,
            'hide_link': True,
            'hide_object': True,
            'client_object': self.object,
            'no_results_text': _(
                ''
            ),
            'no_results_title': _('No files attached to the client %s') % self.object,
            'title': _('Files attached to the client %s') % self.object,
            'total' : self.total,
            'filter_active': self.filter_active,
        }

    def get_object_list(self):
        # ~ contact_list = self.object.contact_set.all().values_list('id',flat=True)
        if self.request.GET:
            query_string = self.request.GET.copy()['q']
            queries = shlex.split(query_string)
            q_all = Q() # Create an empty Q object to start with
            for q in queries:
                q_objects = Q()
                q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                q_all.add(q_objects,Q.AND)
            queryset = self.object.register_set.all()
            queryset = queryset.filter(q_all)
        else:
            self.items = dict(self.items.iterlists())
            q_all = Q()
            for key, query in self.items.iteritems():
                if query:
                    if key == 'status':
                        self.filter_active = True
                        q_all.add(Q(status_id__in=query),Q.AND)
                    elif key == 'files':
                        self.filter_active = True
                        q_all.add(Q(id__in=query),Q.AND)
                    elif key == 'lawyers':
                        self.filter_active = True
                        q_all.add(Q(lawyers__id__in=query),Q.AND)
                    elif key == 'departments':
                        self.filter_active = True
                        q_all.add(Q(department__id__in=query),Q.AND)
                    elif key == 'groups':
                        self.filter_active = True
                        q_all.add(Q(group__id__in=query),Q.AND)
                    elif key == 'from' and query[0] != '':
                        self.filter_active = True
                        opened_from = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(opened__gte=opened_from),Q.AND)
                    elif key == 'to' and query[0] != '':
                        self.filter_active = True
                        opened_to = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(opened__lte=opened_to),Q.AND)
            queryset = self.object.register_set.all()
            queryset = queryset.filter(q_all).distinct()
            if 'documents_check' in self.items and self.items['documents_check'] != '':
                self.filter_active = True
                documents = self.items['documents'][0]
                queryset = queryset.annotate(count = Count('documents') )
                queryset = queryset.filter(count__lte=documents)
            if 'checklist' in self.items and self.items['checklist'] != '':
                self.filter_active = True
                queryset = queryset.exclude(registerchecklist=None)

        self.total = queryset.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,queryset)

        # collect entries for filter
        status_list = queryset.values_list('status', flat=True).distinct()
        status = Status.objects.filter(id__in=status_list)

        files = queryset

        lawyers_list = queryset.values_list('lawyers', flat=True).distinct()
        lawyers = User.objects.filter(id__in=lawyers_list)

        groups_list = queryset.values_list('group', flat=True).distinct()
        groups = Group.objects.filter(id__in=groups_list)

        departments_list = queryset.values_list('department', flat=True).distinct()
        departments = Department.objects.filter(id__in=departments_list)

        self.queryset_id_list = queryset.values_list('id', flat=True)

        self.form = ClientListFilesFilterForm(self.request.POST,
            status_list=status,
            lawyers = lawyers,
            groups = groups,
            departments = departments,
            files = files
        )
        return queryset

class ClientListView(SingleObjectListView):
    template_name = 'clients/client_list.html'
    object_permission = permission_client_view
    display_closed_files = True
    title = "Client List"
    filter_active=False
    cache_key = None
    list_external = False


    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_report(queryset, 'Clients',queryset[0].count())
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Clients'}))

        self.search_query = self.request.GET.get('q',None)
        if not self.search_query:
            self.search_query = self.request.GET.get('search_query','')

        filter_query = self.request.GET.get('filter_query',None)
        if filter_query:
            self.filter_query = json.loads(filter_query)
        else:
            self.filter_query = {}
        return super(ClientListView,self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'form' : self.form,
            'hide_link': True,
            'hide_object': True,
            'no_results_text': '',
            'no_results_title': _('No clients available'),
            'cache_key': self.cache_key,
            'display_closed_files' : self.display_closed_files,
            'hide_object' : True,
            'hide_link': True,
            'action_url' : 'clients:client_list',
            'print_url': 'clients:clients_list_print',
            'filter_active':self.filter_active,
            'search_query':self.search_query,
            'filter_query':json.dumps(self.filter_query),
            'lawyers' : self.lawyers,
            'active' : self.active,
            'not_active' :    self.not_active,
            'dormant' :    self.dormant,
            'closed' :    self.closed,
            'misc' :   self.misc,
            'all' :   self.all,
            'title': mark_safe(
                self.title
                +'<br><span style="font-size:0.8em;">Total: '
                + str(self.total)
                +'<br>'
                + self.filter+'</span>'
            ),

        }

    def get_object_list(self):
        self.filter = ''
        # ~ if self.request.GET:
            # ~ query_string = self.request.GET.copy()['q']
            # ~ queries = shlex.split(query_string)
            # ~ q_all = Q() # Create an empty Q object to start with
            # ~ for q in queries:
                # ~ q_objects = Q()
                # ~ q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                # ~ q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                # ~ q_all.add(q_objects,Q.AND)
            # ~ queryset = Client.objects.all()
            # ~ queryset = queryset.filter(q_all)
        # ~ else:
        self.items = dict(self.request.GET.iterlists())
        q_all = Q()
        self.clients = None
        self.contacts = None
        regs = Register.objects.all()
        for key, query in self.items.iteritems():
            if query:
                if key == 'clients':
                    self.filter_active = True
                    q_all.add(Q(id__in=query),Q.AND)
                    self.filter_query['clients'] = query
                    self.clients = query
                    regs = regs.filter(clients__pk__in=query)
                elif key == 'contacts':
                    self.filter_active = True
                    q_all.add(Q(clients__id__in=query),Q.AND)
                    self.filter_query['contacts'] = query
                    self.contacts = query
                    regs = regs.filter(contacts__pk__in=query)

        queryset = self.get_client_list()
        queryset = queryset.filter(q_all)
        if 'status' in self.items and self.items['status']:
            queryset = queryset.filter(register__status__pk__in=self.items['status']).distinct()
            self.filter_active = True
            self.filter_query['status'] = self.items['status']

            self.filter += ' Status: '
            for x in self.items['status']:
                self.filter += Status.objects.get(pk=x).name+ ' '
        #regs = Register.objects.all()
        self.lawyers = None
        if 'lawyers' in self.items and self.items['lawyers']:
            queryset = queryset.filter(register__lawyers__pk__in=self.items['lawyers']).distinct()
            self.filter_active = True
            self.filter_query['lawyers'] = self.items['lawyers']
            self.lawyers = self.items['lawyers']
            regs = regs.filter(lawyers__pk__in=self.items['lawyers'])
            self.filter += ' Lawyer: '
            for x in self.items['lawyers']:
                self.filter += User.objects.get(pk=x).get_full_name()+ ' '
            # Clients filtered by status, lawyers
            #regs = Register.objects.filter(lawyers__pk__in=self.items['lawyers']


        # Calculate totals
        self.active = regs.filter(status__name='Active').count()
        self.not_active = regs.filter(status__name='Not active').count()
        self.dormant = regs.filter(status__name='Dormant').count()
        self.closed = regs.filter(status__name='Closed').count()
        status = ['Active','Not active','Dormant','Closed']
        self.misc = regs.exclude(status__name__in=status).count()
        self.all = regs.count()

        self.total = queryset.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,(queryset,self.lawyers,self.active,self.not_active,self.dormant,self.closed,
            self.misc, self.all, self.filter))

        # collect entries for filter
        contacts_list = queryset.exclude(clients__name=None).values_list('clients', flat=True).distinct()
        contacts = Contact.objects.filter(id__in=contacts_list).exclude(name='')

        lawyers = []
        for a,b in access_choices.value:
            lawyers.append(User.objects.get(first_name=a.split(' ')[0],last_name=a.split(' ')[1]).pk)
        lawyers = User.objects.filter(pk__in=lawyers)

        self.form = ClientFilterForm(
            self.request.POST,
            clients_list=queryset,
            contacts_list = contacts,
            lawyers_list = lawyers,
            status_list = Status.objects.all(),
            initials = self.filter_query
        )
        self.count = queryset.count()
        return queryset

    def get_client_list(self):
        return Client.objects.all()

# ~ class ClientExtListView(ClientListView):
    # ~ def get_client_list(self):
        # ~ return Client.objects.filter(is_ex_lawyer=True)

class ContactCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create Contact')}
    form_class = ContactCreateForm
    post_action_redirect = reverse_lazy(viewname='clients:client_list')
    view_permission = permission_client_create
    template_name = 'clients/contact_create.html'
    success_message = 'Success: Contact was created.'
    success_url = reverse_lazy(viewname='clients:client_create')
    client = None
    def dispatch(self, request, *args, **kwargs):
        self.cache_key = kwargs.pop('key',None)
        client_pk = kwargs.pop('client_pk',None)
        if client_pk:
            self.client = get_object_or_404(Client, pk=client_pk)
        if self.cache_key:
            self.success_url = reverse_lazy(viewname='clients:client_create', kwargs={'key': self.cache_key })
        return super(ContactCreateView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        contact = form.save()
        data = cache.get(self.cache_key)
        if data:
            if 'contacts' not in data:
                data['contacts'] = []
            data['contacts'].append(contact)
            cache.set(self.cache_key,data)

        if self.client:
            contact.clients.add(self.client)
            return HttpResponseRedirect(
                reverse_lazy(
                    viewname='clients:client_edit',
                    kwargs={'client_pk':self.client.pk, 'key': self.cache_key }
                )
            )

        return HttpResponseRedirect(self.success_url)

class ContactEditView(SingleObjectEditView):
    fields = ('name', 'position','phone', 'email')
    model = Contact
    pk_url_kwarg = 'contact_pk'
    #post_action_redirect = reverse_lazy(viewname='clients:client_list')
    view_permission = permission_client_create
    template_name = 'clients/contact_create.html'
    cache_key = None

    def dispatch(self, request, *args, **kwargs):
        self.cache_key = kwargs.pop('key',None)
        self.client_pk = kwargs.pop('client_pk',None)
        self.object = get_object_or_404(Contact, pk=self.kwargs['contact_pk'])
        return super(ContactEditView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': _('Edit Contact: %s') % self.object,
        }

    def form_valid(self, form):
        form.save()
        if not self.client_pk:
            # Edit was called directly
            # TODO reverse to contact_list
            return HttpResponseRedirect(reverse_lazy(viewname='clients:client_list'))
        # Edit was called through a client
        return HttpResponseRedirect(
            reverse_lazy(
                viewname='clients:client_edit',
                kwargs={'client_pk': self.client_pk, 'key': self.cache_key }
            )
        )

    def get_object(self):
        return get_object_or_404(Contact, pk=self.kwargs['contact_pk'])

class ContactDeleteView(SingleObjectDeleteView):
    model = Contact
    object_permission = permission_client_create
    pk_url_kwarg = 'contact_pk'
    post_action_redirect = reverse_lazy('client:setup_metadata_type_list')

    def dispatch(self,request,*args,**kwargs):
        client_pk = kwargs.pop('client_pk',None)
        cache_key = kwargs.pop('key', None)
        self.post_action_redirect = reverse_lazy('clients:client_edit', kwargs={'client_pk': client_pk, 'key': cache_key })
        return super(ContactDeleteView, self).dispatch(request, *args, **kwargs)


    def get_extra_context(self):
        return {
            'delete_view': True,
            'object': self.get_object(),
            'title': _('Delete the contact: %s?') % self.get_object(),
        }

