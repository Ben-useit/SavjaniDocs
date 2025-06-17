from __future__ import absolute_import, unicode_literals
from dal import autocomplete
from dal_select2.widgets import ModelSelect2
from django import forms
from django.core.exceptions import ValidationError
from django.forms.formsets import formset_factory
from django.utils.translation import ugettext_lazy as _

from acls.models import AccessControlList
from documents.models import DocumentType
from permissions.models import Role
from checklist.forms import XDSoftDateTimePickerInput, XDSoftDateTimePickerInput2

from .utils import get_str_from_aware
from .widgets import RoleFormWidget, ListTextWidget #, DateSelectionWidget,

__all__ = ('DocumentTypeSelectForm',)

from django.utils.safestring import mark_safe

from mayan.apps.sapitwa.widgets import DateSelectionWidget


class DocumentStatisticForm(forms.Form):
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super(DocumentStatisticForm, self).__init__(*args, **kwargs)
        self.fields['week'] = forms.CharField(widget = XDSoftDateTimePickerInput(), required=False, help_text='To select a week, just select a day within that week')
        self.fields['month'] = forms.CharField(widget = XDSoftDateTimePickerInput(), required=False,help_text='To select a month, just select a day within that month')
        self.fields['from'] = forms.CharField(widget = XDSoftDateTimePickerInput(), required=False, help_text='Only recognized, if no week or month has been selected')
        self.fields['to'] = forms.CharField(widget = XDSoftDateTimePickerInput(), required=False, help_text='Only recognized, if no week or month has been selected. Leave emtpy for current day.')


class ShareEditForm(forms.Form):
    CHOICES = [('full','Full Access'),('limited','Limited Access'),('none','No Access')]
    permission =forms.ChoiceField(widget=forms.RadioSelect,choices=CHOICES,required=False)

class RoleMultipleSelectionForm(forms.Form):

    class Media:
        js = ('sapitwa/js/sapitwa_form.js',)

    def __init__(self, *args, **kwargs):
        help_text = kwargs.pop('help_text', None)
        user_role = kwargs.pop('user_role', None)
        queryset = kwargs.pop('roles', None)
        extra_kwargs = {}
        if not queryset:
            queryset = Role.objects.all()
        if user_role:
            queryset = queryset.exclude(pk=user_role.pk)
        super(RoleMultipleSelectionForm, self).__init__(*args, **kwargs)
        self.fields['read_write_access'] = forms.ModelMultipleChoiceField(
            help_text=help_text, label="Full Access",
            queryset=queryset, required=False,
            widget=RoleFormWidget(attrs={'class': 'select2-tags','background':'#555'}),
            **extra_kwargs
        )
        self.fields['read_only_access'] = forms.ModelMultipleChoiceField(
            help_text=help_text, label="Read Only Access",
            queryset=queryset, required=False,
            widget=RoleFormWidget(attrs={'class': 'select2-tags'}),
            **extra_kwargs
        )

from os.path import splitext
from .widgets import DateTimeSelectionWidget
from register.models import Register, Quotation
from register.permissions import permission_register_view
from .widgets import RegListWidget
from .models import ListOptions
'''
Overwrite clean function to accept empty values and convert the given value 
into a tuple.
'''
class ModelMultipleChoiceField(forms.models.ModelMultipleChoiceField):
    def clean(self, value):
        if not value:
            return self.queryset.none()
        else:
            value = (value,value)
        return super(ModelMultipleChoiceField,self).clean(value)

from cabinets.models import Cabinet
class DocumentTypeSelectForm(forms.Form):
    def __init__(self, *args, **kwargs):
        email = kwargs.pop('email', None)
        user = kwargs.pop('user', None)
        document = kwargs.pop('document', None)
        email_info = kwargs.pop('email_info', None)
        email_subject = kwargs.pop('email_subject', None)
        permission = kwargs.pop('permission', None)
        user_role = kwargs.pop('user_role', None)
        file_timestamps = kwargs.pop('file_timestamps', None)
        last_modified = kwargs.pop('last_modified', None)
        last_modified = get_str_from_aware(last_modified)
        initial_register_file = None

        if not email_info:
            super(DocumentTypeSelectForm, self).__init__(*args, **kwargs)
            queryset = AccessControlList.objects.restrict_queryset(
                permission=permission, queryset=DocumentType.objects.all().exclude(label='Temp__Upload'), user=user
            )
        else:
            super(DocumentTypeSelectForm, self).__init__(*args, **kwargs)
        #Label and last modified only for a single document
        if not email_info and not file_timestamps:
            if document:
                file_name,extension = splitext(document.label)
                self.fields['label'] = forms.CharField(initial = file_name, max_length=200)
                self.fields['extension'] = forms.CharField(initial=extension, widget = forms.HiddenInput(), required = False)
                self.fields['last_modified'] = forms.CharField(initial=last_modified, widget = XDSoftDateTimePickerInput2())
                self.fields['last_modified'].widget.attrs.update(
                        {'readonly': True}
                )
                initial_register_file = file_name
            self.fields['document_type'] = forms.ModelChoiceField(
                empty_label=None, label=_('Document type'), queryset=queryset,
                required=True, widget=forms.widgets.Select(attrs={'size': 4})
            )
        #A zip file
        elif file_timestamps:
            if not email_info:
                self.fields['document_type'] = forms.ModelChoiceField(
                    empty_label=None, label=_('Document type'), queryset=queryset,
                    required=True, widget=forms.widgets.Select(attrs={'size': 4})
                )
            else:
                self.fields['document_type'] = forms.ModelChoiceField(
                    empty_label=None, label=_('Document type'), queryset=DocumentType.objects.filter(label='Email'),
                    required=False, widget=forms.widgets.Select(attrs={'size': 1,'readonly': True})
                )
        if not initial_register_file:
            initial_register_file = email_subject
        register_files = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=user, queryset=Register.objects.all())
        help_text = """
        If a suitable file is not in this list, request one using Register > Create new register file.<br />
        """

        field = ModelMultipleChoiceField(
            label=_('Register File'),required=False,
            queryset = register_files,
            help_text = help_text
        )
        widget = ModelSelect2(
                url ='sapitwa:register_file_autocomplete',
                #attrs={"class": "selector", "data-placeholder": "Select a register file"}
        )
        
        widget.choices = forms.models.ModelChoiceIterator(field)   
        field.widget = widget
        self.fields['register_file'] = field 
        if initial_register_file:
            for r in register_files:
                if r.file_no in initial_register_file:
                    self.fields['register_file'].initial = r
                    break
                if r._file_no_bak and r._file_no_bak in initial_register_file:
                    self.fields['register_file'].initial = r
                    break

        help_text = """
        Use either a Register File <b>OR</b> a Quotation File )
        """
        quotation_files = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=user, queryset=Quotation.objects.all())
        
        field = ModelMultipleChoiceField(
            label=_('Quotation File'),required=False,
            queryset = quotation_files,
            help_text = help_text
        )
        widget = ModelSelect2(
                url ='sapitwa:quotation_file_autocomplete',
                attrs={"class": "selector", "data-placeholder": "Select a quotation file"}
        )
        widget.choices = forms.models.ModelChoiceIterator(field)
        field.widget = widget
        self.fields['quotation_file'] = field 
        
        #------------------
        queryset = Cabinet.objects.all()
        field = forms.ModelMultipleChoiceField(
            label=_('Cabinets'), help_text='Option: Select a folder',
            queryset=queryset, required=False,
            widget=forms.SelectMultiple(attrs={'class': 'select2'})
        )
        self.fields['cabinet'] = field 

class DocumentMetadataSelectForm(forms.Form):
    id = forms.CharField(label=_('ID'), widget=forms.HiddenInput)

    name = forms.CharField(
        label=_('Name'), required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly','style':'width:150px;'})
    )
    value = forms.CharField(
        label=_('Value'), required=False, widget=forms.TextInput(
            attrs={'class': 'metadata-value'}
        )
    )
    required = forms.CharField(label=_('Required'),disabled=True, required=False, widget=forms.HiddenInput)

    class Media:
        js = ('metadata/js/metadata_form.js',)

    def __init__(self, *args, **kwargs):
        super(DocumentMetadataSelectForm, self).__init__(*args, **kwargs)

        # Set form fields initial values
        if 'initial' in kwargs:
            self.metadata_type = kwargs['initial']['metadata_type']
            self.document_type = kwargs['initial']['document_type']
            required_string = ''

            required = self.metadata_type.get_required_for(
                document_type=self.document_type
            )

            if required:
                self.fields['value'].required = True
                self.fields['value'].help_text = "Required"
                #required_string = ' (%s)' % _('Required')
                #self.fields['update'].initial = True
                self.fields['required'].widget=forms.TextInput(attrs={'value':'Required','readonly': 'readonly'})
            else:
                self.fields['value'].required = False
                #self.fields['update'].initial = False

            self.fields['name'].initial = '%s%s' % (
                (
                    self.metadata_type.label if self.metadata_type.label else self.metadata_type.name
                ),
                required_string
            )
            self.fields['id'].initial = self.metadata_type.pk

            if self.metadata_type.lookup:
                try:
                    self.fields['value'] = forms.ChoiceField(
                        label=self.fields['value'].label
                    )
                    choices = self.metadata_type.get_lookup_values()
                    choices = list(zip(choices, choices))
                    if not required:
                        choices.insert(0, ('', '------'))
                    self.fields['value'].choices = choices
                    self.fields['value'].required = required
                    self.fields['value'].widget.attrs.update(
                        {'class': 'metadata-value'}
                    )
                except Exception as exception:
                    self.fields['value'].initial = _(
                        'Lookup value error: %s'
                    ) % exception
                    self.fields['value'].widget = forms.TextInput(
                        attrs={'readonly': 'readonly'}
                    )
            if self.metadata_type.validation == 'metadata.validators.DateAndTimeValidator':
                #initial = get_str_from_aware(str(self.metadata_type.default),if_error_now = False)
                initial = self.metadata_type.default
                #initial = ''
                self.fields['value'] = forms.CharField(initial=initial, widget = XDSoftDateTimePickerInput2)
                self.fields['value'].required = required
                self.fields['value'].widget.attrs.update(
                    {'class': 'metadata-value', 'readonly': 'readonly'}
                )
            elif self.metadata_type.default:
                try:
                    self.fields[
                        'value'
                    ].initial = self.metadata_type.get_default_value()
                except Exception as exception:
                    self.fields['value'].initial = _(
                        'Default value error: %s'
                    ) % exception
                    self.fields['value'].widget = forms.TextInput(
                        attrs={'readonly': 'readonly'}
                    )

    def clean(self):
        metadata_type = getattr(self, 'metadata_type', None)

        if metadata_type:
            required = self.metadata_type.get_required_for(
                document_type=self.document_type
            )
            if required and self.cleaned_data.get('value') == '': #self.cleaned_data.get('update'):
                raise ValidationError(
                    _(
                        '"%s" is required for this document type.'
                    ) % self.metadata_type.label
                )

        if self.cleaned_data.get('value') != '' and hasattr(self, 'metadata_type'):
            self.cleaned_data['value'] = self.metadata_type.validate_value(
                document_type=self.document_type,
                value=self.cleaned_data.get('value')
            )

        return self.cleaned_data
DocumentMetadataFormSet = formset_factory(DocumentMetadataSelectForm, extra=0)

class FormOptions(object):
    def __init__(self, form, kwargs, options=None):
        """
        Option definitions will be iterated. The option value will be
        determined in the following order: as passed via keyword
        arguments during form intialization, as form get_... method or
        finally as static Meta options. This is to allow a form with
        Meta options or method to be overridden at initialization
        and increase the usability of a single class.
        """
        for name, default_value in self.option_definitions.items():
            try:
                # Check for a runtime value via kwargs
                value = kwargs.pop(name)
            except KeyError:
                try:
                    # Check if there is a get_... method
                    value = getattr(self, 'get_{}'.format(name))()
                except AttributeError:
                    try:
                        # Check the meta class options
                        value = getattr(options, name)
                    except AttributeError:
                        value = default_value

            setattr(self, name, value)

class FilteredSelectionFormOptions(FormOptions):
    # Dictionary list of option names and default values
    option_definitions = {
        'allow_multiple': False,
        'field_name': None,
        'help_text': None,
        'label': None,
        'model': None,
        'permission': None,
        'queryset': None,
        'required': True,
        'user': None,
        'widget_class': None,
        'widget_attributes': {'size': '10'},
    }

class FilteredSelectionForm(forms.Form):
    """
    Form to select the from a list of choice filtered by access. Can be
    configure to allow single or multiple selection.
    """
    def __init__(self, *args, **kwargs):
        opts = FilteredSelectionFormOptions(
            form=self, kwargs=kwargs, options=getattr(self, 'Meta', None)
        )

        if opts.queryset is None:
            if not opts.model:
                raise ImproperlyConfigured(
                    '{} requires a queryset or a model to be specified as '
                    'a meta option or passed during initialization.'.format(
                        self.__class__.__name__
                    )
                )

            queryset = opts.model.objects.all()
        else:
            queryset = opts.queryset

        if opts.allow_multiple:
            extra_kwargs = {}
            field_class = forms.ModelMultipleChoiceField
            widget_class = forms.widgets.SelectMultiple
        else:
            extra_kwargs = {'empty_label': None}
            field_class = forms.ModelChoiceField
            widget_class = forms.widgets.Select

        if opts.widget_class:
            widget_class = opts.widget_class

        if opts.permission:
            queryset = AccessControlList.objects.restrict_queryset(
                permission=opts.permission, queryset=queryset,
                user=opts.user
            )

        super(FilteredSelectionForm, self).__init__(*args, **kwargs)

        self.fields[opts.field_name] = field_class(
            help_text=opts.help_text, label=opts.label,
            queryset=queryset, required=opts.required,
            widget=widget_class(attrs=opts.widget_attributes),
            **extra_kwargs
        )

from .widgets import TagFormWidget
#from common.forms import FilteredSelectionForm
class TagMultipleSelectionForm(FilteredSelectionForm):
    class Media:
        js = ('tags/js/tags_form.js',)

    class Meta:
        allow_multiple = True
        field_name = 'tags'
        label = _('Tags')
        required = False
        widget_class = TagFormWidget
        widget_attributes = {'class': 'select2-tags'}
