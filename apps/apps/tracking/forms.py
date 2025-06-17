from __future__ import absolute_import, unicode_literals
from datetime import datetime
from exceptions import Exception
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from register.widgets import FilterFormWidget, LawyerFormWidget
from reports.widgets import DatePickerInput
from clients.models import Client

from .models import TrackedFile

class DateField(forms.CharField):
    widget = DatePickerInput()
    default_error_messages = {
        u'required': u'This field is required.',
        u'invalid': u'Not a valid date2 format.'
    }
    def validate(self, value):
        if value in self.empty_values and self.required:
            raise ValidationError(self.error_messages['required'], code='required')
        elif value not in self.empty_values:
            try:
                datetime.strptime(value, "%d.%m.%Y").date()
            except Exception as e:
                raise ValidationError(self.error_messages['invalid'], code='invalid')

class TrackingFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        request_query = kwargs.pop('request_query', None)
        status_list = kwargs.pop('status_list', None)
        lawyers = kwargs.pop('lawyers', None)
        ex_lawyers = kwargs.pop('ex_lawyers', None)
        clients = kwargs.pop('clients', None)
        groups = kwargs.pop('groups', None)
        departments = kwargs.pop('departments', None)
        search_string = kwargs.pop('search_q', None)
        initials = kwargs.pop('initials', {})
        super(TrackingFilterForm, self).__init__(*args, **kwargs)
        self.fields['from'] = DateField(label='File opened From' ,required=False)
        self.fields['from'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('from'):
            self.fields['from'].widget.attrs.update(
                {'value' : initials.get('from') }
            )
        self.fields['to'] = DateField(label='File opened To' ,required=False)
        self.fields['to'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('to'):
            self.fields['to'].widget.attrs.update(
                {'value' : initials.get('to') }
            )
        self.fields['retain_or_transfer'] = forms.ChoiceField(
            label='Retain file or transfer required?', choices=TrackedFile.ACTION_CHOICES, required = False
        )
        self.fields['closure_from'] = DateField(label='Closure Letter from' ,required=False)
        self.fields['closure_from'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('closure_from'):
            self.fields['closure_from'].widget.attrs.update(
                {'value' : initials.get('closure_from') }
            )
        self.fields['closure_to'] = DateField(label='Closure Letter to' ,required=False)
        self.fields['closure_to'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('closure_to'):
            self.fields['closure_to'].widget.attrs.update(
                {'value' : initials.get('closure_to') }
            )
        self.fields['closure_from'] = DateField(label='Closure Letter from' ,required=False)
        self.fields['closure_from'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('closure_from'):
            self.fields['closure_from'].widget.attrs.update(
                {'value' : initials.get('closure_from') }
            )
        self.fields['closure_to'] = DateField(label='Closure Letter to' ,required=False)
        self.fields['closure_to'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('closure_to'):
            self.fields['closure_to'].widget.attrs.update(
                {'value' : initials.get('closure_to') }
            )
        self.fields['instructions_from'] = DateField(required=False)
        self.fields['instructions_from'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('instructions_from'):
            self.fields['instructions_from'].widget.attrs.update(
                {'value' : initials.get('instructions_from') }
            )
        self.fields['instructions_to'] = DateField(required=False)
        self.fields['instructions_to'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('instructions_to'):
            self.fields['instructions_to'].widget.attrs.update(
                {'value' : initials.get('instructions_to') }
            )
        self.fields['notice_from'] = DateField(required=False)
        self.fields['notice_from'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('notice_from'):
            self.fields['notice_from'].widget.attrs.update(
                {'value' : initials.get('notice_from') }
            )
        self.fields['notice_to'] = DateField(required=False)
        self.fields['notice_to'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('notice_to'):
            self.fields['notice_to'].widget.attrs.update(
                {'value' : initials.get('notice_to') }
            )
        self.fields['receipt_from'] = DateField(required=False)
        self.fields['receipt_from'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('receipt_from'):
            self.fields['receipt_from'].widget.attrs.update(
                {'value' : initials.get('receipt_from') }
            )
        self.fields['receipt_to'] = DateField(label='Closure Letter to' ,required=False)
        self.fields['receipt_to'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('receipt_to'):
            self.fields['receipt_to'].widget.attrs.update(
                {'value' : initials.get('receipt_to') }
            )
        self.fields['completion_from'] = DateField(required=False)
        self.fields['completion_from'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('completion_from'):
            self.fields['completion_from'].widget.attrs.update(
                {'value' : initials.get('completion_from') }
            )
        self.fields['completion_to'] = DateField(required=False)
        self.fields['completion_to'].widget.attrs.update({'class':'form-control date-entry'})
        if initials.get('completion_to'):
            self.fields['completion_to'].widget.attrs.update(
                {'value' : initials.get('completion_to') }
            )

        if lawyers:
            if initials.get('lawyers'):
                selected = User.objects.filter(id__in=initials.get('lawyers'))
            else:
                selected = User.objects.none()
            self.fields['lawyers'] = forms.ModelMultipleChoiceField(
                label='Lawyers ( internal )', help_text='',
                queryset=lawyers, required=False,
                initial = lawyers,
                widget=LawyerFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=lawyers,selected=selected
                )
            )
        if ex_lawyers:
            if initials.get('ex_lawyers'):
                selected = Client.objects.filter(id__in=initials.get('ex_lawyers'))
            else:
                selected = Client.objects.none()
            self.fields['ex_lawyers'] = forms.ModelMultipleChoiceField(
                label='Lawyer ( external )',
                queryset=ex_lawyers, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=ex_lawyers, selected=selected
                )
            )
        if clients:
            if initials.get('clients'):
                selected = Client.objects.filter(id__in=initials.get('clients'))
            else:
                selected = Client.objects.none()
            self.fields['clients'] = forms.ModelMultipleChoiceField(
                label='Clients',
                queryset=clients, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients, selected=selected
                )
            )
        self.fields['cb_closure'] = forms.BooleanField(label='Date of closure',required = False)
        self.fields['cb_instruction'] = forms.BooleanField(label='Date instructions received',required = False)
        self.fields['cb_notice'] = forms.BooleanField(label='Date of notice of change',required = False)
        self.fields['cb_acknowledgement'] = forms.BooleanField(label='Date of receipt of file acknowledgement',required = False)
        self.fields['cb_completion'] = forms.BooleanField(label='Date of completion of transfer process',required = False)
        # ~ if groups:
            # ~ if initials.get('groups'):
                # ~ selected = Group.objects.filter(id__in=initials.get('groups'))
            # ~ else:
                # ~ selected = User.objects.none()
            # ~ self.fields['groups'] = forms.ModelMultipleChoiceField(
                # ~ label=_('Group'), help_text='',
                # ~ queryset=groups, required=False,
                # ~ widget=FilterFormWidget(
                    # ~ attrs={'class': 'select2-tags'}, queryset=groups,selected=selected
                # ~ )
            # ~ )
        # ~ if departments:
            # ~ if initials.get('departments'):
                # ~ selected = Department.objects.filter(id__in=initials.get('departments'))
            # ~ else:
                # ~ selected = User.objects.none()
            # ~ self.fields['departments'] = forms.ModelMultipleChoiceField(
                # ~ label=_('Departments'), help_text='',
                # ~ queryset=departments, required=False,
                # ~ widget=FilterFormWidget(
                    # ~ attrs={'class': 'select2-tags'}, queryset=departments,selected=selected
                # ~ )
            # ~ )
        # ~ self.fields['checklist'] = forms.BooleanField(label="Has checklist",required = False)
        # ~ if initials.get('checklist'):
            # ~ self.fields['checklist'].widget.attrs.update(
                # ~ {'checked': True}
            # ~ )
        # ~ self.fields['status_report'] = forms.BooleanField(label="Has status report",required = False)
        # ~ if initials.get('status_report'):
            # ~ self.fields['status_report'].widget.attrs.update(
                # ~ {'checked': True}
            # ~ )
        # ~ self.fields['documents_check'] = forms.BooleanField(label="", required = False)
        # ~ if initials.get('documents_check'):
            # ~ self.fields['documents_check'].widget.attrs.update(
                # ~ {'checked': True}
            # ~ )

        # ~ if initials.get('documents'):
            # ~ value = initials.get('documents')
        # ~ else:
            # ~ value = 50
        # ~ self.fields['documents'] = forms.IntegerField(required=False,
            # ~ label=_('Documents'),
            # ~ min_value=0,
            # ~ max_value=100,
            # ~ widget=RangeInput(attrs={"max": 100, "id" : "myRange", "value": value })
        # ~ )



class TrackedFileForm(forms.Form):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        obj = kwargs.pop('instance', None)
        obj = kwargs.pop('obj', None)
        request_url = kwargs.pop('request_url', None)
        can_edit = True
        super(TrackedFileForm, self).__init__(*args, **kwargs)
        self.fields['retain_or_transfer'] = forms.ChoiceField(
            label='Retain file or transfer required?', choices=TrackedFile.ACTION_CHOICES, required = False
        )
        self.fields['closure_letter'] = DateField(
            label='Date of closure letter to client', required=False,
          )
        self.fields['instructions'] = DateField(
            label='Instructions received regarding file transfer', required=False
        )
        clients = Client.objects.all()
        self.fields['client'] = forms.ModelMultipleChoiceField(
                label='Client', help_text='',
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
        self.fields['completion'] = DateField(
            label='Date of completion of transfer process', required=False
        )
        if obj:
            self.fields['retain_or_transfer'].initial = obj.retain_or_transfer
            self.fields['closure_letter'].initial = obj.get_date(obj.closure_letter,no=False)
            self.fields['instructions'].initial = obj.get_date(obj.instructions,no=False)
            self.fields['client'].initial = obj.client
            self.fields['notice'].initial = obj.get_date(obj.notice,no=False)
            self.fields['receipt'].initial = obj.get_date(obj.receipt,no=False)
            self.fields['completion'].initial = obj.get_date(obj.completion,no=False)

class ClosureLetterEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance',None)
        super(ClosureLetterEditForm, self).__init__(*args, **kwargs)
        self.fields['closure_letter'] = DateField(
            label='Date of closure letter to client', required=False,
          )

class InstructionsEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance',None)
        super(InstructionsEditForm, self).__init__(*args, **kwargs)
        self.fields['instructions'] = DateField(
            label='Date instructions received regarding file transfer', required=False,
          )

class ClientEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance',None)
        super(ClientEditForm, self).__init__(*args, **kwargs)
        clients = Client.objects.all()
        self.fields['client'] = forms.ModelMultipleChoiceField(
                label='File to new lawyer or client', help_text='',
                queryset=clients, required=False,
                widget=FilterFormWidget(
                    attrs={'class': 'select2-tags'}, queryset=clients
                )
        )

class NoticeEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance',None)
        super(NoticeEditForm, self).__init__(*args, **kwargs)
        self.fields['notice'] = DateField(
            label='Date of notice of change of legal practitioners', required=False,
          )

class ReceiptEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance',None)
        super(ReceiptEditForm, self).__init__(*args, **kwargs)
        self.fields['receipt'] = DateField(
            label='Date of receipt of file acknowledgement', required=False,
          )

class CompletionEditForm(forms.Form):

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance',None)
        super(CompletionEditForm, self).__init__(*args, **kwargs)
        self.fields['completion'] = DateField(
            label='Date of completion of transfer process', required=False,
          )
