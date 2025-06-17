from __future__ import absolute_import, unicode_literals

import logging
import time
import datetime

from django.http import Http404
from django.views.generic import (
    DetailView, ListView
)
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _, ungettext
from django.views.generic.edit import CreateView
from django.views.generic import TemplateView
from django.template import RequestContext
from acls.models import AccessControlList
from common.forms import ChoiceForm
from common.icons import icon_assign_remove_add, icon_assign_remove_remove
from common.generics import ConfirmView, SimpleView, CreateView
from common.views import (
    SingleObjectCreateView, SingleObjectListView, SingleObjectEditView
)

from register.models import Register
from register.permissions import permission_register_create

from sapitwa.utils import get_now

from .forms import ChecklistSelectForm, ChecklistForm
from .models import Checklist, RegisterChecklist, RegisterChecklist, TemplateEntry, RegisterTemplateEntry
from .tasks import create_report, send_checklist_delete_request_mail, create_status_report

class ChecklistPdf(SimpleView):

    def dispatch(self, request, *args, **kwargs):
        register = get_object_or_404(Register,pk = kwargs.pop('pk', None))
        queryset = register.matter.all().order_by('template_entry__number')
        pdf =create_report(register, get_now(True))
        title = register.file_no.replace('/','_')+' + '+register.parties+' ['+timezone.now().strftime("%d.%m.%Y")+'].pdf'
        return HttpResponseRedirect(reverse('checklist:checklist_pdf', kwargs={'pdf':pdf,'title':title}))

class StatusPdf(SimpleView):

    def dispatch(self, request, *args, **kwargs):
        register = get_object_or_404(Register,pk = kwargs.pop('pk', None))
        self.register_template_entry = RegisterTemplateEntry.objects.filter(register=register)
        data = {}
        data['client'] = self.get_entry('3. Client Name:').encode('Windows-1252')
        data['contact'] = self.get_entry('a. Name and position of contact person at client:').encode('Windows-1252')
        data['email'] = self.get_entry('b. E-mail address:').encode('Windows-1252')
        data['phone'] = self.get_entry('c. Telephone Number:').encode('Windows-1252')
        data['description'] = self.get_entry('6. Description of matter').encode('Windows-1252')
        data['stage_reached'] = self.get_entry('7. Stage reached:').encode('Windows-1252')
        data['time_to_complete'] = self.get_entry('8. Estimated time for completion:').encode('Windows-1252')
        data['costs'] = self.get_entry('9. Estimated Fixed/Capped Costs:').encode('Windows-1252')
        data['stamping'] = self.get_entry('*(i) Stamping?').encode('Windows-1252')
        data['consent'] = self.get_entry('13. Consents/certificate required?').encode('Windows-1252')
        data['document_return'] = self.get_entry('14. Do any documents need to be returned/sent to client or any party?').encode('Windows-1252')
        data['remarks'] = self.get_entry('17. Remarks:').encode('Windows-1252')
        pdf = create_status_report(register,data, get_now(date_only=True,long_date=True))
        title = 'Status Report '+ register.file_no.replace('/','_')+' + '+register.parties+' ['+timezone.now().strftime("%d.%m.%Y")+'].pdf'
        return HttpResponseRedirect(reverse('checklist:checklist_pdf', kwargs={'pdf':pdf,'title':title}))

    def get_entry(self, name):
        entry = ''
        try:
            if self.register_template_entry.filter(template_entry__label=name ).first():
                entry = self.register_template_entry.filter(template_entry__label=name).first().value
        except:
            pass
        return entry

class ChecklistView(CreateView):
    form_class= ChecklistForm
    template_name = 'checklist/checklist_view.html'

    def dispatch(self,request,*args,**kwargs):
        self.register = get_object_or_404(Register,pk = kwargs.pop('pk', None))
        register_checklist = RegisterChecklist.objects.filter(register=self.register).first()
        if register_checklist:
            self.checklist = register_checklist.checklist
        else:
            raise Http404('Register file has no checklist')
        return super(ChecklistView,self).dispatch(request=request,*args,**kwargs)

    def get_context_data(self, **kwargs):
        context = super(ChecklistView,self).get_context_data(**kwargs)
        context['register'] = self.register
        context['queryset'] = self.queryset
        context['title'] = self.checklist.name
        return context

    def get_queryset(self):
        self.queryset = self.checklist.checklist.all()
        return self.queryset

    def get_form_kwargs(self):
        kwargs = super(ChecklistView, self).get_form_kwargs()
        kwargs['template_entries'] = self.checklist.templateentry_set.all().order_by('number')
        kwargs['register'] = self.register
        return kwargs

    def form_valid(self,form):
        for k,v in form.cleaned_data.items():
            template_entry = TemplateEntry.objects.filter(pk=k).first()
            if template_entry:
                obj,c = RegisterTemplateEntry.objects.get_or_create(register=self.register,template_entry=template_entry)
                obj.value = v
                obj.save()
        return HttpResponseRedirect('/checklist/'+str(self.register.pk)+'/view/')

def selectChecklist(request,pk):
    form = ChecklistSelectForm()
    title = "Select checklist"
    register = get_object_or_404(Register,pk=pk)
    if request.method == 'POST':
        form = ChecklistSelectForm(request.POST)
        if form.is_valid():
            checklist = form.cleaned_data['checklist']
            obj = RegisterChecklist(register=register,checklist= checklist)
            obj.save()
            return HttpResponseRedirect(reverse_lazy('checklist:view', kwargs={'pk': register.pk}))
    else:
        form = ChecklistSelectForm()
    return render(request, 'appearance/generic_form.html', {'form': form, 'title': title})


class ChecklistDeleteView(ConfirmView):

    success_message = 'Checklist deleted.'
    success_message_plural = success_message
    def get_extra_context(self):
        return {
            'title': _('Delete checklist?')
        }

    def get_object(self):
        return get_object_or_404(Register, pk=self.kwargs['pk'])

    def get_post_action_redirect(self):
        return reverse('register:register_list')

    def view_action(self):
        ee = RegisterTemplateEntry.objects.filter(register=self.get_object()).exclude(value='')
        if ee.count() > 1:
            if not permission_register_create.stored_permission.requester_has_this(self.request.user):
                messages.success( self.request, _("Request to delete sent"))
                send_checklist_delete_request_mail(self.request.user,self.get_object())
                return
            else:
                cl = get_object_or_404(RegisterChecklist,register=self.get_object())
                cl.delete()
                rte = RegisterTemplateEntry.objects.filter(register=self.get_object())
                for e in rte:
                    e.delete()
        else:
            cl = get_object_or_404(RegisterChecklist,register=self.get_object())
            cl.delete()
            rte = RegisterTemplateEntry.objects.filter(register=self.get_object())
            for e in rte:
                e.delete()

        messages.success(
            self.request, _(self.success_message)
        )

class ChecklistListView(SingleObjectListView):
    model = Checklist

    def dispatch(self, request, *args, **kwargs):
        object_pk = kwargs.pop('pk',None)
        register = get_object_or_404(Register,pk=object_pk)
        checklist = RegisterChecklist.objects.filter(register=register).first()
        if not checklist:
            return HttpResponseRedirect(reverse_lazy('checklist:select', kwargs={'pk': object_pk }))
        return HttpResponseRedirect(reverse_lazy('checklist:view', kwargs={'pk': object_pk}))

        return super(ChecklistListView,self).dispatch(request,*args,**kwargs)

from django.http import FileResponse
def open_pdf(response,pdf,title):
    pdf = open('/tmp/'+pdf, 'rb')
    response = FileResponse(pdf)
    response['Content-Disposition'] = "attachment; filename=\""+title+"\""
    return response
