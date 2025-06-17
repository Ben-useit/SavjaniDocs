from __future__ import absolute_import, unicode_literals

import logging

from datetime import timedelta

from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from acls.models import AccessControlList
from register.settings import ( register_status_choices,register_group_choices, quotation_status_choices, access_choices, statistic_access_choices )



#from checklist.forms import XDSoftDateTimePickerInput, XDSoftDateTimePickerInput

from .widgets import DatePickerInput

logger = logging.getLogger(__name__)


class LawyerActivityForm(forms.Form):
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        date_from = kwargs.pop('date_from', None)
        date_to = kwargs.pop('date_to', None)
        lawyers = kwargs.pop('lawyers', None)
        initials = []


        if lawyers:
                for lawyer in lawyers:
                        initials.append((lawyer.get_full_name(),lawyer.get_full_name()))
        initials = ((u'Duncan Singano', u'Duncan Singano'), (u'Martin Chagoma', u'Martin Chagoma'))
        super(LawyerActivityForm, self).__init__(*args, **kwargs)
        if date_from:
            self.fields['from'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                        initial=date_from.strftime("%d.%m.%Y"),help_text='')
        if date_to:
            self.fields['to'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                initial=date_to.strftime("%d.%m.%Y"), help_text='')
        self.fields['lawyers'] = forms.MultipleChoiceField(
            label="Lawyers",
            choices=statistic_access_choices.value, required=False,
            initial=initials
        )
        self.fields['lawyers'].widget.attrs.update({'class':'form-control'})

class RegisterStatisticForm(forms.Form):
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        date_from = kwargs.pop('date_from', None)
        date_to = kwargs.pop('date_to', None)
        super(RegisterStatisticForm, self).__init__(*args, **kwargs)
        #date_to = timezone.now().date()
        #date_from = date_to - timedelta(days=6)

        self.fields['from'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                initial=date_from.strftime("%d.%m.%Y"),help_text='')
        self.fields['to'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                initial=date_to.strftime("%d.%m.%Y"), help_text='')
        self.fields['lawyers'] = forms.MultipleChoiceField(
            help_text='To select multiple items in the list, hold down the Ctrl key. Then click on your desired items to select.', label="Lawyer",
            choices=statistic_access_choices.value, required=False,
        )
        self.fields['lawyers'].widget.attrs.update({'class':'form-control'})

class UserActivityForm(forms.Form):

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        date_from = kwargs.pop('date_from', None)
        date_to = kwargs.pop('date_to', None)
        super(UserActivityForm, self).__init__(*args, **kwargs)
        #date_to = timezone.now().date()
        #date_from = date_to - timedelta(days=6)

        self.fields['from'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                initial=date_from.strftime("%d.%m.%Y"),help_text='')
        self.fields['to'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                initial=date_to.strftime("%d.%m.%Y"), help_text='')



