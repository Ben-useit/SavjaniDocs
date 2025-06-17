from __future__ import absolute_import, unicode_literals
from datetime import datetime
import logging

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User
from acls.models import AccessControlList
from common.utils import get_str_from_aware
from metadata.widgets import ListTextWidget
from permissions.models import Role
from checklist.forms import XDSoftDateTimePickerInput
#from sapitwa.widgets import DateSelectionWidget
from .widgets import UserSelectionWidget,RangeInput, DateTimePickerInput, DatePickerInput
from .models import Register, Quotation, Department, Group, Status
from .permissions import permission_register_edit
from clients.models import Client, Contact
from sapitwa.utils import get_now, get_str_from_aware, get_users_of_role

logger = logging.getLogger(__name__)
from .settings import (
        register_status_choices,register_group_choices, quotation_status_choices,
        access_choices, statistic_access_choices
)
from exceptions import Exception
class DateField(forms.CharField):
    widget = DatePickerInput()
    default_error_messages = {
        u'required': u'This field is required.',
        u'invalid': u'Not a valid date format.'
    }
    def validate(self, value):
        if value in self.empty_values and self.required:
            raise ValidationError(self.error_messages['required'], code='required')
        elif value not in self.empty_values:
            try:
                datetime.strptime(value, "%d.%m.%Y").date()
            except Exception as e:
                raise ValidationError(self.error_messages['invalid'], code='invalid')

class RegisterStatisticForm(forms.Form):
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super(RegisterStatisticForm, self).__init__(*args, **kwargs)
        self.fields['from'] = forms.CharField(widget = XDSoftDateTimePickerInput(),required = False)
        self.fields['to'] = forms.CharField(widget = XDSoftDateTimePickerInput(), required = False)
        self.fields['lawyers'] = forms.MultipleChoiceField(
            help_text='To select multiple items in the list, hold down the Ctrl key. Then click on your desired items to select.', label="Show statistics for",
            choices=statistic_access_choices.value, initial='All', required=False,
        )

class RegisterRequestTransferForm(forms.Form):

    def __init__(self, *args, **kwargs):
        ACCESS_CHOICES = access_choices.value
        file_no = ''
        user = kwargs.pop('user', None)
        instance = kwargs.pop('instance', None)
        request_url = kwargs.pop('request_url', None)
        can_edit = True
        super(RegisterRequestTransferForm, self).__init__(*args, **kwargs)

        roles = Role.objects.all()
        user_role = get_user_role(user)
        self.fields['request_url'] = forms.CharField(widget = forms.HiddenInput(), required = False,initial=request_url)
        self.fields['access'] = forms.MultipleChoiceField(label='Access',choices=ACCESS_CHOICES, required = False)

class RegisterEditGroupForm(forms.Form):

    def __init__(self, *args, **kwargs):
        GROUP_CHOICES = register_group_choices.value
        file_no = ''
        user = kwargs.pop('user', None)
        instance = kwargs.pop('instance', None)
        request_url = kwargs.pop('request_url', None)
        can_edit = True
        super(RegisterEditGroupForm, self).__init__(*args, **kwargs)

        self.fields['request_url'] = forms.CharField(widget = forms.HiddenInput(), required = False,initial=request_url)
        self.fields['group'] = forms.MultipleChoiceField(label='Group',choices=GROUP_CHOICES, required = False)


class RegisterFileCreateForm(forms.Form):

    def __init__(self, *args, **kwargs):

        ACCESS_CHOICES = access_choices.value

        file_no = ''
        try:
           last_register_entry = Register.objects.all().exclude(file_no__startswith="TEMP__")[0]
           file_no = last_register_entry.file_no
        except:
           pass
        user = kwargs.pop('user', None)
        instance = kwargs.pop('instance', None)
        can_edit = True
        if user and not user.is_superuser:
            can_edit = permission_register_edit.stored_permission.requester_has_this(user)
        super(RegisterFileCreateForm, self).__init__(*args, **kwargs)
        timestamp = get_now(True)

        self.fields['opened'] = forms.CharField(widget = XDSoftDateTimePickerInput())
        self.fields['opened'].widget.attrs.update(
                    {'readonly': True }
            )
        clients = Client.objects.all().order_by('name')
        self.fields['clients'] = forms.ModelMultipleChoiceField(
                label=_('Clients'), help_text='',
                queryset=clients, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients
                )
        )
        contacts = Contact.objects.all().order_by('name')
        self.fields['contacts'] = forms.ModelMultipleChoiceField(
                label=_('Contacts'), help_text='',
                queryset=contacts, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=contacts
                )
        )
        self.fields['department'] = forms.ModelChoiceField(required = False, queryset=Department.objects.all())

        if can_edit:
            self.fields['file_no'] =  forms.CharField(label='File No',max_length=100,help_text='The file number. Last one used: '+file_no)
            self.fields['parties'] = forms.CharField(label='Parties',max_length=512)
            self.fields['group'] = forms.ModelChoiceField(label='Group',queryset=Group.objects.all(), required = False)
            self.fields['status'] = forms.ModelChoiceField(label='Status',queryset=Status.objects.all())
            roles = Role.objects.all()
            user_role = get_user_role(user)
            if user_role:
                roles = roles.exclude(id = user_role.id)
            self.fields['access'] = forms.ModelMultipleChoiceField(
                help_text='The user you select here will be able to add document to this File No.', label="Give access:",
                queryset=roles, required=False,
                widget=UserSelectionWidget(attrs={'class': 'select2-tags','color':'#555'})
            )
            self.fields['access'] = forms.MultipleChoiceField(
                help_text='The user you select here will be able to add document to this File No.', label="Give access:",
                choices=ACCESS_CHOICES, required=False,
                widget=UserSelectionWidget(attrs={'class': 'select2-tags','color':'#555'})
            )
        else:
            help_text = """
            As you do not have permissions to activate a new file no.,<br />
            your request will be sent to someone with sufficient permissions.<br />
            <b>You will be notified by mail as soon as the file no. has been created.</b>"""
            self.fields['parties'] = forms.CharField(label='Parties',max_length=512,help_text=help_text)

class RegisterFileCreateForm1(forms.ModelForm):

    class Meta:
        model = Register
        fields = ('opened', 'file_no', 'parties')

    def __init__(self, *args, **kwargs):
        data = kwargs.get('data',None)
        instance = kwargs.pop('instance', None)
        super(RegisterFileCreateForm,self).__init__(*args, **kwargs)

        file_no = ''
        try:
           last_register_entry = Register.objects.all().exclude(file_no__startswith="TEMP__")[0]
           file_no = last_register_entry.file_no
        except:
           pass


        # ~ self.fields['opened'] = forms.CharField(widget = DateTimePickerInput())
        # ~ self.fields['opened'].widget.attrs.update(
                    # ~ {'readonly': True }
            # ~ )
        self.fields['file_no'] =  forms.CharField(label='File No',max_length=100,help_text='The file number. Last one used: '+file_no)
        clients = Client.objects.all().order_by('name')
        self.fields['clients'] = forms.ModelMultipleChoiceField(
                label=_('Clients'), help_text='',
                queryset=clients, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients
                )
        )

        if data:
            if 'register' in data:
                register = data['register']
                self.fields['opened'].initial = register.opened
                self.fields['file_no'].initial = register.file_no
                self.fields['parties'].initial = register.parties

    def clean_file_no(self):
        data = self.cleaned_data['file_no']
        if data and Register.objects.filter(file_no=data).exists():
            raise ValidationError("<"+data+"> does already exist.")
        return data

class ActiveFileTrackingChartCreateForm(forms.Form):

    def __init__(self, *args, **kwargs):
        obj = kwargs.pop('instance', None)
        super(ActiveFileTrackingChartCreateForm, self).__init__(*args, **kwargs)
        self.fields['retain_or_transfer'] = forms.CharField(label='Retain file or transfer required?',required = False)
        self.fields['date_closure_letter'] = forms.CharField(label='Date of closure letter to client',widget = DatePickerInput(),required=False)
        self.fields['date_closure_letter'].widget.attrs.update(
                    {'readonly': True }
            )
        self.fields['instructions'] = forms.CharField(label='Instructions received regarding file transfer', widget = DatePickerInput(),required=False)
        self.fields['instructions'].widget.attrs.update(
                    {'readonly': True }
            )
        clients = Client.objects.all()
        self.fields['client'] = forms.ModelMultipleChoiceField(
                label=_('Client'), help_text='',
                queryset=clients, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients
                )
        )
        self.fields['notice'] = forms.CharField(label='Notice of change of legal practitioners', widget = DatePickerInput(),required=False)
        self.fields['notice'].widget.attrs.update(
                    {'readonly': True }
            )
        self.fields['receipt'] = forms.CharField(label='Receipt of file acknowledgement',widget = DatePickerInput(),required=False)
        self.fields['receipt'].widget.attrs.update(
                    {'readonly': True }
            )
        self.fields['date_completion'] = forms.CharField(label='Date of completion of transfer process',widget = DatePickerInput(),required=False)
        self.fields['date_completion'].widget.attrs.update(
                    {'readonly': True }
            )


class ActiveFileTrackingChartEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        obj = kwargs.pop('instance', None)
        super(ActiveFileTrackingChartEditForm, self).__init__(*args, **kwargs)
        self.fields['retain_or_transfer'] = forms.CharField(
            label='Retain file or transfer required?', required = False
        )
        self.fields['date_closure_letter'] = DateField(
            label='Date of closure letter to client', required=False,
          )
        self.fields['instructions'] = DateField(
            label='Instructions received regarding file transfer', required=False
        )
        clients = Client.objects.all()
        self.fields['client'] = forms.ModelMultipleChoiceField(
                label=_('Client'), help_text='',
                queryset=clients, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients
                )
        )
        self.fields['notice'] = DateField(
            label='Notice of change of legal practitioners', required=False
        )
        self.fields['receipt'] = DateField(
            label='Receipt of file acknowledgement', required=False
        )
        self.fields['date_completion'] = DateField(
            label='Date of completion of transfer process', required=False
        )
        if obj:
            self.fields['retain_or_transfer'].initial = obj.retain_or_transfer
            self.fields['date_closure_letter'].initial = obj.get_date(obj.date_closure_letter,no=False)
            self.fields['instructions'].initial = obj.get_date(obj.instructions,no=False)
            self.fields['client'].initial = obj.get_client_file_transferrred_to(),
            self.fields['notice'].initial = obj.get_date(obj.notice,no=False)
            self.fields['receipt'].initial = obj.get_date(obj.receipt,no=False)
            self.fields['date_completion'].initial = obj.get_date(obj.date_completion,no=False)



class RegisterFileEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        STATUS_CHOICES = register_status_choices.value
        GROUP_CHOICES = register_group_choices.value
        ACCESS_CHOICES = access_choices.value
        last_register_entry = Register.objects.all().exclude(file_no__startswith="TEMP__")[0]
        user = kwargs.pop('user', None)
        instance = kwargs.pop('instance', None)
        reg_id = kwargs.pop('reg_id', None)
        req_id = kwargs.pop('req_id', None)
        request_path = kwargs.pop('request_path', None)
        super(RegisterFileEditForm, self).__init__(*args, **kwargs)
        register_entry = Register.objects.get(pk=reg_id)
        can_edit = True
        if user and not user.is_superuser:
            can_edit = permission_register_edit.stored_permission.requester_has_this(user)
        if register_entry.file_no.startswith("TEMP__"):
            file_no = ""
        else:
            file_no = register_entry.file_no
        timestamp = register_entry.opened.strftime('%d.%m.%Y')
        self.fields['opened'] = forms.CharField(initial=timestamp, widget = XDSoftDateTimePickerInput())
        self.fields['opened'].widget.attrs.update(
                    {'readonly': True }
            )
        clients = Client.objects.all()
        self.fields['clients'] = forms.ModelMultipleChoiceField(
                label=_('Clients'), help_text='',
                queryset=clients, required=False,
                initial = register_entry.clients.all(),
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients
                )
        )
        contacts = Contact.objects.all()
        self.fields['contacts'] = forms.ModelMultipleChoiceField(
                label=_('Contacts'), help_text='',
                queryset=contacts, required=False,
                initial = register_entry.contacts.all(),
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=contacts
                )
        )

        #self.fields['clients'] =  forms.ModelMultipleChoiceField(required = False, queryset=Client.objects.all().order_by('name'), initial=register_entry.client)
        self.fields['department'] =  forms.ModelChoiceField(required = False, queryset=Department.objects.all(), initial=register_entry.department)
        self.fields['file_no'] =  forms.CharField(label='File No',max_length=100,initial=file_no,help_text='The file number. Last one used: '+str(last_register_entry.file_no))
        self.fields['parties'] = forms.CharField(label='Parties',initial=register_entry.parties,max_length=512)
        self.fields['group'] = forms.ModelChoiceField(label='Group',queryset=Group.objects.all(),
            required = False, initial=register_entry.group
        )
        self.fields['status'] = forms.ModelChoiceField(
            label='Status',queryset=Status.objects.all(),
            initial = register_entry.status
        )

        roles_selected = None
        u = register_entry.lawyers.first()

        if u and [u.first_name+' '+u.last_name,u.first_name+' '+u.last_name] in ACCESS_CHOICES:
            roles_selected = [u.first_name+' '+u.last_name,u.first_name+' '+u.last_name]
        self.fields['access'] = forms.MultipleChoiceField(
            help_text='The user you select here will be able to add document to this File No.', label="Give access:",
            choices=ACCESS_CHOICES, required=False, initial=roles_selected,
            widget=UserSelectionWidget(attrs={'class': 'select2-tags','color':'#555'})
        )
        self.fields['request'] = forms.CharField(max_length=254, initial=request_path)
        self.fields['request'].widget = forms.HiddenInput()

class RegisterSearchForm(forms.Form):

    Search = forms.CharField(initial = '', max_length=200)
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        queryset = kwargs.pop('queryset', None)
        super(RegisterSearchForm, self).__init__(*args, **kwargs)


from .widgets import LawyerFormWidget, FilterFormWidget, DateTimePickerInput

class QuotationFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        request_query = kwargs.pop('request_query', None)
        status_list = kwargs.pop('status_list', None)
        search_string = kwargs.pop('search_q', None)
        initials = kwargs.pop('initials', {})
        super(QuotationFilterForm, self).__init__(*args, **kwargs)
        self.fields['search'] = forms.CharField(label='', required = False)
        self.fields['search'].widget.attrs.update({'class':'form-control'})
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

class DepartmentFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        request_query = kwargs.pop('request_query', None)
        status_list = kwargs.pop('status_list', None)
        lawyers = kwargs.pop('lawyers', None)
        departments = kwargs.pop('departments', None)
        search_string = kwargs.pop('search_q', None)
        initials = kwargs.pop('initials', {})
        super(DepartmentFilterForm, self).__init__(*args, **kwargs)
        self.fields['search'] = forms.CharField(label='', required = False)
        self.fields['search'].widget.attrs.update({'class':'form-control'})
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

        if lawyers:
            if initials.get('lawyers'):
                selected = User.objects.filter(id__in=initials.get('lawyers'))
            else:
                selected = User.objects.none()
            self.fields['lawyers'] = forms.ModelMultipleChoiceField(
                label=_('Lawyers'), help_text='',
                queryset=lawyers, required=False,
                initial = lawyers,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=lawyers,selected=selected
                )
            )

        if departments:
            if initials.get('departments'):
                selected = Department.objects.filter(id__in=initials.get('departments'))
            else:
                selected = User.objects.none()
            self.fields['departments'] = forms.ModelMultipleChoiceField(
                label=_('Departments'), help_text='',
                queryset=departments, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=departments,selected=selected
                )
            )

class RegisterFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        request_query = kwargs.pop('request_query', None)
        status_list = kwargs.pop('status_list', None)
        room = kwargs.pop('room',None)
        lawyers = kwargs.pop('lawyers', None)
        clients = kwargs.pop('clients', None)
        groups = kwargs.pop('groups', None)
        departments = kwargs.pop('departments', None)
        search_string = kwargs.pop('search_q', None)
        initials = kwargs.pop('initials', {})
        super(RegisterFilterForm, self).__init__(*args, **kwargs)
        self.fields['search'] = forms.CharField(label='', required = False)
        self.fields['search'].widget.attrs.update({'class':'form-control'})
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

        if lawyers:
            if initials.get('lawyers'):
                selected = User.objects.filter(id__in=initials.get('lawyers'))
            else:
                selected = User.objects.none()
            self.fields['lawyers'] = forms.ModelMultipleChoiceField(
                label=_('Lawyers'), help_text='',
                queryset=lawyers, required=False,
                initial = lawyers,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=lawyers,selected=selected
                )
            )
        if clients:
            if initials.get('clients'):
                selected = Client.objects.filter(id__in=initials.get('clients'))
            else:
                selected = User.objects.none()
            self.fields['clients'] = forms.ModelMultipleChoiceField(
                label=_('Clients'), help_text='',
                queryset=clients, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients, selected=selected
                )
            )
        if groups:
            if initials.get('groups'):
                selected = Group.objects.filter(id__in=initials.get('groups'))
            else:
                selected = User.objects.none()
            self.fields['groups'] = forms.ModelMultipleChoiceField(
                label=_('Group'), help_text='',
                queryset=groups, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=groups,selected=selected
                )
            )
        if departments:
            if initials.get('departments'):
                selected = Department.objects.filter(id__in=initials.get('departments'))
            else:
                selected = User.objects.none()
            self.fields['departments'] = forms.ModelMultipleChoiceField(
                label=_('Departments'), help_text='',
                queryset=departments, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=departments,selected=selected
                )
            )
        self.fields['checklist'] = forms.BooleanField(label="Has checklist",required = False)
        if initials.get('checklist'):
            self.fields['checklist'].widget.attrs.update(
                {'checked': True}
            )
        self.fields['status_report'] = forms.BooleanField(label="Has status report",required = False)
        if initials.get('status_report'):
            self.fields['status_report'].widget.attrs.update(
                {'checked': True}
            )
        self.fields['room'] = forms.BooleanField(label="Archived",required = False)
        if initials.get('room'):
            self.fields['room'].widget.attrs.update(
                {'checked': True}
            )
        self.fields['documents_check'] = forms.BooleanField(label="", required = False)
        if initials.get('documents_check'):
            self.fields['documents_check'].widget.attrs.update(
                {'checked': True}
            )

        if initials.get('documents'):
            value = initials.get('documents')
        else:
            value = 50
        self.fields['documents'] = forms.IntegerField(required=False,
            label=_('Documents'),
            min_value=0,
            max_value=100,
            widget=RangeInput(attrs={"max": 100, "id" : "myRange", "value": value })
        )


class FilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        search_string = kwargs.pop('search_q', None)
        register_filter = kwargs.pop('register_filter', None)
        super(FilterForm, self).__init__(*args, **kwargs)

        self.fields['from'] = forms.CharField(label='Opened From' ,widget = XDSoftDateTimePickerInput(),required=False)
        self.fields['from'].widget.attrs.update(
                        {'class':'form-control', 'readonly': True}
                )
        self.fields['to'] = forms.CharField(label='Opened To' ,widget = XDSoftDateTimePickerInput(),required=False)
        self.fields['to'].widget.attrs.update(
                        {'class':'form-control', 'readonly': True}
                )
        for k,v in register_filter.items():
            if k == 'Number of uploaded documents':
                choices = [('---','---')]
                choices.append((0,0))
                choices.append((1,1))
                choices.append((2,2))
                choices.append((3,3))
                choices.append((4,4))
                choices.append((5,5))
                choices.append((6,6))
                choices.append((7,7))
                choices.append((8,8))
                choices.append((9,9))
                choices.append((10,10))

            else:
                choices = [(0,'---')]
                for i in  v:
                    choices.append((i,i))
            self.fields[str(k)] = forms.ChoiceField(label = k, choices = choices , required = False,
                widget = forms.Select(attrs={'class':'form-control','style' :"width:300px;" }))

class QuotationSearchForm(forms.Form):

    Search = forms.CharField(initial = '', max_length=200)
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        queryset = kwargs.pop('queryset', None)
        super(QuotationSearchForm, self).__init__(*args, **kwargs)

def get_user_role(user):
    role = None
    if user and not user.is_superuser:
        try:
            role = Role.objects.get(label=user.first_name+" "+user.last_name)
        except Role.DoesNotExist:
            pass
    return role


class QuotationEntryCreateForm(forms.Form):

    def __init__(self, *args, **kwargs):
        STATUS_CHOICES = quotation_status_choices.value
        ACCESS_CHOICES = access_choices.value
        file_no = ''
        try:
           last_register_entry = Quotation.objects.all().exclude(file_no__startswith="TEMP__")[0]
           file_no = last_register_entry.file_no
        except:
           pass
        user = kwargs.pop('user', None)
        instance = kwargs.pop('instance', None)
        can_edit = True
        if user and not user.is_superuser:
            can_edit = permission_register_edit.stored_permission.requester_has_this(user)
        super(QuotationEntryCreateForm, self).__init__(*args, **kwargs)
        timestamp = get_now(True)

        self.fields['opened'] = forms.CharField(widget = XDSoftDateTimePickerInput())
        self.fields['opened'].widget.attrs.update(
                    {'readonly': True }
            )

        if can_edit:
            self.fields['file_no'] =  forms.CharField(label='File No',max_length=100,help_text='The file number. Last one used: '+file_no)
            self.fields['parties'] = forms.CharField(label='Parties',max_length=512)
            #self.fields['group'] = forms.ChoiceField(label='Group',choices=GROUP_CHOICES, required = False)
            #self.fields['status'] = forms.ChoiceField(label='Status',choices=STATUS_CHOICES)
            status_qs = Status.objects.exclude(name='').exclude(name='Not active').exclude(name='Dormant').exclude(name='Request to close').exclude(name='Request to transfer').exclude(name='Transferred to client')
            self.fields['status'] = forms.ModelChoiceField(label='Status',queryset=status_qs)

            # ~ roles = Role.objects.all()
            # ~ user_role = get_user_role(user)
            # ~ if user_role:
                # ~ roles = roles.exclude(id = user_role.id)
            # ~ self.fields['access'] = forms.ModelMultipleChoiceField(
                # ~ help_text='The user you select here will be able to add document to this File No.', label="Give access:",
                # ~ queryset=roles, required=False,
                # ~ widget=UserSelectionWidget(attrs={'class': 'select2-tags','color':'#555'})
            # ~ )
        else:
            help_text = """
            As you do not have permissions to create a new quotation number,<br />
            your request will be sent to someone with sufficient permissions.<br />
            <b>You will be notified by mail as soon as the quotation number has been created.</b>"""
            self.fields['parties'] = forms.CharField(label='Parties',max_length=512,help_text=help_text)

    def clean_file_no(self):
        data = self.cleaned_data['file_no']
        if data and Quotation.objects.filter(file_no=data).exists():
            raise ValidationError("<"+data+"> does already exist.")
        return data


class QuotationEntryEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        STATUS_CHOICES = quotation_status_choices.value
        ACCESS_CHOICES = access_choices.value
        last_register_entry = Quotation.objects.all().exclude(file_no__startswith="TEMP__")[0]
        user = kwargs.pop('user', None)
        instance = kwargs.pop('instance', None)
        reg_id = kwargs.pop('reg_id', None)
        req_id = kwargs.pop('req_id', None)
        super(QuotationEntryEditForm, self).__init__(*args, **kwargs)
        register_entry = Quotation.objects.get(pk=reg_id)
        can_edit = True
        if user and not user.is_superuser:
            can_edit = permission_register_edit.stored_permission.requester_has_this(user)
        if register_entry.file_no.startswith("TEMP__"):
            file_no = ""
        else:
            file_no = register_entry.file_no
        timestamp = get_str_from_aware(str(register_entry.opened),True)
        timestamp = register_entry.opened.strftime('%d.%m.%Y') #get_str_from_aware(str(register_entry.opened),True)
        self.fields['opened'] = forms.CharField(initial=timestamp, widget = XDSoftDateTimePickerInput())
        self.fields['opened'].widget.attrs.update(
                    {'readonly': True }
            )
        self.fields['file_no'] =  forms.CharField(label='File No',max_length=100,initial=file_no,help_text='The file number. Last one used: '+str(last_register_entry.file_no))
        self.fields['parties'] = forms.CharField(label='Parties',initial=register_entry.parties,max_length=512)
        self.fields['status'] = forms.ChoiceField(label='Status',choices=STATUS_CHOICES,initial=register_entry.status)

        roles = Role.objects.all()
        user_role = get_user_role(user)
        if user_role:
            roles = roles.exclude(id = user_role.id)
        roles_selected = []
        acls = AccessControlList.objects.filter(object_id=register_entry.pk, content_type=ContentType.objects.get_for_model(register_entry))
        for a in acls:
            roles_selected.append(a.role)
        self.fields['access'] = forms.ModelMultipleChoiceField(
            help_text='The user you select here will be able to add document to this File No.', label="Give access:",
            queryset=roles, required=False, initial=roles_selected,
            widget=UserSelectionWidget(attrs={'class': 'select2-tags','color':'#555'})
        )
