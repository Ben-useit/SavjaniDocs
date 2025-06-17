from __future__ import absolute_import, unicode_literals
import datetime
from bootstrap_modal_forms.forms import BSModalModelForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from acls.models import AccessControlList

from register.widgets import ( LawyerFormWidget, FilterFormWidget, DateTimePickerInput,
        UserSelectionWidget,RangeInput
)

from register.models import Status

from .models import Client, Contact
from .permissions import permission_client_view

from django.contrib.auth.models import User


class ContactCreateForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'position','phone','email']

class ClientCreateForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('name', 'address', 'city')

    def __init__(self, *args, **kwargs):
        data = kwargs.pop('data',None)
        super(ClientCreateForm, self).__init__(*args, **kwargs)
        if data:
            if 'client' in data:
                client = data['client']
                self.fields['name'].initial = client.name
                self.fields['address'].initial = client.address
                self.fields['city'].initial = client.city

class ClientEditForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('name', 'address', 'city')

    def __init__(self, *args, **kwargs):
        data = kwargs.pop('data',None)
        super(ClientEditForm, self).__init__(*args, **kwargs)
        if data:
            client = data['client']
            self.fields['name'].initial = client.name
            self.fields['address'].initial = client.address
            self.fields['city'].initial = client.city

class ClientListFilesFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        request_query = kwargs.pop('request_query', None)
        status_list = kwargs.pop('status_list', None)
        lawyers = kwargs.pop('lawyers', None)
        groups = kwargs.pop('groups', None)
        departments = kwargs.pop('departments', None)
        files = kwargs.pop('files', None)
        search_string = kwargs.pop('search_q', None)
        super(ClientListFilesFilterForm, self).__init__(*args, **kwargs)
        self.fields['search'] = forms.CharField(label='', required = False)
        self.fields['search'].widget.attrs.update({'class':'form-control'})
        self.fields['from'] = forms.CharField(label='Opened From' ,widget = DateTimePickerInput(),required=False)
        self.fields['from'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})
        self.fields['to'] = forms.CharField(label='Opened To' ,widget = DateTimePickerInput(),required=False)
        self.fields['to'].widget.attrs.update({'class':'form-control date-entry', 'readonly': True})
        if status_list:
            self.fields['status'] = forms.ModelMultipleChoiceField(
                label=_('Status'), help_text='',
                queryset=status_list, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=status_list
                )
            )

        if lawyers:
            self.fields['lawyers'] = forms.ModelMultipleChoiceField(
                label=_('Lawyers'), help_text='',
                queryset=lawyers, required=False,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=lawyers
                )
            )
        if groups:
            self.fields['groups'] = forms.ModelMultipleChoiceField(
                label=_('Group'), help_text='',
                queryset=groups, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=groups
                )
            )
        if files:
            self.fields['files'] = forms.ModelMultipleChoiceField(
                label=_('Files  '), help_text='',
                queryset=files, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=files
                )
            )
        if departments:
            self.fields['departments'] = forms.ModelMultipleChoiceField(
                label=_('Departments'), help_text='',
                queryset=departments, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=departments
                )
            )
        self.fields['checklist'] = forms.BooleanField(label="Has checklist", required = False)
        self.fields['documents_check'] = forms.BooleanField(label="", required = False)
        self.fields['documents'] = forms.IntegerField(required=False,
            label=_('Documents'),
            min_value=0,
            max_value=100,
            widget=RangeInput(attrs={"max": 100, "id" : "myRange" })
        )

class ClientFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):

        #ACCESS_CHOICES = access_choices.value

        user = kwargs.pop('user', None)
        request_query = kwargs.pop('request_query', None)
        clients_list = kwargs.pop('clients_list', None)
        contacts_list = kwargs.pop('contacts_list', None)
        status_list = kwargs.pop('status_list', None)
        lawyers_list = kwargs.pop('lawyers_list', None)
        initials = kwargs.pop('initials', {})
        super(ClientFilterForm, self).__init__(*args, **kwargs)
        if clients_list:
            if initials.get('clients'):
                selected = Client.objects.filter(id__in=initials.get('clients'))
            else:
                selected = Client.objects.none()
            self.fields['clients'] = forms.ModelMultipleChoiceField(
                label=_('Clients'), help_text='',
                queryset=clients_list, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients_list, selected=selected
                )
            )
        if contacts_list:
            if initials.get('contacts'):
                selected = Contact.objects.filter(id__in=initials.get('contacts'))
            else:
                selected = Contact.objects.none()
            self.fields['contacts'] = forms.ModelMultipleChoiceField(
                label=_('Contacts'), help_text='',
                queryset=contacts_list, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=contacts_list, selected = selected
                )
            )

        if status_list:
            if initials.get('status'):
                selected = Status.objects.filter(id__in=initials.get('status'))
            else:
                selected = Status.objects.none()
            self.fields['status'] = forms.ModelMultipleChoiceField(
                label=_('Status'), help_text='',
                queryset=status_list, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=status_list, selected = selected
                )
            )
        if lawyers_list:
            if initials.get('lawyers'):
                selected = User.objects.filter(id__in=initials.get('lawyers'))
            else:
                selected = User.objects.none()
            self.fields['lawyers'] = forms.ModelMultipleChoiceField(
                label=_('Lawyer'), help_text='',
                queryset=lawyers_list, required=False,
                initial = lawyers_list,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=lawyers_list,selected=selected
                )
            )
