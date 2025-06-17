from __future__ import absolute_import, unicode_literals
import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from acls.models import AccessControlList
from .permissions import permission_client_view

from .models import Contact, ClientA

from register.models import Register, Quotation, Client, Department

class ContactCreateForm(forms.ModelForm):

    class Meta:
        model = Contact
        fields = ['name', 'address', 'city','phone','email','client']

    def __init__(self, *args, **kwargs):
        # ~ print('init')
        # ~ instance = kwargs.pop('instance',None)
        # ~ print('instance', instance)
        # ~ queryset = Client.objects.all()
        # ~ print('qs: ', queryset )
        super(ContactCreateForm,self).__init__(*args, **kwargs)
        self.fields['client'].queryset = ClientA.objects.all()
        print('self.fields', self.fields)

        # ~ self.fields['file_no'] =  forms.CharField(label='File No',max_length=100,help_text='The file number. Last one used: ')
        # ~ self.fields['abcd'] = forms.ModelChoiceField(
                # ~ queryset=queryset,required=True,
                # ~ label=_('Client'),
                # ~ widget=forms.Select(
                    # ~ attrs={
                        # ~ 'class': 'select2'
                    # ~ }
                # ~ )
            # ~ )


