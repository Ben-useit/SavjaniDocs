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
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
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

from ..models import Register, Quotation, Department, Status
from ..permissions import (
    permission_register_view, permission_register_edit, permission_register_create,
)
from ..forms import ( RegisterSearchForm,
    QuotationEntryCreateForm, QuotationEntryEditForm, QuotationSearchForm, FilterForm,
    RegisterRequestTransferForm, RegisterStatisticForm, RegisterEditGroupForm,
    DepartmentFilterForm
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
from ..tasks import create_report, create_statistic_report, create_client_report, create_department_report

#Department
class DepartmentCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create new department')}
    model = Department
    fields = ['name']
    post_action_redirect = reverse_lazy('register:department_list')

class DepartmentListPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = 'Department List'
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_department_report(queryset, title,self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Department_Report'}))
        return HttpResponseRedirect(reverse('register:department_list'))


class DepartmentListView(SearchModelMixin,SingleObjectListView):

    template_name = 'register/department_list.html'
    display_closed_files = False
    url = ''
    query = ''
    title = "Departments"
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
        return super(DepartmentListView,self).dispatch(request, *args, **kwargs)
            
    def get_object_list(self):
        return Department.objects.all().order_by('name')

    def get_object_list(self):

        # if checkbox was altered, update user setting
        # ~ if 'q' in self.request.GET:
            # ~ if 'closed_files' in self.request.GET:
                # ~ self.request.user.user_options.display_closed_register_files = True
                # ~ self.request.user.user_options.save()
                # ~ self.display_closed_files = True
            # ~ else:
                # ~ self.request.user.user_options.display_closed_register_files = False
                # ~ self.request.user.user_options.save()
                # ~ self.display_closed_files = False
          
        queryset = self.get_department_queryset()
        #queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)

        # Process queries in search box
        # ~ if self.search_query:
            # ~ queries = shlex.split(self.search_query)
            # ~ q_all = Q()
            # ~ for q in queries:
                # ~ q_objects = Q()
                # ~ q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                # ~ q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                # ~ q_all.add(q_objects,Q.AND)
            # ~ queryset = queryset.filter(q_all)

        # Process filter entries
        # current entries
        self.items = dict(self.request.GET.iterlists())
        q_all = Q()
        for key, query in self.items.iteritems():
            if query:
                if key == 'status':
                    self.filter_active = True
                    q_all.add(Q(register__status_id__in=query),Q.AND)
                    self.filter_query['status'] = query
                elif key == 'lawyers':
                    self.filter_active = True
                    q_all.add(Q(register__lawyers__id__in=query),Q.AND)
                    self.filter_query['lawyers'] = query
                elif key == 'departments':
                    self.filter_active = True
                    q_all.add(Q(register__department__id__in=query),Q.AND)
                    self.filter_query['departments'] = query
                elif key == 'from' and query[0] != '':
                    self.filter_active = True
                    opened_from = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(register__opened__gte=opened_from),Q.AND)
                    self.filter_query['from'] = query[0]
                elif key == 'to' and query[0] != '':
                    self.filter_active = True
                    opened_to = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(register__opened__lte=opened_to),Q.AND)
                    self.filter_query['to'] = query[0]
        queryset = queryset.filter(q_all).distinct()
        # Based on the current queryset populate filter
        status_list = queryset.values_list('register__status', flat=True).distinct()
        status = Status.objects.filter(id__in=status_list)

        lawyers_list = queryset.values_list('register__lawyers', flat=True).distinct()
        lawyers = User.objects.filter(id__in=lawyers_list)

        departments_list = queryset.values_list('register__department', flat=True).distinct()
        departments = Department.objects.filter(id__in=departments_list)

        self.form = DepartmentFilterForm(self.request.POST,
            status_list=status,
            lawyers = lawyers,
            departments = departments,
            initials = self.filter_query
        )
        self.total = queryset.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,queryset)
        return queryset

    def get_department_queryset(self, display_closed_files = False):
        return Department.objects.all()

        
    def get_extra_context1(self):
        regs = Register.objects.exclude(department=None)
        return {
            'hide_object' : True,
            'hide_link': True,
            'no_results_title': _('No departments.'),
            'title': _('Departments:'),
            'total_matters' : regs.count(),
            'total_active' : regs.filter(status__name='Active').count(),
            'total_not_active' : regs.filter(status__name='Not active').count(),
            'total_dormant' : regs.filter(status__name='Dormant').count(),
            'total_closed' : regs.filter(status__name='Closed').count(),
            'total_transferred_to_client' : regs.filter(status__name='Transferred to client').count(),
        }

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
            'action_url' : 'register:department_list',
            'print_url': 'register:register_list_print',
            'print_csv': 'register:register_list_print_csv',
            'filter_active':self.filter_active,
            'no_results_text': _('Nothing'),
            'no_results_title': _('No Departments'),
            'search_query':self.search_query,
            'filter_query':json.dumps(self.filter_query),
            'display_group': True,
            'title': mark_safe(self.title +'<br><span style="font-size:0.8em;">Total: '+ str(self.total)+'</span>'),
        }
        
class DepartmentEditView(SingleObjectEditView):
    model = Department
    fields = ['name']


class DeleteDepartmentListMatterView(SingleObjectListView):
    queryset_slice = None
    def dispatch(self, request, *args, **kwargs):
        if 'pk' in kwargs:
            department = Department.objects.get(pk=kwargs['pk'])
            Register.objects.filter(department=department)
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
            return super(DepartmentListMatterView, self).get_context_data(**kwargs)
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
        title = _('Files')
        return {
            'hide_links': True,
            'list_as_items': True,
            'no_results_icon': icon_document_list,
            'no_results_text': _(
                ''
            ),
            'no_results_title': _('No files available'),
            'title': title,
        }

    def get_success_url(self):
        matters =','.join([str(int) for int in self.queryset.values_list('id', flat=True)])
        return reverse_lazy('register:register_list', kwargs={'id_list': matters.replace(',','_')})
