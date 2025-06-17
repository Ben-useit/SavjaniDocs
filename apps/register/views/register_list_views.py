from __future__ import absolute_import, unicode_literals
import json
import shlex
import uuid
from datetime import datetime
from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import Http404, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Count, Q
from django.utils.timezone import make_aware
from django.utils.encoding import force_text
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404
from acls.models import AccessControlList
from common.views import (
    SingleObjectListView,SingleObjectCreateView,
    SingleObjectEditView
)
from common.generics import ConfirmView
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from dynamic_search.mixins import SearchModelMixin
from sapitwa.utils import get_now
from clients.models import Client
from ..forms import RegisterFilterForm, ActiveFileTrackingChartEditForm, ActiveFileTrackingChartCreateForm
from ..icons import icon_register
from ..links import link_register_create, link_active_file_tracking_chart_create
from ..models import Register, Department,Status, Group, ActiveFileTrackingChart
from ..permissions import permission_register_view
from ..tasks import create_report
from ..events import event_file_no_transferred, event_file_no_transferred_out

class RegisterListPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = 'Register List'
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_report(queryset, title ,queryset.count(),'', get_now(True),True,user=self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Register_Files'}))
        return HttpResponseRedirect(reverse('register:register_list'))

from django.shortcuts import get_object_or_404
class RegisterListView(SearchModelMixin,SingleObjectListView):
    template_name = 'register/register_list.html'
    display_closed_files = False
    url = ''
    query = ''
    title = "Register Files"
    filter_active=False
    cache_key = None

    def dispatch(self, request, *args, **kwargs):
        self.department = kwargs.pop('department_id', None)
        if self.department:
            self.department = get_object_or_404(Department, pk=self.department)
        self.display_closed_files = self.request.user.user_options.display_closed_register_files
        self.search_query = self.request.GET.get('q',None)
        if not self.search_query:
            self.search_query = self.request.GET.get('search_query','')

        filter_query = self.request.GET.get('filter_query',None)
        if filter_query:
            self.filter_query = json.loads(filter_query)
        else:
            self.filter_query = {}
        return super(RegisterListView,self).dispatch(request, *args, **kwargs)

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
            'action_url' : 'register:register_list',
            'print_url': 'register:register_list_print',
            'print_csv': 'register:register_list_print_csv',
            'filter_active':self.filter_active,
            'no_results_text': _('Nothing'),
            'no_results_title': _('No Register Files'),
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
                elif key == 'clients':
                    self.filter_active = True
                    q_all.add(Q(clients__id__in=query),Q.AND)
                    self.filter_query['clients'] = query
                elif key == 'lawyers':
                    self.filter_active = True
                    q_all.add(Q(lawyers__id__in=query),Q.AND)
                    self.filter_query['lawyers'] = query
                elif key == 'departments':
                    self.filter_active = True
                    q_all.add(Q(department__id__in=query),Q.AND)
                    self.filter_query['departments'] = query
                elif key == 'groups':
                    self.filter_active = True
                    q_all.add(Q(group__id__in=query),Q.AND)
                    self.filter_query['groups'] = query
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
        if 'documents_check' in self.items and self.items['documents_check'] != '':
            self.filter_active = True
            documents = self.items['documents'][0]
            queryset = queryset.annotate(count = Count('documents') )
            queryset = queryset.filter(count__lte=documents)
            self.filter_query['documents_check'] = True
            self.filter_query['documents'] = documents

        if 'checklist' in self.items and self.items['checklist'] != '':
            self.filter_active = True
            queryset = queryset.exclude(registerchecklist=None)
            self.filter_query['checklist'] = True
        if 'status_report' in self.items and self.items['status_report'] != '':
            self.filter_active = True
            queryset = regs = queryset.filter(registerchecklist__checklist__name='Checklist on Commercial Department Files')
            self.filter_query['status_report'] = True
        if 'room' in self.items and self.items['room'] != '':
            self.filter_active = True
            queryset = regs = queryset.filter(room__gt='')
            self.filter_query['room'] = True
        # Based on the current queryset populate filter
        status_list = queryset.values_list('status', flat=True).distinct()
        status = Status.objects.filter(id__in=status_list)

        lawyers_list = queryset.values_list('lawyers', flat=True).distinct()
        lawyers = User.objects.filter(id__in=lawyers_list)

        clients_list = queryset.values_list('clients', flat=True).distinct()
        clients = Client.objects.filter(id__in=clients_list)
        groups_list = queryset.values_list('group', flat=True).distinct()
        groups = Group.objects.filter(id__in=groups_list)

        departments_list = queryset.values_list('department', flat=True).distinct()
        if self.department:
            departments_list = [self.department.pk,]
            self.filter_query['departments'] = departments_list
        departments = Department.objects.filter(id__in=departments_list)

        self.form = RegisterFilterForm(self.request.POST,
            status_list=status,
            lawyers = lawyers,
            clients = clients,
            groups = groups,
            departments = departments,
            initials = self.filter_query
        )
        self.total = queryset.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,queryset)
        return queryset

    def get_register_queryset(self, display_closed_files = False):

        if self.department:
            if display_closed_files:
                return Register.objects.filter(department=self.department)
            else:
                return Register.objects.filter(department=self.department).exclude(status__name='Closed')
        else:
            if display_closed_files:
                return Register.objects.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono').exclude(group__name='Debt Collection Files')
            else:
                regs = Register.objects.filter(
                    Q(status__name='Active') |
                    Q(status__name='Not active') |
                    Q(status__name='Dormant'))
                return regs.exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono').exclude(group__name='Debt Collection Files')

                return Register.objects.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono').exclude(group__name='Debt Collection Files').exclude(status__name='Closed')

class ActiveFileTrackingChartCreate(SingleObjectCreateView):
    extra_context = {'title': _('Create Chart')}
    #fields = ('date_closure', 'date_completion')
    form_class = ActiveFileTrackingChartEditForm
    model = ActiveFileTrackingChart
    post_action_redirect = reverse_lazy('register:active_file_tracking_chart_list')
    #view_permission = permission_tag_create

    def form_valid(self, form):
        if form.is_valid():
            obj = ActiveFileTrackingChart()
            if form.cleaned_data['retain_or_transfer']:
                obj.retain_or_transfer = form.cleaned_data['retain_or_transfer']
            if form.cleaned_data['date_closure_letter'] and form.cleaned_data['date_closure_letter'] != '':
                obj.date_closure_letter = datetime.strptime(form.cleaned_data['date_closure_letter'], "%d.%m.%Y").date()
            if form.cleaned_data['instructions'] and form.cleaned_data['instructions'] != '':
                obj.instructions = datetime.strptime(form.cleaned_data['instructions'], "%d.%m.%Y").date()
            if form.cleaned_data['notice'] and form.cleaned_data['notice'] != '':
                obj.notice = datetime.strptime(form.cleaned_data['notice'], "%d.%m.%Y").date()
            if form.cleaned_data['receipt'] and form.cleaned_data['receipt'] != '':
                obj.receipt = datetime.strptime(form.cleaned_data['receipt'], "%d.%m.%Y").date()
            if form.cleaned_data['date_completion'] and form.cleaned_data['date_completion'] != '':
                obj.date_completion = datetime.strptime(form.cleaned_data['date_completion'], "%d.%m.%Y").date()
            if form.cleaned_data['client']:
                obj.file_to = form.cleaned_data['client'].first()
            obj.save()
        return HttpResponseRedirect(self.get_success_url())

class ActiveFileTrackingChartEdit(SingleObjectEditView):
    extra_context = {'title': _('Edit Tracking Chart')}

    model = ActiveFileTrackingChart
    form_class = ActiveFileTrackingChartEditForm
    post_action_redirect = reverse_lazy('register:active_file_tracking_chart_list')
    #view_permission = permission_tag_create

    def form_valid(self, form):
        if form.is_valid():
            obj = self.get_object()
            if form.cleaned_data['retain_or_transfer']:
                obj.retain_or_transfer = form.cleaned_data['retain_or_transfer']
            if form.cleaned_data['date_closure_letter'] and form.cleaned_data['date_closure_letter'] != '':
                obj.date_closure_letter = datetime.strptime(form.cleaned_data['date_closure_letter'], "%d.%m.%Y").date()
            if form.cleaned_data['instructions'] and form.cleaned_data['instructions'] != '':
                obj.instructions = datetime.strptime(form.cleaned_data['instructions'], "%d.%m.%Y").date()
            if form.cleaned_data['notice'] and form.cleaned_data['notice'] != '':
                obj.notice = datetime.strptime(form.cleaned_data['notice'], "%d.%m.%Y").date()
            if form.cleaned_data['receipt'] and form.cleaned_data['receipt'] != '':
                obj.receipt = datetime.strptime(form.cleaned_data['receipt'], "%d.%m.%Y").date()
            if form.cleaned_data['date_completion'] and form.cleaned_data['date_completion'] != '':
                obj.date_completion = datetime.strptime(form.cleaned_data['date_completion'], "%d.%m.%Y").date()
            if form.cleaned_data['client']:
                obj.file_to = form.cleaned_data['client'].first()
            obj.save()
        return HttpResponseRedirect(self.get_success_url())

class ActiveFileTrackingChartAddFileView(RegisterListView):
    template_name = 'register/active_file_tracking_chart_list.html'
    def dispatch(self,request,*args,**kwargs):
        self.pk = kwargs.pop('pk',None)
        self.action_url = reverse_lazy('register:active_file_tracking_chart_add_file',kwargs={'pk':self.pk}),
        return super(ActiveFileTrackingChartAddFileView,self).dispatch(request,*args,**kwargs)

    def get_extra_context(self):
        context = super(ActiveFileTrackingChartAddFileView,self).get_extra_context()
        context['hide_links'] = True
        context['obj_pk'] = self.pk
        #context['action_url'] = self.action_url
        return context

class ActiveFileTrackingChartProcessAddingView(ConfirmView):
    success_message = 'Activated all File numbers.'
    success_message_plural = 'Activated all File numbers.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_list'
    )

    def dispatch(self, request, *args, **kwargs):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        pk = kwargs.pop('pk',None)
        self.obj = get_object_or_404(ActiveFileTrackingChart, pk=pk)
        self.post_action_redirect = reverse_lazy('register:active_file_tracking_chart_list')
        return super(ActiveFileTrackingChartProcessAddingView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': _('Add all selected files to the avtife file tracking chart?'),
            'next': self.post_action_redirect
        }

    def get_post_action_redirect(self):
        return reverse('register:active_file_tracking_chart_list')

    def view_action(self):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        regs = Register.objects.filter(pk__in=id_list.split(','))
        for r in regs:
            r.status = Status.objects.get(name="Transferred out")
            r.save()
            self.obj.files.add(r)
            event_file_no_transferred_out.commit(
                actor=self.request.user, action_object=r, target=r
            )
        messages.success(
            self.request, _('All selected files added.')
        )

class ActiveFileTrackingChartListFilesView(RegisterListView):
    template_name = 'register/active_file_tracking_chart_file_list.html'
    def dispatch(self,request,*args,**kwargs):
        pk = kwargs.pop('pk',None)
        self.obj = get_object_or_404(ActiveFileTrackingChart, pk=pk)
        return super(ActiveFileTrackingChartListFilesView,self).dispatch(request,*args,**kwargs)

    def get_register_queryset(self, display_closed_files = False):

        if self.department:
            if display_closed_files:
                return self.obj.files.filter(department=self.department)
            else:
                return self.obj.files.filter(department=self.department).exclude(status__name='Closed')
        else:
            if display_closed_files:
                return self.obj.files.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono')
            else:
                return self.obj.files.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono').exclude(status__name='Closed')

class ActiveFileTrackingChartListView(SingleObjectListView):
    #object_permission = permission_tag_view

    def get_extra_context(self):
        return {
            'hide_link': True,
            'hide_object': True,
            'no_actions' : True,
            # ~ 'no_results_icon': icon_menu_tags,
            'no_results_main_link': link_active_file_tracking_chart_create.resolve(
                context=RequestContext(request=self.request)
            ),
            # ~ 'no_results_text': _(
                # ~ 'Tags are color coded properties that can be attached or '
                # ~ 'removed from documents.'
            # ~ ),
            #'no_results_title': _('No tags available'),
            'title': _('Transferred Register Files')
        }

    def get_object_list(self):
        return ActiveFileTrackingChart.objects.all()

class ActiveFileTrackingChartDetailsView(RegisterListView):
    '''
    Displays details of an Active File Tracking Record
    pk can either be the pk of an ActiveFileTrackingChart object
    or a register file object.
    '''
    template_name = 'register/active_file_tracking_chart_file_list.html'
    title = 'Active File Tracking Chart Details'
    def dispatch(self,request,*args,**kwargs):
        reg_pk = kwargs.pop('reg_pk',None)
        aftc_pk = kwargs.pop('aftc_pk',None)
        self.obj = None

        if reg_pk:
            obj = get_object_or_404(Register,pk=reg_pk)
            self.obj = obj.activefiletrackingchart_set.first()
        elif aftc_pk:
            self.obj = get_object_or_404(ActiveFileTrackingChart,pk=aftc_pk)
        if not self.obj:
            raise Http404('No valid object')
        return super(ActiveFileTrackingChartDetailsView, self).dispatch(request,*args,**kwargs)

    def get_register_queryset(self, display_closed_files = False):

        if self.department:
            if display_closed_files:
                return self.obj.files.filter(department=self.department)
            else:
                return self.obj.files.filter(department=self.department).exclude(status__name='Closed')
        else:
            if display_closed_files:
                return self.obj.files.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono')
            else:
                return self.obj.files.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono').exclude(status__name='Closed')

    def get_extra_context(self):
        context = super(ActiveFileTrackingChartDetailsView,self).get_extra_context()
        context['chart_obj'] = self.obj
        context['title'] ='Active File Tracking Chart Details'
        return context

class RegisterListView1(SearchModelMixin,SingleObjectListView):
    template_name = 'register/register_list.html'
    http_method_names = ['get','post']
    filter_active = False
    title = 'Register Files'
    display_closed_files = False
    url = ''
    get_query = ''

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.user_options.block_password_change:
            self.display_closed_files = True
        cache_key = kwargs.pop('key',None)
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_report(queryset, self.title ,queryset.count(),'', get_now(True),True,user=self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Register_Files'}))

        self.items = self.request.POST
        if not self.items:
            self.items = self.request.GET
        return super(RegisterListView, self).dispatch(request, *args, **kwargs)

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
            #'register_search_form' : self.register_search_form,
            #'search_q' : self.search_q,
            'form' : self.form,
            #'query_request': json.dumps(self.query_request),
            'hide_object' : True,
            'hide_link': True,
            #'register_filter': self.register_filter,
            #'permission_register_edit' : self.register_edit_permission,
            'no_results_icon': icon_register,
            'no_results_main_link': link_register_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _('Nothing'),
            'no_results_title': _('No Register Files'),
            #'queryset_id_list':json.dumps(list(self.queryset_id_list)),
            'filter_active': self.filter_active,
            'cache_key' : self.cache_key,
            'total' : self.total,
            'url_filter': self.url,
            'get_query': self.get_query,
            'action_url' : 'register:register_list',
            'print_url' : 'register:register_list_print',
            'display_closed_files' : self.display_closed_files,
            'title': mark_safe(self.title +'<br><span style="font-size:0.8em;">Total: '+ str(self.total)+'</span>'),
        }
    def get_register_queryset(self, display_closed_files = False):

        if display_closed_files:
            return Register.objects.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files')
        else:
            return Register.objects.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(status__name='Closed')

    def get_object_list(self):
        #if self.request.GET:
        if 'q' in self.request.GET:
            query_string = self.request.GET.get('q','')
            queries = shlex.split(query_string)
            self.get_query = query_string
            q_all = Q() # Create an empty Q object to start with
            for q in queries:
                q_objects = Q()
                q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                q_all.add(q_objects,Q.AND)
            if 'closed_files' in self.request.GET:
                self.request.user.user_options.block_password_change = True
                self.request.user.user_options.save()
                self.display_closed_files = True
            else:
                self.request.user.user_options.block_password_change = False
                self.request.user.user_options.save()
                self.display_closed_files = False
            queryset = self.get_register_queryset(display_closed_files=self.display_closed_files)
            queryset = queryset.filter(q_all)
        else:
            self.items = dict(self.items.iterlists())
            q_all = Q()
            for key, query in self.items.iteritems():
                if query:
                    if key == 'get_query':
                        queries = query[0].split(' ')
                        self.url += '&get_query='+' '.join(query)
                        for q in queries:
                            q_objects = Q()
                            q_objects.add(Q(**{'%s__%s' % ('file_no', 'icontains'): q }), Q.OR)
                            q_objects.add(Q(**{'%s__%s' % ('parties', 'icontains'): q }), Q.OR)
                            q_all.add(q_objects,Q.AND)
                    elif key == 'status':
                        self.filter_active = True
                        q_all.add(Q(status_id__in=query),Q.AND)
                        for q in query:
                            self.url += '&status='+q
                    elif key == 'clients':
                        self.filter_active = True
                        q_all.add(Q(clients__id__in=query),Q.AND)
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
            queryset = self.get_register_queryset(display_closed_files=self.display_closed_files)
            queryset = queryset.filter(q_all).distinct()
            if 'documents_check' in self.items and self.items['documents_check'] != '':
                self.filter_active = True
                documents = self.items['documents'][0]
                queryset = queryset.annotate(count = Count('documents') )
                queryset = queryset.filter(count__lte=documents)
            if 'checklist' in self.items and self.items['checklist'] != '':
                self.filter_active = True
                queryset = queryset.exclude(registerchecklist=None)

        queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)
        self.total = queryset.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,queryset)

        # ~ # collect entries for filter
        status_list = queryset.values_list('status', flat=True).distinct()
        status = Status.objects.filter(id__in=status_list)

        lawyers_list = queryset.values_list('lawyers', flat=True).distinct()
        lawyers = User.objects.filter(id__in=lawyers_list)

        clients_list = queryset.values_list('clients', flat=True).distinct()
        clients = Client.objects.filter(id__in=clients_list)
        groups_list = queryset.values_list('group', flat=True).distinct()
        groups = Group.objects.filter(id__in=groups_list)

        departments_list = queryset.values_list('department', flat=True).distinct()
        departments = Department.objects.filter(id__in=departments_list)

        self.queryset_id_list = queryset.values_list('id', flat=True)

        self.form = RegisterFilterForm(self.request.POST,
            status_list=status,
            lawyers = lawyers,
            clients = clients,
            groups = groups,
            departments = departments,
        )
        return queryset

    def filter_queryset(self, queryset, value):
        pass

class RegisterDebtCollectionFilesListView(RegisterListView):
    title = 'Debt Collection Files'
    def get_extra_context(self):
        context = super(RegisterDebtCollectionFilesListView, self).get_extra_context()
        context.update(
            {
                'action_url' : 'register:register_debt_collection_list',
                'print_url' :   'register:register_debt_collection_list_print',
                'display_group': False,
            }
        )
        return context


    def get_register_queryset(self,display_closed_files=False):
        if display_closed_files:
            return Register.objects.filter(group__name='Debt Collection Files')
        else:
            return Register.objects.filter(group__name='Debt Collection Files').exclude(status__name='Closed')

class RegisterDebtCollectionFilesPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = "Debt Collection Files"
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_report(queryset, title ,queryset.count(),'', get_now(True),False,user=self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Debt_Collection_Files'}))
        return HttpResponseRedirect(reverse('register:register_debt_collection_list'))


class RegisterAuditListView(RegisterListView):
    title = 'Audit Report Files'
    def get_extra_context(self):
        context = super(RegisterAuditListView, self).get_extra_context()
        context.update(
            {
                'action_url' : 'register:register_audit_list',
                'print_url' :   'register:register_audit_list_print',
                'display_group': False,
            }
        )
        return context


    def get_register_queryset(self,display_closed_files=False):
        if display_closed_files:
            return Register.objects.filter(group__name='Audit Reports')
        else:
            return Register.objects.filter(group__name='Audit Reports').exclude(status__name='Closed')

class RegisterAuditListPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = "Audit Files"
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_report(queryset, title ,queryset.count(),'', get_now(True),False,user=self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Audit_Files'}))
        return HttpResponseRedirect(reverse('register:register_audit_list'))

class RegisterGeneralNonBillableListView(RegisterListView):

    title = 'General & Non-Billable Files'

    def get_extra_context(self):
        context = super(RegisterGeneralNonBillableListView, self).get_extra_context()
        context.update(
            {
                'action_url' : 'register:register_general_non_billable_list',
                'print_url' :   'register:register_general_non_billable_list_print',
                'display_group': False,
            }
        )
        return context

    def get_register_queryset(self, display_closed_files=False):
        if display_closed_files:
            return Register.objects.filter(group__name='General and Non-Billable Files')
        else:
            return Register.objects.filter(group__name='General and Non-Billable Files').exclude(status__name='Closed')

class RegisterGeneralNonBillableListPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = "General & Non-billable Files"
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_report(queryset, title ,queryset.count(),'', get_now(True),False,user=self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'General_&_Non-billable_Files'}))
        return HttpResponseRedirect(reverse('register:register_general_non_billable_list_print'))

class RegisterProBonoListView(RegisterListView):

    title = 'Pro Bono Files'

    def get_extra_context(self):
        context = super(RegisterProBonoListView, self).get_extra_context()
        context.update(
            {
                'action_url' : 'register:register_probono_list',
                'print_url' :   'register:register_probono_list_print',
                'display_group': False,
            }
        )
        return context

    def get_register_queryset(self, display_closed_files=False):
        if display_closed_files:
            return Register.objects.filter(group__name='Pro Bono')
        else:
            return Register.objects.filter(group__name='Pro Bono').exclude(status__name='Closed')

class RegisterProBonoListPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = "Pro Bono Files"
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_report(queryset, title ,queryset.count(),'', get_now(True),False,user=self.request.user)
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Pro_Bono_Files'}))
        return HttpResponseRedirect(reverse('register:register_probono_list'))

from tempfile import NamedTemporaryFile
class RegisterListPrintCSVView(SingleObjectListView):

    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                result = 'Opened,File Number,Parties,Client,Docs,Status\n'
                for r in queryset:
                    line = ''
                    line += r.opened.strftime("%d %b %Y")
                    line +=','+str(r.file_no)
                    line +=','+r.parties.replace(',',';')
                    line +=','+r.get_client_name()
                    line +=','+str(r.get_document_count(self.request.user))
                    line +=','+r.status.name+'\n'
                    result += line
                tmp_file = NamedTemporaryFile(delete=False)
                tmp_file.write(result)
                tmp_file.close()
                #return tmp_file.name.split('/')[2]
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':tmp_file.name.split('/')[2],'title':'Register_CSVcsv'}))
        return HttpResponseRedirect(reverse('register:register_list'))

