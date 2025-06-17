from __future__ import absolute_import, unicode_literals

import logging
import uuid
import json
from datetime import datetime, timedelta
from actstream.models import Action, any_stream
from django.core.cache import cache
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text
from django.db.models import Count, Q
from django.utils.timezone import make_aware
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, reverse
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _, ungettext
from django.utils import timezone

from acls.models import AccessControlList
from common.views import (
    MultipleObjectFormActionView, MultipleObjectConfirmActionView,
    SingleObjectCreateView, SingleObjectEditView, SingleObjectListView
)
from register.models import Register
from register.permissions import permission_register_view
from register.settings import statistic_access_choices

from sapitwa.utils import get_now

from .forms import (
    UserActivityForm, RegisterStatisticForm,LawyerActivityForm,
    TransferReportFilterForm, UploadReportFilterForm
)
from .tasks import (
    create_upload_report, create_transfer_report,
    create_report, create_register_files_report
)

logger = logging.getLogger(__name__)

from django.core.urlresolvers import resolve

class EventsView(SingleObjectListView):
    template_name = 'reports/events.html'

    def dispatch(self, request, *args, **kwargs):
        object_pk = kwargs.pop('object_pk',None)
        self.object = get_object_or_404(Register, pk=object_pk)
        AccessControlList.objects.check_access(
            permissions=permission_register_view, user=self.request.user,
            obj=self.object
        )
        return super(EventsView, self).dispatch(request, *args, **kwargs)

    def get_object_list(self):
        return any_stream(self.object)

    def get_extra_context(self):
        context = super(EventsView, self).get_extra_context()
        context.update({
            'hide_object': True,
            'no_results_icon': None,
            'no_results_text': _(
                'Events are actions that have been performed to this object '
                'or using this object.'
            ),
            'no_results_title': _('There are no events for this object'),
            'object': self.object,
            'title': _('Events for: %s') % self.object,
        })
        return context


class RegisterFilesReportView(SingleObjectListView):
    form_class = RegisterStatisticForm
    template_name = 'reports/register_files_report.html'
    http_method_names = ['get','post']
    filter_active = False
    title = 'Register Files Report'

    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =create_register_files_report(queryset, self.title,'', get_now(True))
                return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Register_Files_Report'}))

        self.items = self.request.POST
        return super(RegisterFilesReportView, self).dispatch(request, *args, **kwargs)

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
            'form' : self.form,
            #'date_from':context['date_from'],
            #'date_to':context['date_to'],
            #'title':context['title'],
            #'total':context['total'],
            #'user_dic': context['user_dic'],
            #'user' : False,
            'title' : 'Register Files Report',
            #'timestamp' : timezone.now(),
            'cache_key' : self.cache_key,
            'filter_active' : self.filter_active,
            'reg_dic' : self.reg_dic
        }

    def get_object_list(self):
        lawyers = None
        items = self.request.POST
        self.items = dict(items.iterlists())
        q_all = Q()
        for key, query in self.items.iteritems():
            if query:
                if key == 'status':
                    self.filter_active = False
                    q_all.add(Q(status_id__in=query),Q.AND)
                elif key == 'clients':
                    self.filter_active = False
                    q_all.add(Q(contacts__client__id__in=query),Q.AND)
                elif key == 'lawyers':
                    self.filter_active = True
                    lawyers = query
                    q_all.add(Q(lawyers__id__in=lawyers),Q.AND)
                elif key == 'departments':
                    q_all.add(Q(department__id__in=query),Q.AND)
                elif key == 'groups':
                    self.filter_active = False
                    q_all.add(Q(group__id__in=query),Q.AND)
                elif key == 'from' and query[0] != '':
                    self.filter_active = True
                    opened_from = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(opened__gte=opened_from),Q.AND)
                elif key == 'to' and query[0] != '':
                    self.filter_active = True
                    opened_to = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(opened__lte=opened_to),Q.AND)
        #queryset = Register.objects.exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(status__name='Closed')
        queryset = Register.objects.exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(group__name='Pro Bono').exclude(status__name='Closed')

        queryset = queryset.filter(q_all).distinct()


        if lawyers:
            lawyers = User.objects.filter(id__in=lawyers)
            filtered = True
        else:
            filtered = False
            ids_list = []
            for v in statistic_access_choices.value:
                v = v[0]
                user = User.objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                ids_list.append(user.pk)
            lawyers = User.objects.filter(id__in=ids_list)
        self.reg_dic = []
        for obj in lawyers:
            self.reg_dic.append([obj.get_full_name(),[
                queryset.filter(lawyers=obj).filter(status__name='Active').count(),
                queryset.filter(lawyers=obj).filter(status__name='Not active').count(),
                queryset.filter(lawyers=obj).filter(status__name='Dormant').count(),
                queryset.filter(lawyers=obj).count()]])
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,self.reg_dic)
        if filtered:
            ids_list = []
            for v in statistic_access_choices.value:
                v = v[0]
                user = User.objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first()
                ids_list.append(user.pk)
            lawyers = User.objects.filter(id__in=ids_list)
        self.form = RegisterStatisticForm(self.request.POST,
            lawyers = lawyers,
        )
        return queryset

class RegisterTransferReportView(SingleObjectListView):
    template_name = 'reports/transfer_report_list.html'
    url = ''
    query = ''
    title = "Register Files: Transfer Report"
    filter_active=False
    cache_key = None

    def dispatch(self, request, *args, **kwargs):
        self.search_query = self.request.GET.get('q',None)
        if not self.search_query:
            self.search_query = self.request.GET.get('search_query','')

        filter_query = self.request.GET.get('filter_query',None)
        if filter_query:
            self.filter_query = json.loads(filter_query)
        else:
            self.filter_query = {}
        return super(RegisterTransferReportView,self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'form' : self.form,
            'cache_key': self.cache_key,
            'hide_object' : True,
            'hide_link': True,
            #'no_results_icon': icon_register,
            # ~ 'no_results_main_link': link_register_create.resolve(
                # ~ context=RequestContext(request=self.request)
            # ~ ),
            'action_url' : 'reports:register_transfer',
            'print_url': 'reports:register_transfer',
            'filter_active':self.filter_active,
            'no_results_text': _('Nothing'),
            'no_results_title': _('No Transfers'),
            'search_query':self.search_query,
            'filter_query':json.dumps(self.filter_query),
            'title': mark_safe(self.title +'<br><span style="font-size:0.8em;">Total: '+ str(self.total)+'</span>'),
        }

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

        queryset = self.get_actions_queryset()
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
                # ~ if key == 'lawyers':
                    # ~ self.filter_active = True
                    # ~ q_all.add(Q(lawyers__id__in=query),Q.AND)
                    # ~ self.filter_query['lawyers'] = query
                if key == 'from' and query[0] != '':
                    self.filter_active = True
                    opened_from = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(timestamp__gte=opened_from),Q.AND)
                    self.filter_query['from'] = query[0]
                elif key == 'to' and query[0] != '':
                    self.filter_active = True
                    opened_to = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(timestamp__gte__lte=opened_to),Q.AND)
                    self.filter_query['to'] = query[0]
                elif 'transferred_to' in self.items and self.items['transferred_to'] != '':
                    q_or = Q()
                    for pk in self.items['transferred_to']:
                        name = User.objects.get(pk=pk).get_full_name()
                        q_or.add(Q(description__endswith=name),Q.OR)
                    q_all.add(q_or,Q.AND)

        queryset = queryset.filter(q_all).distinct()

        qs = queryset.values_list('description', flat=True).distinct()
        users = {}
        for q in qs:
            if q and len(q.split('|')) > 1:
                full_name = q.split('|')[1]
                users[User.objects.get(first_name=full_name.split(' ')[0],
                    last_name=full_name.split(' ')[1]).pk]=True

        transferred_to_lawyers = User.objects.filter(id__in=list(users))
        self.form = TransferReportFilterForm(self.request.GET,
            transferred_to_lawyers = transferred_to_lawyers,
            initials = self.filter_query
        )
        self.total = queryset.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        cache.set(self.cache_key,queryset)
        return queryset

    def get_actions_queryset(self):
        return Action.objects.filter(verb='register.file_no_transferred')
        # ~ if display_closed_files:
            # ~ return Register.objects.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files')
        # ~ else:
            # ~ return Register.objects.all().exclude(group__name='Audit Reports').exclude(group__name='General and Non-Billable Files').exclude(status__name='Closed')

class RegisterTransferReportView21(SingleObjectListView):

    http_method_names = ['get','post']
    title = 'Transfer Report'
    template_name = 'reports/transfer_report_list.html'
    cache_key = None
    url = ''
    #form = None

    def dispatch(self, request, *args, **kwargs):
        self.date_to_str = kwargs.pop('date_to',None)
        self.date_from_str = kwargs.pop('date_from', None)
        # ~ if self.date_to_str:
            # ~ self.date_to = datetime.strptime(self.date_to_str, "%d.%m.%Y").date()
        # ~ if self.date_from_str:
            # ~ self.date_from = datetime.strptime(self.date_from_str, "%d.%m.%Y").date()
        self.items = self.request.POST
        if not self.items:
            self.items = self.request.GET
        return super(RegisterTransferReportView, self).dispatch(request, *args, **kwargs)

    # ~ def get_context_data(self, **kwargs):
        # ~ try:
            # ~ return super(RegisterTransferReportView, self).get_context_data(**kwargs)
        # ~ except Exception as exception:
            # ~ messages.error(
                # ~ self.request, _(
                    # ~ 'Error retrieving transfer report: %(exception)s.'
                # ~ ) % {
                    # ~ 'exception': exception
                # ~ }
            # ~ )
            # ~ self.object_list = []
            # ~ return super(RegisterTransferReportView, self).get_context_data(**kwargs)

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

    def get_object_list(self):
        self.items = dict(self.items.iterlists())
        q_all = Q()
        for key, query in self.items.iteritems():
            if query:
                if key == 'from' and query[0] != '':
                    self.filter_active = True
                    opened_from = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(timestamp__gte=opened_from),Q.AND)
                    self.url+='&from='+query[0]
                elif key == 'to' and query[0] != '':
                    self.filter_active = True
                    opened_to = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(timestamp__lte=opened_to),Q.AND)
                    self.url+='&to='+query[0]
        self.queryset = []
        actions = Action.objects.filter(verb='register.file_no_transferred')
        actions = actions.filter(q_all).distinct()
        self.total = actions.count()
        for a in actions:
            self.queryset.append([a.timestamp,a.action_object,a.description,a.pk])
        #self.cache_key = force_text(uuid.uuid4()).replace('-','')
        #cache.set(self.cache_key,queryset)
        self.form = TransferReportFilterForm(self.request.POST,
            # ~ status_list=status,
            # ~ lawyers = lawyers,
            # ~ clients = clients,
            # ~ groups = groups,
            # ~ departments = departments,
        )
        return self.queryset

    def get_extra_context(self):
        return {
            'hide_object' : True,
            'hide_link': True,
            # ~ 'no_results_icon': icon_register,
            # ~ 'no_results_main_link': link_register_create.resolve(
                # ~ context=RequestContext(request=self.request)
            # ~ ),
            'form': self.form,
            'total': self.total,
            'no_results_text': _('Nothing'),
            'url_filter': self.url,
            'no_results_title': _('No Transfers'),
            'title': mark_safe(self.title +'<br><span style="font-size:0.8em;">Total: '+ str(self.total)+'</span>'),
            'cache_key' : self.cache_key,
        }

class RegisterTransferReportView1(SingleObjectCreateView):
    form_class = LawyerActivityForm
    template_name = 'reports/transfer_report_form.html'
    data_dict = {}
    total_dict = {}
    lawyer_full_name = None
    lawyer = None
    actions = []
    lawyers = None
    print_url = None
    date_to = None
    date_from = None

    def dispatch(self, request, *args, **kwargs):
        self.date_to_str = kwargs.pop('date_to',None)
        self.date_from_str = kwargs.pop('date_from', None)
        self.lawyer_ids_str = kwargs.pop('lawyer_ids', None)

        if self.date_to_str:
            self.date_to = datetime.strptime(self.date_to_str, "%d.%m.%Y").date()
        else:
            self.date_to = self.date_to = timezone.now().date()

        if self.date_from_str:
            self.date_from = datetime.strptime(self.date_from_str, "%d.%m.%Y").date()
        else:
            self.date_from = self.date_to - timedelta(days=6) # (days=6)#
        self.selected_lawyers = []
        initials = []
        if self.lawyer_ids_str:
            for pk in self.lawyer_ids_str.split(','):
                self.selected_lawyers.append(User.objects.get(pk=pk))
            self.data_dict = {}

            for lawyer in self.selected_lawyers:
                initials.append((lawyer.get_full_name(),lawyer.get_full_name()))

                actions = Action.objects.filter(timestamp__gte=self.date_from,timestamp__lte=self.date_to,verb='register.file_no_transferred', description__icontains=lawyer.get_full_name()).order_by('-timestamp')
                regs = {}
                for action in actions:
                    r = action.action_object
                    if r not in regs:
                        regs[r] = []
                    regs[r].append(action)
                # Need the dictionary sorted by register.opened
                # Is there a better way?
                sr = []
                for r,v in regs.items():
                    sr.append((r.opened,{r:v}))

                #now sort
                sorted_by_first = sorted(sr, key=lambda tup: tup[0], reverse=True)

                regs = []
                for d,q in sorted_by_first:
                    regs.append(q)

                self.data_dict[lawyer] = regs

            self.print_url = reverse('reports:register_transfer_print', args=(self.date_from_str,self.date_to_str,self.lawyer_ids_str))
        return super(RegisterTransferReportView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if form.is_valid():
            self.data_from = self.date_to= None
            if 'from' in form.cleaned_data:
                self.date_from = form.cleaned_data['from']
            if 'to' in form.cleaned_data:
                self.date_to = form.cleaned_data['to']
            if 'lawyers' in form.cleaned_data:
                self.lawyers = []
                for lawyer in form.cleaned_data['lawyers']:
                    self.lawyers.append(User.objects.filter(first_name=lawyer.split(' ')[0],last_name=lawyer.split(' ')[1]).first().pk)
                self.lawyers_pk = ','.join(map(str,self.lawyers))
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super(RegisterTransferReportView, self).get_form_kwargs()
        kwargs['date_from'] = self.date_from
        kwargs['date_to'] = self.date_to
        kwargs['lawyers'] = self.selected_lawyers
        return kwargs

    def get_extra_context(self):
        context = get_activity(self.date_from,self.date_to)
        return {
            'date_from':context['date_from'],
            'date_to':context['date_to'],
            'title':context['title'],
            'total':context['total'],
            #'data_dict': context['user_dic'],
            'actions': self.actions,
            'user' : self.request.user,
            'title' : 'Transfer report',
            'transfer_report' : True,
            'timestamp' : timezone.now(),
            'data_dict' : self.data_dict,
            'total_dict' : self.total_dict,
            'print_url' : self.print_url
        }


    def get_success_url(self):
        return reverse_lazy('reports:register_transfer', args = (self.date_from,self.date_to,self.lawyers_pk))


class RegisterTransferPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = "Transfer Report"
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf = create_transfer_report(queryset, title , get_now(True))
                return HttpResponseRedirect(reverse('reports:transfer_pdf', kwargs={'pdf':pdf,'title':'Transfer_Report'}))
        return HttpResponseRedirect(reverse('reports:register_transfer'))

class LawyerActivity(SingleObjectCreateView):
    form_class = LawyerActivityForm
    template_name = 'reports/register_statistic_form.html'
    reg_dic = {}
    lawyer_full_name = None
    lawyer = None

    def dispatch(self, request, *args, **kwargs):
        self.date_to = kwargs.pop('date_to',None)
        self.date_from = kwargs.pop('date_from', None)
        lawyer_pk = kwargs.pop('user_pk', None)


        if self.date_to:
            self.date_to = datetime.strptime(self.date_to, "%d.%m.%Y").date()
        else:
            self.date_to = self.date_to = timezone.now().date()

        if self.date_from:
            self.date_from = datetime.strptime(self.date_from, "%d.%m.%Y").date()
        else:
            self.date_from = self.date_to - timedelta(days=6) # (days=6)#
        if lawyer_pk:
            self.lawyer = User.objects.get(pk=lawyer_pk)
            self.lawyer_full_name = self.lawyer.get_full_name()
            #regs = Register.objects.filter(opened__gte=self.date_from,opened__lte=self.date_to, lawyers = self.lawyer)
            regs = Register.objects.filter(lawyers = self.lawyer).exclude(group='Audit Reports').exclude(group='General and Non-Billable Files').exclude(status='Closed')
            self.reg_dic['Active'] = regs.filter(status='Active')
            self.reg_dic['Not active'] = regs.filter(status='Not active')
            self.reg_dic['Dormant'] = regs.filter(status='Dormant')
            self.reg_dic['Closed'] = regs.filter(status='Closed')

        return super(LawyerActivity, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if form.is_valid():
            self.data_from = self.date_to= None
            if 'from' in form.cleaned_data:
                self.date_from = form.cleaned_data['from']
            if 'to' in form.cleaned_data:
                self.date_to = form.cleaned_data['to']
            if 'lawyer' in form.cleaned_data:
                lawyer = form.cleaned_data['lawyer']
                self.lawyer_pk = User.objects.filter(first_name=lawyer.split(' ')[0],last_name=lawyer.split(' ')[1]).first().pk

        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super(LawyerActivity, self).get_form_kwargs()
        kwargs['date_from'] = self.date_from
        kwargs['date_to'] = self.date_to
        kwargs['lawyer'] = self.lawyer
        return kwargs

    def get_extra_context(self):
        context = get_activity(self.date_from,self.date_to)
        return {
            'date_from':context['date_from'],
            'date_to':context['date_to'],
            'title':context['title'],
            'total':context['total'],
            'user_dic': context['user_dic'],
            'user' : self.request.user,
            'title' : 'Matter report',
            'lawyer_activity' : True,
            'lawyer_full_name': self.lawyer_full_name,
            'timestamp' : timezone.now(),
            'reg_dic' : self.reg_dic
        }


    def get_success_url(self):
        return reverse_lazy('reports:activity_lawyer', args = (self.date_from,self.date_to,self.lawyer_pk))

class UploadReportView(SingleObjectListView):
    template_name = 'reports/upload_report_list.html'
    title = "Upload Report"
    filter_active=False
    cache_key = None


    def dispatch(self, request, *args, **kwargs):
        self.search_query = self.request.GET.get('q',None)
        if not self.search_query:
            self.search_query = self.request.GET.get('search_query','')

        filter_query = self.request.GET.get('filter_query',None)
        if filter_query:
            self.filter_query = json.loads(filter_query)
        else:
            self.filter_query = {}
        return super(UploadReportView,self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'form' : self.form,
            'cache_key': self.cache_key,
            'hide_object' : True,
            'hide_link': True,
            'is_paginated' : False,
            'date_from' : self.date_from,
            'date_to' : self.date_to,
            #'no_results_icon': icon_register,
            # ~ 'no_results_main_link': link_register_create.resolve(
                # ~ context=RequestContext(request=self.request)
            # ~ ),
            'action_url' : 'reports:upload_report',
            'print_url': 'reports:upload_report',
            'user_dict': self.user_dict,
            'filter_active':self.filter_active,
            'no_results_text': _('Nothing'),
            'no_results_title': _('No Transfers'),
            'search_query':self.search_query,
            'filter_query':json.dumps(self.filter_query),
            'title': mark_safe(self.title
                +'<br><span style="font-size:0.8em;">Total: '
                + str(self.total)
                +'<br>Uploads between '+self.date_from+' - '+self.date_to
                +'</span>'
            ),
        }
    def get_action_objects(self, user ):
        if user.is_superuser:
            return Action.objects.filter(verb='documents.document_new_version')
        else:
            return Action.objects.filter(actor_object_id=user.pk, verb='documents.document_new_version')

    def get_object_list(self):
        self.date_from = Action.objects.filter(verb='documents.document_new_version').order_by('timestamp').first().timestamp.strftime("%d.%m.%Y")
        self.date_to = timezone.now().strftime("%d.%m.%Y")
        queryset = self.get_action_objects(self.request.user)

        self.items = dict(self.request.GET.iterlists())
        q_all = Q()
        for key, query in self.items.iteritems():
            if query:

                if key == 'from' and query[0] != '':
                    self.filter_active = True
                    opened_from = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(timestamp__gte=opened_from),Q.AND)
                    self.filter_query['from'] = query[0]
                    self.date_from = query[0]
                elif key == 'to' and query[0] != '':
                    self.filter_active = True
                    opened_to = make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(timestamp__gte__lte=opened_to),Q.AND)
                    self.filter_query['to'] = query[0]
                    self.date_to = query[0]
                elif key == 'users' and query[0] != '':
                    self.filter_active = True
                    # ~ users = User.objects.filter(pk__in=query[0]).values_list('contact', flat=True).distinct()
                    q_all.add(Q(actor_object_id__in=query),Q.AND)
                    self.filter_query['users'] = query

        queryset = queryset.filter(q_all).distinct()
        if 'users' in self.filter_query:
            users = User.objects.filter(pk__in= self.filter_query['users'])
        else:
            users = User.objects.filter(is_active=True).exclude(username='admin').order_by('first_name')
        self.user_dict = []
        self.total = 0
        if self.request.user.is_superuser:
            for user in users:
                aU = queryset.filter(actor_object_id=user.pk)
                self.user_dict.append([user,aU.count()])
                self.total += aU.count()
        else:
                aU = queryset.filter(actor_object_id=self.request.user.pk)
                self.user_dict.append([self.request.user,aU.count()])
                self.total += aU.count()
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        subtitle = 'Upload period: '+self.date_from +' - '+self.date_to
        cache.set(self.cache_key,(self.user_dict,subtitle))

        self.form = UploadReportFilterForm(self.request.GET,
            user = self.request.user,
            users = users,
            initials = self.filter_query
        )
        return self.user_dict

class UploadReportPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = "Upload Report"
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf = create_upload_report(queryset, title , get_now(True))
                return HttpResponseRedirect(reverse('reports:transfer_pdf', kwargs={'pdf':pdf,'title':'Upload_Report'}))
        return HttpResponseRedirect(reverse('reports:upload_report'))


class ActivityView(SingleObjectCreateView):
    form_class = UserActivityForm
    template_name = 'reports/user_activity_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.date_to = kwargs.pop('date_to',None)
        self.date_from = kwargs.pop('date_from', None)

        if self.date_to:
            self.date_to = datetime.strptime(self.date_to, "%d.%m.%Y").date()
        else:
            self.date_to = self.date_to = timezone.now().date()

        if self.date_from:
            self.date_from = datetime.strptime(self.date_from, "%d.%m.%Y").date()
        else:
            self.date_from = self.date_to - timedelta(days=6) # (days=6)#

        return super(ActivityView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if 'from' in form.cleaned_data:
            self.date_from = form.cleaned_data['from']
        if 'to' in form.cleaned_data:
            self.date_to = form.cleaned_data['to']
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super(ActivityView, self).get_form_kwargs()
        kwargs['date_from'] = self.date_from
        kwargs['date_to'] = self.date_to
        return kwargs

    def get_extra_context(self):
        context = get_activity(self.date_from,self.date_to)
        return {
            'date_from':context['date_from'],
            'date_to':context['date_to'],
            'title':context['title'],
            'total':context['total'],
            'user_dic': context['user_dic'],
            'user' : False,
            'timestamp' : timezone.now()
        }

    def get_success_url(self):
        return reverse_lazy('reports:activity', args = (self.date_from,self.date_to))

class UserActivityView(SingleObjectCreateView):
    form_class = UserActivityForm
    template_name = 'reports/user_activity_form.html'

    def dispatch(self, request, *args, **kwargs):
        user_pk = kwargs.pop('user_pk',None)
        if user_pk:
            self.user = User.objects.get(pk = user_pk)
        else:
            self.user = self.request.user
        self.date_to = kwargs.pop('date_to',None)
        self.date_from = kwargs.pop('date_from', None)
        if self.date_to:
            self.date_to = datetime.strptime(self.date_to, "%d.%m.%Y").date()
        else:
            self.date_to = self.date_to = timezone.now().date()

        if self.date_from:
            self.date_from = datetime.strptime(self.date_from, "%d.%m.%Y").date()
        else:
            self.date_from = self.date_to - timedelta(days=6) # (days=6)#


        return super(UserActivityView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if 'from' in form.cleaned_data:
            self.date_from = form.cleaned_data['from']
        if 'to' in form.cleaned_data:
            self.date_to = form.cleaned_data['to']
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super(UserActivityView, self).get_form_kwargs()
        kwargs['date_from'] = self.date_from
        kwargs['date_to'] = self.date_to
        return kwargs

    def get_extra_context(self):
        context = get_user_activity(self.date_from,self.date_to,self.user.pk)
        return {
            'date_from':context['date_from'],
            'date_to':context['date_to'],
            'title':context['title'],
            'total':context['total'],
            'register': context['register'],
            'quotations_dic': context['quotations_dic'],
            'unattached': context['unattached'],
            'user' : True,
            'timestamp' : timezone.now()
        }


    def get_success_url(self):
        return reverse_lazy('reports:user_activity', args = (self.date_from,self.date_to,self.user.pk))

import operator
def get_activity(date_from,date_to):

    users = User.objects.all().order_by('first_name')
    user_dic = []
    total = 0
    for user in users:
        if user.get_full_name() and user.is_active:
            aU = Action.objects.filter(timestamp__gte=date_from,timestamp__lte=date_to, actor_object_id=user.pk, verb='documents.document_new_version')
            user_dic.append([user,aU.count()])
            total += aU.count()
    title = 'Upload report'
    context = {'date_from':date_from, 'date_to':date_to,'title':title,'total':total, 'user_dic': user_dic}
    return context

from django.db.models import Count
from django.contrib.contenttypes.models import ContentType
from documents.models import Document

def get_user_activity(date_from,date_to,user_pk):

    start= timezone.now()
    aU = Action.objects.filter(timestamp__gte=date_from,timestamp__lte=date_to,actor_object_id=user_pk, verb='documents.document_new_version')
    register_dic = {}
    quotations_dic = {}
    unattached = []
    user = User.objects.filter(pk=user_pk)
    context = {}

    ct = ContentType.objects.get_for_model(Document)
    ids = aU.values_list("action_object_object_id", flat=True).filter(action_object_content_type=ct)
    docs = Document.objects.filter(pk__in=list(ids))
    reg = docs.filter(register__isnull=False)
    quot = docs.filter(quotation__isnull=False)
    unattached = docs.exclude(quotation__isnull=False).exclude(register__isnull=False)

    result = reg.values('register__file_no').distinct()
    for r in result:
        register = Register.objects.get(file_no = r['register__file_no'])
        register_dic[register] = reg.filter(register__file_no=r['register__file_no'])
    result = quot.values('quotation__file_no').distinct()
    for r in result:
        quotations_dic[r['quotation__file_no']] = quot.filter(register__file_no=r['quotation__file_no'])

    title = 'Upload report for '+user[0].get_full_name()
    context = {'date_from':date_from, 'date_to':date_to,'title':title,'total':aU.count(), 'register': register_dic, 'quotations_dic': quotations_dic, 'unattached': unattached }
    end =  timezone.now()
    return context

from django.http import FileResponse
def transfer_pdf(response,pdf,title):
    pdf = open('/tmp/'+pdf, 'rb')
    response = FileResponse(pdf)
    title = title.replace('_',' ')
    title += ".pdf"
    response['Content-Disposition'] = "attachment; filename=\""+title+"\""
    return response
