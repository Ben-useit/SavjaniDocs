from __future__ import absolute_import, unicode_literals

import logging
import time
import datetime
import operator
import uuid
import dateutil.parser
import json


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


from django.http import QueryDict
from urlparse import urlparse, urlunparse
from dateutil.parser import parse
from django.urls import reverse
from common.utils import get_aware_str_from_unaware
from user_management.views import GroupMembersView
from common.mixins import ( ObjectNameMixin,ViewPermissionCheckMixin,ExtraContextMixin,RedirectionMixin,FormExtraKwargsMixin,
    ObjectPermissionCheckMixin )
from permissions.models import Permission, StoredPermission, Role
from documents.models import Document
from documents.permissions import permission_document_view

from sapitwa.tasks import task_add_rw_permissions
from sapitwa.tasks import add_entry_to_option_list, remove_entry_from_option_list
from sapitwa.utils import get_now

from ..models import Register, Quotation, Department
from ..permissions import (
    permission_register_view, permission_register_edit, permission_register_create,

)
from ..forms import ( RegisterSearchForm,
    QuotationEntryCreateForm, QuotationEntryEditForm, QuotationSearchForm, FilterForm,
    RegisterRequestTransferForm, RegisterStatisticForm, RegisterEditGroupForm,
)
from ..tasks import ( send_register_request_mail,send_register_request_confirmation_mail,
    send_quotation_request_mail,send_quotation_request_confirmation_mail,
    send_register_request_transfer_mail, send_register_request_close_mail )
from ..links import link_register_create, link_register_quotation_create
from ..icons import icon_document_list, icon_register
from ..events import ( event_file_no_created,event_file_no_requested,event_file_no_activated,
    event_file_no_transferred, event_file_no_closed, event_file_no_not_active,
    event_file_no_transferred_to_client, event_file_no_dormant )
from ..settings import ( register_status_choices, access_choices, abbr )
from ..tasks import create_report, create_statistic_report, create_client_report

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

from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from ..forms import QuotationFilterForm
from ..models import Status
from ..tasks import create_quotation_report
class QuotationListPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = 'Quotation List'
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_quotation_report(queryset, title ,queryset.count(),'', get_now(True),False,user=self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Quotation_Files'}))
        return HttpResponseRedirect(reverse('register:register_quotations_list'))

from tempfile import NamedTemporaryFile
class QuotationListPrintCSVView(SingleObjectListView):
    
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                result = 'Opened,File Number,Parties,Docs,Status\n'
                for r in queryset:
                    line = ''
                    line += r.opened.strftime("%d %b %Y")
                    line +=','+str(r.file_no)
                    line +=','+str(r.parties.replace(',',';'))
                    line +=','+str(r.get_document_count(self.request.user))
                    line +=','+r.status.name+'\n'
                    result += line
                tmp_file = NamedTemporaryFile(delete=False)
                tmp_file.write(result)
                tmp_file.close()
                #return tmp_file.name.split('/')[2]
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':tmp_file.name.split('/')[2],'title':'Quotation_CSVcsv'}))
        return HttpResponseRedirect(reverse('register:register_list'))



class QuotationListView(SearchModelMixin,SingleObjectListView):
    template_name = 'register/quotation_list.html'
    display_closed_files = False
    url = ''
    query = ''
    title = "Quotation Files"
    filter_active=False
    cache_key = None

    def dispatch(self, request, *args, **kwargs):
        self.display_closed_files = self.request.user.user_options.display_closed_register_files
        self.search_query = self.request.GET.get('q',None)
        if not self.search_query:
            self.search_query = self.request.GET.get('search_query','')

        filter_query = self.request.GET.get('filter_query',None)
        if filter_query:
            self.filter_query = json.loads(filter_query)
        else:
            self.filter_query = {}
        return super(QuotationListView,self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'form' : self.form,
            'link_classes' : None,
            'cache_key': self.cache_key,
            'display_closed_files' : self.display_closed_files,
            'hide_object' : True,
            'hide_link': True,
            'no_results_icon': icon_register,
            'no_results_main_link': link_register_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'action_url' : 'register:register_quotations_list',
            'print_url': 'register:register_quotations_print',
            'print_csv': 'register:register_quotations_print_csv',
            'filter_active':self.filter_active,
            'no_results_text': _('Nothing'),
            'no_results_title': _('No Quotation Files'),
            'search_query':self.search_query,
            'filter_query':json.dumps(self.filter_query),
            'display_group': True,
            'title': mark_safe(self.title +'<br><span style="font-size:0.8em;">Total: '+ str(self.total)+'</span>'),
        }

    def get_object_list(self):

        # if checkbox was altered, update user setting
        if 'q' in self.request.GET:
            if 'closed_files' in self.request.GET:
                self.request.user.user_options.display_closed_register_files = True
                self.request.user.user_options.save()
                self.display_closed_files = True
            else:
                self.request.user.user_options.display_closed_register_files = False
                self.request.user.user_options.save()
                self.display_closed_files = False

        queryset = self.get_register_queryset(display_closed_files=self.display_closed_files)
        queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)


        # Process queries in search box
        if self.search_query:
            queries = shlex.split(self.search_query)
            q_all = Q()
            for q in queries:
                q_objects = Q()
                q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                q_all.add(q_objects,Q.AND)
            queryset = queryset.filter(q_all)

        # Process filter entries
        # current entries
        self.items = dict(self.request.GET.iterlists())
        q_all = Q()
        for key, query in self.items.iteritems():
            if query:
                if key == 'status':
                    self.filter_active = True
                    q_all.add(Q(status_id__in=query),Q.AND)
                    self.filter_query['status'] = query
                elif key == 'from' and query[0] != '':
                    self.filter_active = True
                    opened_from = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(opened__gte=opened_from),Q.AND)
                    self.filter_query['from'] = query[0]
                elif key == 'to' and query[0] != '':
                    self.filter_active = True
                    opened_to = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(opened__lte=opened_to),Q.AND)
                    self.filter_query['to'] = query[0]
        queryset = queryset.filter(q_all).distinct()

        if 'status_report' in self.items and self.items['status_report'] != '':
            self.filter_active = True
            queryset = regs = queryset.filter(registerchecklist__checklist__name='Checklist on Commercial Department Files')
            self.filter_query['status_report'] = True
        # Based on the current queryset populate filter
        status_list = queryset.values_list('status', flat=True).distinct()
        status = Status.objects.filter(id__in=status_list)

        self.form = QuotationFilterForm(self.request.POST,
            status_list=status,
            initials = self.filter_query
        )
        self.total = queryset.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,queryset)
        return queryset

    def get_register_queryset(self, display_closed_files = False):

        #if display_closed_files:
        return Quotation.objects.all()
        # ~ else:
            # ~ return Quotation.objects.all().exclude(status__name='Closed')

class QuotationListView1(SingleObjectListView):
    template_name = 'register/register_list.html'
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
    model = Quotation
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
            parties = parties.replace(u'\u2018','"')
            parties = parties.replace('\n','')
            parties = parties.replace(',',';')
            if 'status' in form.cleaned_data:
                status = form.cleaned_data['status']
            # ~ if 'access' in form.cleaned_data:
                # ~ access = form.cleaned_data['access']
            # ~ if file_no == '':
                # ~ file_no = "TEMP__"+str(time.time())
            # ~ if status == '':
                # ~ status = 'Not active'
            register = Quotation(file_no=file_no,opened=opened,parties=parties,status=status)
            register.save()

            # Add to option list of all roles with register_view permission
            # ~ sp = StoredPermission.objects.get(name="register_view")
            # ~ roles = Role.objects.all()
            # ~ for r in roles:
                # ~ if sp in  r.permissions.all():
                    # ~ add_entry_to_option_list('Quotation',r,register)

            # Add to all roles listed in the access field
            # ~ for a in access:
                # ~ acl, created = AccessControlList.objects.get_or_create(
                   # ~ object_id=register.pk,content_type=ContentType.objects.get_for_model(register), role=a
                # ~ )
                # ~ acl.permissions.add(StoredPermission.objects.get(name='register_view'))
                # ~ add_entry_to_option_list('Quotation',a,register)
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
                if register.status.name == "Active":
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
