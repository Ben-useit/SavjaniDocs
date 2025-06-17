import uuid
from datetime import datetime
from exceptions import Exception
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ungettext

from acls.models import AccessControlList
from common.generics import ConfirmView
from common.views import (
    SingleObjectCreateView, SingleObjectListView, SingleObjectEditView,
    SingleObjectDeleteView
)
from clients.models import Client
from register.models import Register, Status
from register.permissions import permission_register_view
from .forms import (
    TrackedFileForm, ClosureLetterEditForm, InstructionsEditForm,
    ClientEditForm, NoticeEditForm, ReceiptEditForm, CompletionEditForm,
    TrackingFilterForm
)
from .models import TrackedFile
from .tasks import print_tracking_chart

class TrackingListPrintView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        cache_key = kwargs.pop('key',None)
        title = 'Active File Tracking Chart'
        if cache_key:
            queryset = cache.get(cache_key)
            if queryset:
                pdf =print_tracking_chart(queryset)
                return HttpResponseRedirect(reverse_lazy('register:report_pdf', kwargs={'pdf':pdf,'title':'Active_File_Tracking_Chart'}))
        return HttpResponseRedirect(reverse_lazy('tracking:tracking_list', kwargs={'key':cache_key}))


class TrackingListView(SingleObjectListView):
    template_name = 'tracking/tracking_list.html'
    filter_active=False
    cache_key = None
    title = 'Tracked register files'
    qs = None

    def dispatch(self,request,*args,**kwargs):
        self.cache_key = kwargs.pop('key',None)
        if not self.cache_key:
            self.cache_key = force_text(uuid.uuid4()).replace('-','')
        self.qs = cache.get(self.cache_key)
        filter_query = self.request.GET.get('filter_query',None)
        if filter_query:
            self.filter_query = json.loads(filter_query)
        else:
            self.filter_query = {}
        return super(TrackingListView,self).dispatch(request,*args,**kwargs)

    def get_extra_context(self):
        return {
            'form' : self.form,
            'link_classes' : None,
            'cache_key': self.cache_key,
            'hide_object' : True,
            'hide_link': False,
            #'no_actions' : True,
            'action_url' :'tracking:tracking_list',
            'print_url': 'tracking:tracking_list_print',
            'print_csv': 'tracking:tracking_list_csv',
            'filter_active':self.filter_active,
            # ~ 'search_query':self.search_query,
            # ~ 'filter_query':json.dumps(self.filter_query),
            'display_group': True,
            'title': mark_safe(self.title +'<br><span style="font-size:0.8em;">Total: '+ str(self.total)+'</span>'),
        }

    def get_object_list(self):

        if self.qs:
            queryset = self.qs
        else:
            queryset = TrackedFile.objects.all()
        queryset = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=queryset)

        # Process filter entries
        # current entries
        self.items = dict(self.request.GET.iterlists())
        q_all = Q()
        cb_closure = False
        cb_instruction = False
        cb_notice = False
        cb_acknowledgement = False
        cb_completion = False
        for key, query in self.items.iteritems():
            # ~ if query:
                if key == 'retain_or_transfer' and query[0] != '':
                    self.filter_active = True
                    q_all.add(Q(retain_or_transfer=query[0]),Q.AND)
                    self.filter_query['retain_or_transfer'] = query[0]
                elif key == 'clients':
                    self.filter_active = True
                    q_all.add(Q(file__clients__id__in=query),Q.AND)
                    self.filter_query['clients'] = query
                elif key == 'ex_lawyers':
                    self.filter_active = True
                    q_all.add(Q(client__id__in=query),Q.AND)
                    self.filter_query['ex_lawyers'] = query
                elif key == 'lawyers':
                    self.filter_active = True
                    q_all.add(Q(file__lawyers__id__in=query),Q.AND)
                    self.filter_query['lawyers'] = query
                elif key == 'from' and query[0] != '':
                    self.filter_active = True
                    opened_from = datetime.strptime(query[0], "%d.%m.%Y").date() #make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(file__opened__gte=opened_from),Q.AND)
                    self.filter_query['from'] = query[0]
                if key == 'to' and query[0] != '':
                    self.filter_active = True
                    opened_to = datetime.strptime(query[0], "%d.%m.%Y").date()#make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                    q_all.add(Q(file__opened__lte=opened_to),Q.AND)
                    self.filter_query['to'] = query[0]
                if key == 'cb_closure':
                    cb_closure = True
                else:
                    if key == 'closure_from' and query[0] != '':
                        self.filter_active = True
                        opened_from = datetime.strptime(query[0], "%d.%m.%Y").date() #make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(closure_letter__gte=opened_from),Q.AND)
                        self.filter_query['closure_from'] = query[0]
                    if key == 'closure_to' and query[0] != '':
                        self.filter_active = True
                        opened_to = datetime.strptime(query[0], "%d.%m.%Y").date()#make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(closure_letter__lte=opened_to),Q.AND)
                        self.filter_query['closure_to'] = query[0]
                if key == 'cb_instruction':
                    cb_instruction = True
                else:
                    if key == 'instructions_from' and query[0] != '':
                        self.filter_active = True
                        opened_from = datetime.strptime(query[0], "%d.%m.%Y").date() #make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(instructions__gte=opened_from),Q.AND)
                        self.filter_query['instructions_from'] = query[0]
                    if key == 'instructions_to' and query[0] != '':
                        self.filter_active = True
                        opened_to = datetime.strptime(query[0], "%d.%m.%Y").date()#make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(instructions__lte=opened_to),Q.AND)
                        self.filter_query['instructions_to'] = query[0]
                if key == 'cb_notice':
                    cb_notice = True
                else:
                    if key == 'notice_from' and query[0] != '':
                        self.filter_active = True
                        opened_from = datetime.strptime(query[0], "%d.%m.%Y").date() #make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(notice__gte=opened_from),Q.AND)
                        self.filter_query['notice_from'] = query[0]
                    if key == 'notice_to' and query[0] != '':
                        self.filter_active = True
                        opened_to = datetime.strptime(query[0], "%d.%m.%Y").date()#make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(notice__lte=opened_to),Q.AND)
                        self.filter_query['notice_to'] = query[0]
                if key == 'cb_acknowledgement':
                    cb_acknowledgement = True
                else:
                    if key == 'receipt_from' and query[0] != '':
                        self.filter_active = True
                        opened_from = datetime.strptime(query[0], "%d.%m.%Y").date() #make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(receipt__gte=opened_from),Q.AND)
                        self.filter_query['receipt_from'] = query[0]
                    if key == 'receipt_to' and query[0] != '':
                        self.filter_active = True
                        opened_to = datetime.strptime(query[0], "%d.%m.%Y").date()#make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(receipt__lte=opened_to),Q.AND)
                        self.filter_query['receipt_to'] = query[0]
                if key == 'cb_completion':
                    cb_completion = True
                else:
                    if key == 'completion_from' and query[0] != '':
                        self.filter_active = True
                        opened_from = datetime.strptime(query[0], "%d.%m.%Y").date() #make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(completion__gte=opened_from),Q.AND)
                        self.filter_query['completion_from'] = query[0]
                    if key == 'completion_to' and query[0] != '':
                        self.filter_active = True
                        opened_to = datetime.strptime(query[0], "%d.%m.%Y").date()#make_aware(datetime.strptime(query[0], "%d.%m.%Y")).date()
                        q_all.add(Q(completion__lte=opened_to),Q.AND)
                        self.filter_query['completion_to'] = query[0]
        queryset = queryset.filter(q_all).distinct()
        # additional filter:
        if cb_closure:
            queryset = queryset.filter(closure_letter=None)
        if cb_instruction:
            queryset = queryset.filter(instructions=None)
        if cb_notice:
            queryset = queryset.filter(notice=None)
        if cb_acknowledgement:
            queryset = queryset.filter(receipt=None)
        if cb_completion:
            queryset = queryset.filter(completion=None)
        lawyers_list = queryset.values_list('file__lawyers', flat=True).distinct()
        lawyers = User.objects.filter(id__in=lawyers_list)

        clients_list = queryset.values_list('file__clients', flat=True).distinct()
        clients = Client.objects.filter(id__in=clients_list)

        ex_lawyers_list = queryset.values_list('client', flat=True).distinct()
        ex_lawyers = Client.objects.filter(id__in=ex_lawyers_list)

        self.form = TrackingFilterForm(self.request.POST,
            lawyers = lawyers,
            clients = clients,
            ex_lawyers = ex_lawyers,
            initials = self.filter_query
        )
        self.total = queryset.count()
        cache.set(self.cache_key,queryset)
        return queryset


class StartTrackingManyView(SingleObjectCreateView):
    extra_context = {'title': 'Start Tracking'}
    model = TrackedFile
    form_class = TrackedFileForm

    def dispatch(self, request, *args, **kwargs):
        self.id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        try:
            self.regs = Register.objects.filter(pk__in=self.id_list.split(','))
        except Exception as e:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        self.cache_key = force_text(uuid.uuid4()).replace('-','')
        self.post_action_redirect = reverse_lazy('tracking:tracking_list', kwargs={'key': self.cache_key })
        for r in self.regs:
             if r.trackedfile_set.all():
                messages.error(
                    self.request, 'Please select only files that are not tracked already.'
                )
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        return super(StartTrackingManyView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(StartTrackingManyView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            for reg in self.regs:
                obj = TrackedFile()
                if form.cleaned_data['retain_or_transfer']:
                    obj.retain_or_transfer = form.cleaned_data['retain_or_transfer']
                if form.cleaned_data['closure_letter'] and form.cleaned_data['closure_letter'] != '':
                    obj.closure_letter = datetime.strptime(form.cleaned_data['closure_letter'], "%d.%m.%Y").date()
                if form.cleaned_data['instructions'] and form.cleaned_data['instructions'] != '':
                    obj.instructions = datetime.strptime(form.cleaned_data['instructions'], "%d.%m.%Y").date()
                if form.cleaned_data['notice'] and form.cleaned_data['notice'] != '':
                    obj.notice = datetime.strptime(form.cleaned_data['notice'], "%d.%m.%Y").date()
                if form.cleaned_data['receipt'] and form.cleaned_data['receipt'] != '':
                    obj.receipt = datetime.strptime(form.cleaned_data['receipt'], "%d.%m.%Y").date()
                if form.cleaned_data['completion'] and form.cleaned_data['completion'] != '':
                    obj.completion = datetime.strptime(form.cleaned_data['completion'], "%d.%m.%Y").date()
                if form.cleaned_data['client']:
                    obj.client = form.cleaned_data['client'].first()
                obj.file = reg
                reg.status = Status.objects.get(name="Transferred out")
                reg.save()
                obj.save()
        cache.set(self.cache_key,TrackedFile.objects.filter(file__in=self.regs))
        return HttpResponseRedirect(self.post_action_redirect)

class TrackingEditView(SingleObjectCreateView):
    model = TrackedFile
    form_class = TrackedFileForm

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.pop('pk',None)
        if pk:
            self.obj = get_object_or_404(TrackedFile, pk=self.kwargs['pk'])
            self.extra_context = {'title': 'Edit Tracking Chart for file: '+ self.obj.file.file_no }
        self.post_action_redirect = reverse_lazy('tracking:tracking_list')
        return super(TrackingEditView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(TrackingEditView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['obj'] = self.obj
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            if form.cleaned_data['retain_or_transfer']:
                self.obj.retain_or_transfer = form.cleaned_data['retain_or_transfer']
            if form.cleaned_data['closure_letter'] and form.cleaned_data['closure_letter'] != '':
                self.obj.closure_letter = datetime.strptime(form.cleaned_data['closure_letter'], "%d.%m.%Y").date()
            if form.cleaned_data['instructions'] and form.cleaned_data['instructions'] != '':
                self.obj.instructions = datetime.strptime(form.cleaned_data['instructions'], "%d.%m.%Y").date()
            if form.cleaned_data['notice'] and form.cleaned_data['notice'] != '':
                self.obj.notice = datetime.strptime(form.cleaned_data['notice'], "%d.%m.%Y").date()
            if form.cleaned_data['receipt'] and form.cleaned_data['receipt'] != '':
                self.obj.receipt = datetime.strptime(form.cleaned_data['receipt'], "%d.%m.%Y").date()
            if form.cleaned_data['completion'] and form.cleaned_data['completion'] != '':
                self.obj.completion = datetime.strptime(form.cleaned_data['completion'], "%d.%m.%Y").date()
            if form.cleaned_data['client']:
                self.obj.client = form.cleaned_data['client'].first()
            self.obj.save()
        return HttpResponseRedirect(self.post_action_redirect)

class TrackingDeleteView(SingleObjectDeleteView):
    model = TrackedFile
    object_permission = permission_register_view
    post_action_redirect = reverse_lazy('tracking:tracking_list')

    # ~ def get_extra_context(self):
        # ~ return {
            # ~ 'delete_view': True,
            # ~ 'object': self.get_object(),
            
        # ~ }

    def get_extra_context(self):
        return {
            'message': None,
            'object': self.get_object(),
            'title': _('Remove file from tracked list: %s?') % self.get_object(),
        }

class TrackingDetailView(TrackingEditView):

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.pop('pk',None)
        if pk:
            obj = get_object_or_404(Register, pk=self.kwargs['pk'])
            self.obj = obj.trackedfile_set.first()
            self.extra_context = {'title': 'Edit Tracking Chart for file: '+ obj.file_no }
        self.post_action_redirect = reverse_lazy('register:register_list')
        return super(TrackingDetailView, self).dispatch(request, *args, **kwargs)

class TrackingEditManyView(SingleObjectCreateView):

    extra_context = {'title': 'Edit'}
    #fields = ('retain_or_transfer',)
    model = TrackedFile
    #form_class = TrackedFileForm

    def dispatch(self, request, *args, **kwargs):
        self.id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        try:
            self.files = TrackedFile.objects.filter(pk__in=self.id_list.split(','))
        except Exception as e:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        self.post_action_redirect = reverse_lazy('tracking:tracking_list', kwargs={'id_list': self.id_list.replace(',','_') })
        return super(TrackingEditManyView, self).dispatch(request, *args, **kwargs)

class RetainOrTransferEditManyView(TrackingEditManyView):
    fields = ('retain_or_transfer',)
    model = TrackedFile

    def form_valid(self, form):
        if form.is_valid():
            for file in self.files:
                file.retain_or_transfer = form.cleaned_data['retain_or_transfer']
                file.save()
        return HttpResponseRedirect(self.post_action_redirect)

class ClosureLetterEditManyView(TrackingEditManyView):
    form_class = ClosureLetterEditForm

    def form_valid(self, form):
        if form.is_valid():
            for file in self.files:
                file.closure_letter = datetime.strptime(form.cleaned_data['closure_letter'], "%d.%m.%Y").date()
                file.save()
        return HttpResponseRedirect(self.post_action_redirect)

class InstructionsEditManyView(TrackingEditManyView):
    form_class = InstructionsEditForm

    def form_valid(self, form):
        if form.is_valid():
            for file in self.files:
                file.instructions = datetime.strptime(form.cleaned_data['instructions'], "%d.%m.%Y").date()
                file.save()
        return HttpResponseRedirect(self.post_action_redirect)

class ClientEditManyView(TrackingEditManyView):
    form_class = ClientEditForm

    def form_valid(self, form):
        if form.is_valid():
            for file in self.files:
                file.client = form.cleaned_data['client'].first()
                file.save()
        return HttpResponseRedirect(self.post_action_redirect)

class NoticeEditManyView(TrackingEditManyView):
    form_class = NoticeEditForm

    def form_valid(self, form):
        if form.is_valid():
            for file in self.files:
                file.notice = datetime.strptime(form.cleaned_data['notice'], "%d.%m.%Y").date()
                file.save()
        return HttpResponseRedirect(self.post_action_redirect)

class ReceiptEditManyView(TrackingEditManyView):
    form_class = ReceiptEditForm

    def form_valid(self, form):
        if form.is_valid():
            for file in self.files:
                file.receipt = datetime.strptime(form.cleaned_data['receipt'], "%d.%m.%Y").date()
                file.save()
        return HttpResponseRedirect(self.post_action_redirect)

class CompletionEditManyView(SingleObjectCreateView):
    form_class = CompletionEditForm
    def form_valid(self, form):
        if form.is_valid():
            for file in self.files:
                file.completion = datetime.strptime(form.cleaned_data['completion'], "%d.%m.%Y").date()
                file.save()
        return HttpResponseRedirect(self.post_action_redirect)

class StopTrackingManyView(ConfirmView):
    success_message = 'Selected file is not longer tracked.'
    success_message_plural = 'Selected files are not longer tracked.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'register:register_list'
    )
    id_list = 'None'
    title = _('Stop tracking selected files?')

    def dispatch(self, request, *args, **kwargs):
        # ~ try:
            # ~ self.permission_register_view = Permission.check_permissions(self.request.user,permission_register_view)
            # ~ self.title = _('Stop tracking selected files?')
            # ~ self.message_success = _('Selected files are not longer tracked.')
        # ~ except PermissionDenied:
            # ~ self.permission_register_create = False
            # ~ self.title = _('Send request to close selected files?')
            # ~ self.message_success = _('Sent request to close all selected files.')
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        self.post_action_redirect = reverse_lazy('tracking:tracking_list')
        return super(StopTrackingManyView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': self.title,
            'next' : self.post_action_redirect
        }

    def view_action(self):
        self.id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )

        tfs = TrackedFile.objects.filter(pk__in=self.id_list.split(','))

        for tf in tfs:
            tfs.delete()
