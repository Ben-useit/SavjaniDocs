from __future__ import absolute_import, unicode_literals

import logging
from datetime import datetime, timedelta
from actstream.models import Action, any_stream

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

from .forms import UserActivityForm, RegisterStatisticForm,LawyerActivityForm
from .tasks import create_report

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


class RegisterStatisticView(SingleObjectCreateView):
    form_class = RegisterStatisticForm
    template_name = 'reports/register_statistic_form.html'
    reg_dic = {}


    def dispatch(self, request, *args, **kwargs):
        self.date_to = kwargs.pop('date_to',None)
        self.date_from = kwargs.pop('date_from', None)
        self.lawyer_ids = kwargs.pop('lawyer_ids', None)

        if self.date_to:
            self.date_to = datetime.strptime(self.date_to, "%d.%m.%Y").date()
        else:
            self.date_to = self.date_to = timezone.now().date()

        if self.date_from:
            self.date_from = datetime.strptime(self.date_from, "%d.%m.%Y").date()
        else:
            self.date_from = self.date_to - timedelta(days=6) # (days=6)#

        regs = Register.objects.filter(opened__gte=self.date_from,opened__lte=self.date_to)

        lawyers = []
        self.reg_dic = []
        if self.lawyer_ids:
            for pk in self.lawyer_ids.split(','):
                lawyers.append(User.objects.get(pk=pk))
        else:
            for v in statistic_access_choices.value:
                v = v[0]
                lawyers.append(User.objects.filter(first_name=v.split(' ')[0],last_name=v.split(' ')[1]).first())

        for obj in lawyers:
            self.reg_dic.append([obj.get_full_name(),[
                regs.filter(lawyers=obj).filter(status='Active').count(),
                regs.filter(lawyers=obj).filter(status='Not active').count(),
                regs.filter(lawyers=obj).filter(status='Dormant').count(),
                regs.filter(lawyers=obj).filter(status='Closed').count(),
                regs.filter(lawyers=obj).count()]])

        return super(RegisterStatisticView, self).dispatch(request, *args, **kwargs)

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
                self.lawyers = ','.join(map(str,self.lawyers))

        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super(RegisterStatisticView, self).get_form_kwargs()
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
            'title' : 'Matter report',
            'timestamp' : timezone.now(),
            'reg_dic' : self.reg_dic
        }


    def get_success_url(self):
        return reverse_lazy('reports:register_statistics', args = (self.date_from,self.date_to,self.lawyers))


class RegisterTransferReportView(SingleObjectCreateView):
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


class RegisterTransferPrintReportView(RegisterTransferReportView):

    def dispatch(self, request, *args, **kwargs):
        super(RegisterTransferPrintReportView, self).dispatch(request, *args, **kwargs)
        period = self.date_from.strftime('%d. %b %Y')+' - '+self.date_to.strftime('%d. %b %Y')
        pdf =create_report(self.data_dict, self.total_dict, 'Report: Transfers', period, get_now(True),user=self.request.user)
        return HttpResponseRedirect(reverse('register:report_pdf', kwargs={'pdf':pdf,'title':'Report_Transfers'}))

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
            regs = Register.objects.filter(lawyers = self.lawyer)

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
