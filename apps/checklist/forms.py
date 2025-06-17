from __future__ import absolute_import, unicode_literals

import logging

from django import forms
from django.forms import DateTimeInput
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from acls.models import AccessControlList
from common.utils import get_str_from_aware
from metadata.widgets import ListTextWidget
from permissions.models import Role

from .models import Checklist, RegisterTemplateEntry

class ChecklistSelectForm(forms.Form):
    checklist = forms.ModelChoiceField(queryset=Checklist.objects.filter(pk__gt=4),empty_label=None)

class XDSoftDateTimePickerInput(DateTimeInput):
    template_name = 'checklist/xdsoft_datetimepicker.html'

class XDSoftDateTimePickerInput2(DateTimeInput):
    template_name = 'checklist/xdsoft_datetimepicker2.html'

class ChecklistForm(forms.Form):


    def __init__(self, *args, **kwargs):
        template_entries = kwargs.pop('template_entries', None)
        register = kwargs.pop('register', None)
        instance = kwargs.pop('instance', None)
        hint = False
        super(ChecklistForm,self).__init__(*args,**kwargs)
        for entry in template_entries:
            label = entry.symbol+ ' '+ entry.label
            if entry.label.startswith('**'):
                hint = True
            mte = RegisterTemplateEntry.objects.filter(register=register,template_entry=entry).first()
            if entry.entry_type == entry.TEXT:
                self.fields[str(entry.id)] = forms.CharField(label=label,required=False,help_text=entry.help_text)
                self.fields[str(entry.id)].widget.attrs.update({'class': "form-control" , 'style': 'height:30px;' })
            elif entry.entry_type == entry.TEXTAREA:
                self.fields[str(entry.id)] = forms.CharField(label=label,required=False,help_text=entry.help_text)
                self.fields[str(entry.id)].widget=forms.Textarea(attrs={'cols': '60', 'rows': '3' })
                self.fields[str(entry.id)].widget.attrs.update({'textarea': True })
                self.fields[str(entry.id)].widget.attrs.update({'class': "form-control" })
            elif entry.entry_type == entry.DATE:
                self.fields[str(entry.id)] = forms.CharField(label=label,required=False, help_text=entry.help_text)
                self.fields[str(entry.id)].input_formats='%d.%m.%Y',
                self.fields[str(entry.id)].widget = XDSoftDateTimePickerInput()
                self.fields[str(entry.id)].widget.attrs.update({'class': "form-control",'style':'width:100px; height:30px;' })

            elif entry.entry_type == entry.YESNO:
                self.fields[str(entry.id)] = forms.ChoiceField(choices=(('', ''),('yes', 'Yes'),('no', 'No')), label=label, required=False, help_text=entry.help_text)
                self.fields[str(entry.id)].widget.attrs.update({'class': "form-control" , 'style':'width:60px; height:30px;padding:0 0 0 10px;' })
            elif entry.entry_type == entry.ACTIVEDORMANT:
                self.fields[str(entry.id)] = forms.ChoiceField(choices=(('', ''),('active', 'Active'),('dormant', 'Dormant')), label=label, required=False, help_text=entry.help_text)
                self.fields[str(entry.id)].widget.attrs.update({'class': "form-control" , 'style':'width:120px; height:30px;padding:0 0 0 10px;' })
            elif entry.entry_type == entry.LABEL:
                self.fields[str(entry.id)] = forms.CharField(label=label,required=False, help_text=entry.help_text)
                self.fields[str(entry.id)].widget.attrs.update({'class': 'hide' })
            elif entry.entry_type == entry.CHECKBOX:
                if mte and mte.value == 'True':
                    self.fields[str(entry.id)] = forms.BooleanField(label=label,initial=True,required=False, help_text=entry.help_text)
                else:
                    self.fields[str(entry.id)] = forms.BooleanField(label=label,initial=None,required=False, help_text=entry.help_text)
                self.fields[str(entry.id)].widget.attrs.update({'class': "form-control", 'style':'width:50px; height:30px;'  })
            if entry.indent > 0:
                indent = str(entry.indent)
                self.fields[str(entry.id)].widget.attrs.update({'indent': indent })
            if mte:
                if entry.entry_type != entry.CHECKBOX:
                    self.fields[str(entry.id)].initial = mte.value
            if hint:
                label = '*Delete which is not applicable'
                self.fields[str(entry.id)] = forms.CharField(label=label,required=False)
                self.fields[str(entry.id)].widget.attrs.update({'class': 'hide' })

