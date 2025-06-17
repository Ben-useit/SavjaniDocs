from __future__ import absolute_import, unicode_literals

import logging

from datetime import timedelta

from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from acls.models import AccessControlList
from register.widgets import LawyerFormWidget, FilterFormWidget, DateTimePickerInput
from register.settings import ( register_status_choices,register_group_choices, quotation_status_choices, access_choices, statistic_access_choices )



#from checklist.forms import XDSoftDateTimePickerInput, XDSoftDateTimePickerInput
from register.widgets import DateTimePickerInput
from .widgets import DatePickerInput

logger = logging.getLogger(__name__)

class UploadReportFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        #request_query = kwargs.pop('request_query', None)
        # ~ status_list = kwargs.pop('status_list', None)
        # ~ lawyers = kwargs.pop('lawyers', None)
        users = kwargs.pop('users', None)
        # ~ groups = kwargs.pop('groups', None)
        # ~ departments = kwargs.pop('departments', None)
        # ~ search_string = kwargs.pop('search_q', None)
        initials = kwargs.pop('initials', {})
        super(UploadReportFilterForm, self).__init__(*args, **kwargs)
        self.fields['from'] = forms.CharField(label='Opened From' ,widget = DateTimePickerInput(),required=False)
        if initials.get('from'):
            self.fields['from'].widget.attrs.update(
                {'class':'form-control date-entry', 'readonly': True,
                 'value' : initials.get('from') }
            )
        else:
            self.fields['from'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})

        self.fields['to'] = forms.CharField(label='Opened To' ,widget = DateTimePickerInput(),required=False)
        if initials.get('to'):
            self.fields['to'].widget.attrs.update(
                {'class':'form-control date-entry', 'readonly': True,
                 'value': initials.get('to')}
            )
        else:
            self.fields['to'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})

        if user.is_superuser and users:
            self.fields['users'] = forms.ModelMultipleChoiceField(
                label=_('Users'), help_text='',
                queryset=users, required=False,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=users
                )
            )

class TransferReportFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        # ~ user = kwargs.pop('user', None)
        # ~ request_query = kwargs.pop('request_query', None)
        # ~ status_list = kwargs.pop('status_list', None)
        # ~ lawyers = kwargs.pop('lawyers', None)
        # ~ clients = kwargs.pop('clients', None)
        # ~ groups = kwargs.pop('groups', None)
        # ~ departments = kwargs.pop('departments', None)
        # ~ search_string = kwargs.pop('search_q', None)
        transferred_to_lawyers = kwargs.pop('transferred_to_lawyers', None)
        initials = kwargs.pop('initials', {})
        super(TransferReportFilterForm, self).__init__(*args, **kwargs)
        self.fields['from'] = forms.CharField(label='Opened From' ,widget = DateTimePickerInput(),required=False)
        if initials.get('from'):
            self.fields['from'].widget.attrs.update(
                {'class':'form-control date-entry', 'readonly': True,
                 'value' : initials.get('from') }
            )
        else:
            self.fields['from'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})

        self.fields['to'] = forms.CharField(label='Opened To' ,widget = DateTimePickerInput(),required=False)
        if initials.get('to'):
            self.fields['to'].widget.attrs.update(
                {'class':'form-control date-entry', 'readonly': True,
                 'value': initials.get('to')}
            )
        else:
            self.fields['to'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})

        if transferred_to_lawyers:
            self.fields['transferred_to'] = forms.ModelMultipleChoiceField(
                label=_('Transferred to'), help_text='',
                queryset=transferred_to_lawyers, required=False,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=transferred_to_lawyers
                )
            )

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
    # ~ def __init__1(self, *args, **kwargs):
        # ~ instance = kwargs.pop('instance', None)
        # ~ date_from = kwargs.pop('date_from', None)
        # ~ date_to = kwargs.pop('date_to', None)
        # ~ super(RegisterStatisticForm, self).__init__(*args, **kwargs)
        # ~ #date_to = timezone.now().date()
        # ~ #date_from = date_to - timedelta(days=6)

        # ~ self.fields['from'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                # ~ initial=date_from.strftime("%d.%m.%Y"),help_text='')
        # ~ self.fields['to'] = forms.CharField(widget = DatePickerInput(attrs = {'class':'form-control'}),
                # ~ initial=date_to.strftime("%d.%m.%Y"), help_text='')
        # ~ self.fields['lawyers'] = forms.MultipleChoiceField(
            # ~ help_text='To select multiple items in the list, hold down the Ctrl key. Then click on your desired items to select.', label="Lawyer",
            # ~ choices=statistic_access_choices.value, required=False,
        # ~ )
        # ~ self.fields['lawyers'].widget.attrs.update({'class':'form-control'})
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        request_query = kwargs.pop('request_query', None)
        status_list = kwargs.pop('status_list', None)
        lawyers = kwargs.pop('lawyers', None)
        clients = kwargs.pop('clients', None)
        groups = kwargs.pop('groups', None)
        departments = kwargs.pop('departments', None)
        search_string = kwargs.pop('search_q', None)
        super(RegisterStatisticForm, self).__init__(*args, **kwargs)
        self.fields['from'] = forms.CharField(label='Opened From' ,widget = DateTimePickerInput(),required=False)
        self.fields['from'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})
        self.fields['to'] = forms.CharField(label='Opened To' ,widget = DateTimePickerInput(),required=False)
        self.fields['to'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})
        if lawyers:
            self.fields['lawyers'] = forms.ModelMultipleChoiceField(
                label=_('Lawyers'), help_text='',
                queryset=lawyers, required=False,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=lawyers
                )
            )

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



