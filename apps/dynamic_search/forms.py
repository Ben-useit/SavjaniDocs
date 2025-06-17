from __future__ import unicode_literals
import logging
from django import forms
from django.utils.translation import ugettext_lazy as _
from documents.models import DocumentType
from metadata.models import MetadataType
from tags.models import Tag

from metadata.models import DocumentMetadata

logger = logging.getLogger(__name__)

class AdvancedSearchForm(forms.Form):
    _match_all = forms.BooleanField(
        label=_('Match all'), help_text=_(
            'When checked, only results that match all fields will be '
            'returned. When unchecked results that match at least one field '
            'will be returned.'
        ), required=False
    )

    def __init__(self, *args, **kwargs):
        self.search_model = kwargs.pop('search_model')
        super(AdvancedSearchForm, self).__init__(*args, **kwargs)
        document_types = DocumentType.objects.all()
        document_type_choices = [('','')]
        for dt in document_types:
            document_type_choices.append((str(dt),dt))
            
        tags = Tag.objects.all()
        tags_choices = [('','')]
        for t in tags:
            tags_choices.append((str(t),t))     
               
        metadata_types = MetadataType.objects.all()
        metadata_types_choices = [('','')]
        for m in metadata_types:
            metadata_types_choices.append((str(m),m)) 
                         
        for name, label in self.search_model.get_fields_simple_list():
            if name == 'document_type__label' or name == 'document_version__document__document_type__label' :
                self.fields[name] = forms.ChoiceField(
                    label = label,
                    choices=document_type_choices,
                    required = False,
                    widget = forms.Select(
                     attrs={ 'class': 'select' }
                    ))
            elif name == 'tags__label' or name == 'document_version__document__tags__label':
                self.fields[name] = forms.ChoiceField(
                    label = label,
                    choices=tags_choices,
                    required = False,
                    widget = forms.Select(
                     attrs={ 'class': 'select' }
                    ))                
            elif name == 'metadata__metadata_type__name' or name == 'document_version__document__metadata__metadata_type__name':
                self.fields[name] = forms.ChoiceField(
                    label = label,
                    choices=metadata_types_choices,
                    required = False,
                    widget = forms.Select(
                     attrs={ 'class': 'select' }
                    ))                
            elif name == 'ocr_content__content' or name == 'versions__pages__ocr_content__content':
                self.fields[name] = forms.CharField(required = False,widget=forms.HiddenInput())
                
            else:
                self.fields[name] = forms.CharField(
                    label=label,
                    required=False
                )

class SearchForm(forms.Form):
    q = forms.CharField(
        max_length=128, label=_('Search terms'), required=False
    )

class MySearch(forms.Form):

    def  __init__(self, *args, **kwargs):
        metas = kwargs.pop('metas', 0)
        register = kwargs.pop('register', 0)
        super(MySearch,self).__init__(*args,**kwargs)
        for k,v in metas.items():
            choices = [(0,'---')]
            for i in  v:
                choices.append((i,i))
            self.fields[str(k)] = forms.ChoiceField(label = k.label, choices = choices , required = False,
                widget = forms.Select(attrs={'style' :"width:300px;" }))

        for k,v in register.items():
            choices = [(0,'---')]
            for i in  v:
                choices.append((i,i))
            self.fields[str(k)] = forms.ChoiceField(label = k, choices = choices , required = False,
                widget = forms.Select(attrs={'style' :"width:300px;" }))
            
    class Meta:
        model = DocumentMetadata
        exclude = ('document',)
