from __future__ import absolute_import, unicode_literals

import logging
import os

from os.path import splitext

from django import forms
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from acls.models import AccessControlList
from common.forms import DetailForm
from common.utils import get_str_from_aware
from register.models import Register
from register.permissions import permission_register_view

from .fields import (
    DocumentField, DocumentPageField, DocumentVersionField
)
from .models import (
    Document, DocumentType, DocumentTypeFilename
)
from metadata.widgets import ListTextWidget
from .literals import DEFAULT_ZIP_FILENAME, PAGE_RANGE_ALL, PAGE_RANGE_CHOICES
from .permissions import permission_document_create
from .runtime import language_choices
from .widgets import LastModifiedWidget

logger = logging.getLogger(__name__)

# Document page forms


class DocumentPageForm(forms.Form):
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        rotation = kwargs.pop('rotation', None)
        zoom = kwargs.pop('zoom', None)
        super(DocumentPageForm, self).__init__(*args, **kwargs)
        self.fields['document_page'].initial = instance
        self.fields['document_page'].widget.attrs.update({
            'zoom': zoom,
            'rotation': rotation,
        })

    document_page = DocumentPageField()


# Document forms
class DocumentPreviewForm(forms.Form):
    def __init__(self, *args, **kwargs):
        document = kwargs.pop('instance', None)
        super(DocumentPreviewForm, self).__init__(*args, **kwargs)
        self.fields['document'].initial = document

    document = DocumentField()


class DocumentVersionPreviewForm(forms.Form):
    def __init__(self, *args, **kwargs):
        document_version = kwargs.pop('instance', None)
        super(DocumentVersionPreviewForm, self).__init__(*args, **kwargs)
        self.fields['document_version'].initial = document_version

    document_version = DocumentVersionField()


class DocumentForm(forms.ModelForm):
    """
    Form sub classes from DocumentForm used only when editing a document
    """
    class Meta:
        fields = ('label', 'description', 'language')
        model = Document
        widgets = {
            'language': forms.Select(
                choices=language_choices, attrs={
                    'class': 'select2'
                }
            )

        }

    def __init__(self, *args, **kwargs):
        document = kwargs.get('instance', None)
        if document:
            file_name,extension = splitext(document.label)
            #-self.extension = extension
            initial = kwargs.get('initial', {})
            initial['label'] = file_name
            kwargs['initial'] = initial            
        document_type = kwargs.pop('document_type', None)
        super(DocumentForm, self).__init__(*args, **kwargs)


        # Is a document (documents app edit) and has been saved (sources
        # app upload)?
        if self.instance and self.instance.pk:
            document_type = self.instance.document_type

        filenames_queryset = document_type.filenames.filter(enabled=True)

        if filenames_queryset:
            self.fields[
                'document_type_available_filenames'
            ] = forms.ModelChoiceField(
                queryset=filenames_queryset,
                required=False,
                label=_('Quick document rename'),
                widget=forms.Select(
                    attrs={
                        'class': 'select2'
                    }
                )
            )
            self.fields['preserve_extension'] = forms.BooleanField(
                label=_('Preserve extension'), required=False,
                help_text=_(
                    'Takes the file extension and moves it to the end of the '
                    'filename allowing operating systems that rely on file '
                    'extensions to open document correctly.'
                )
            )

    def clean(self):
        self.cleaned_data['label'] = self.get_final_label(
            # Fallback to the instance label if there is no label key or
            # there is a label key and is an empty string
            filename=self.cleaned_data.get('label')#+self.extension or self.instance.label
        )

        return self.cleaned_data

    def get_final_label(self, filename):
        if 'document_type_available_filenames' in self.cleaned_data:
            if self.cleaned_data['document_type_available_filenames']:
                if self.cleaned_data['preserve_extension']:
                    filename, extension = os.path.splitext(filename)

                    filename = '{}{}'.format(
                        self.cleaned_data[
                            'document_type_available_filenames'
                        ].filename, extension
                    )
                else:
                    filename = self.cleaned_data[
                        'document_type_available_filenames'
                    ].filename

        return filename


class DocumentPropertiesForm(DetailForm):
    """
    Detail class form to display a document file based properties
    """
    def __init__(self, *args, **kwargs):
        document = kwargs['instance']

        extra_fields = [
            {
                'label': _('Date added'),
                'field': 'date_added',
                'widget': forms.widgets.DateTimeInput
            },         
            {'label': _('UUID'), 'field': 'uuid'},
            {
                'label': _('Language'),
                'field': lambda x: dict(language_choices).get(
                    document.language, _('Unknown')
                )
            },
        ]

        if document.latest_version:
            extra_fields += (           
                {
                    'label': _('File mimetype'),
                    'field': lambda x: document.file_mimetype or _('None')
                },
                {
                    'label': _('File encoding'),
                    'field': lambda x: document.file_mime_encoding or _(
                        'None'
                    )
                },
                {
                    'label': _('File size'),
                    'field': lambda document: filesizeformat(
                        document.size
                    ) if document.size else '-'
                },
                {'label': _('Exists in storage'), 'field': 'exists'},
                {
                    'label': _('File path in storage'),
                    'field': 'latest_version.file'
                },
                {'label': _('Checksum'), 'field': 'checksum'},
                {'label': _('Pages'), 'field': 'page_count'},
                {
                    'label': _('Last modified'),
                    'field': 'latest_version.timestamp',
                    'widget': forms.widgets.DateTimeInput
                }                
            )

        kwargs['extra_fields'] = extra_fields
        super(DocumentPropertiesForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ('document_type', 'description')
        model = Document


class DocumentTypeSelectForm(forms.Form):
    """
    Form to select the document type of a document to be created, used
    as form #1 in the document creation wizard
    """
    def __init__(self, *args, **kwargs):
        email = kwargs.pop('email', None)
        user = kwargs.pop('user', None)
        document = kwargs.pop('document_pk', None)
        if not email:

            if document:
                last_modified = get_str_from_aware(str(document.last_modified))

            super(DocumentTypeSelectForm, self).__init__(*args, **kwargs)

            queryset = AccessControlList.objects.filter_by_access(
                permission_document_create, user,
                queryset=DocumentType.objects.all().exclude(label="Temp__Upload")
            )
            if document:
                file_name,extension = splitext(document.label)
                self.fields['label'] = forms.CharField(initial = file_name, max_length=200)
                self.fields['extension'] = forms.CharField(initial=extension, widget = forms.HiddenInput(), required = False)
                self.fields['last_modified'] = forms.CharField(initial=last_modified, widget = LastModifiedWidget())
                self.fields['last_modified'].widget.attrs.update(
                        {'readonly': True}
                )
        else:
            super(DocumentTypeSelectForm, self).__init__(*args, **kwargs)
        
        self.entries = Register.objects.all().exclude(file_no__startswith="TEMP__").order_by('opened').reverse()
        self.entries = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=user, queryset=self.entries)
        reg_list = ['']
        help_text = """
Select a File No. from the list ( optional )</br>
If a suitable file no. is not in this list, request one using Register > Create new file no.<br />
The file no. replaces the matter no. that was attached as metadata in the past."""
        for r in self.entries:
            reg_list.append(r.file_no+' -  '+r.parties)
        self.fields['register_entry'] = forms.CharField(
            label=_('File No.'), required=False, help_text=help_text, widget=ListTextWidget(data_list=reg_list, name='metadata_list')
        )
        if not email:
            self.fields['document_type'] = forms.ModelChoiceField(
                empty_label=None, label=_('Document type'), queryset=queryset,
                required=True, widget=forms.widgets.Select(attrs={'size': 4})
            )

    def clean_register_entry(self):
        register_entry = self.cleaned_data['register_entry'].split('-')[0].strip()
        if register_entry and not Register.objects.filter(file_no=register_entry).exists():
            raise ValidationError("<"+register_entry+"> is not an entry from the list. Please select one from the list or leave it empty.")
        return register_entry

class DocumentTypeFilenameForm_create(forms.ModelForm):
    """
    Model class form to create a new document type filename
    """
    class Meta:
        fields = ('filename',)
        model = DocumentTypeFilename


class DocumentDownloadForm(forms.Form):
    compressed = forms.BooleanField(
        label=_('Compress'), required=False,
        help_text=_(
            'Download the document in the original format or in a compressed '
            'manner. This option is selectable only when downloading one '
            'document, for multiple documents, the bundle will always be '
            'downloads as a compressed file.'
        )
    )
    zip_filename = forms.CharField(
        initial=DEFAULT_ZIP_FILENAME, label=_('Compressed filename'),
        required=False,
        help_text=_(
            'The filename of the compressed file that will contain the '
            'documents to be downloaded, if the previous option is selected.'
        )
    )

    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.pop('queryset', None)
        super(DocumentDownloadForm, self).__init__(*args, **kwargs)
        if self.queryset.count() > 1:
            self.fields['compressed'].initial = True
            self.fields['compressed'].widget.attrs.update({'disabled': True})


class DocumentVersionDownloadForm(DocumentDownloadForm):
    preserve_extension = forms.BooleanField(
        label=_('Preserve extension'), required=False,
        help_text=_(
            'Takes the file extension and moves it to the end of the '
            'filename allowing operating systems that rely on file '
            'extensions to open the downloaded document version correctly.'
        )
    )


class DocumentPrintForm(forms.Form):
    page_group = forms.ChoiceField(
        choices=PAGE_RANGE_CHOICES, initial=PAGE_RANGE_ALL,
        widget=forms.RadioSelect
    )
    page_range = forms.CharField(label=_('Page range'), required=False)


class DocumentPageNumberForm(forms.Form):
    page = forms.ModelChoiceField(
        help_text=_(
            'Page number from which all the transformation will be cloned. '
            'Existing transformations will be lost.'
        ), queryset=None
    )

    def __init__(self, *args, **kwargs):
        self.document = kwargs.pop('document')
        super(DocumentPageNumberForm, self).__init__(*args, **kwargs)
        self.fields['page'].queryset = self.document.pages.all()
