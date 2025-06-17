from __future__ import absolute_import, unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from acls.models import AccessControlList

from .models import Role
from .permissions import permission_role_view
from .widgets import RoleFormWidget, RoleSelectWidget

import logging
logger = logging.getLogger(__name__)

from django.utils.safestring import mark_safe

class RoleMultipleSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        help_text = kwargs.pop('help_text', None)
        choices = kwargs.pop('choices', None)
        permission = kwargs.pop('permission', permission_role_view)
        user = kwargs.pop('user', None)
        current_roles = kwargs.pop('current_roles', None)
        queryset = kwargs.pop('queryset', Role.objects.all().exclude(label=user.first_name+" "+user.last_name))
        
        super(RoleMultipleSelectionForm, self).__init__(*args, **kwargs)

        queryset = AccessControlList.objects.filter_by_access(
            permission=permission, queryset=queryset, user=user
        )
        lawyers = Role.objects.filter(role_type='Lawyer').exclude(label=user.first_name+" "+user.last_name)
        groups = Role.objects.filter(role_type='Group').exclude(label=user.first_name+" "+user.last_name)
        other = Role.objects.filter(role_type='Other').exclude(label=user.first_name+" "+user.last_name)      
   
        
        for role in groups:
            members = []
            for g in role.groups.iterator():
                members.append(g.name)
            
            if len(members) == 0:
                members.append('')
                            
            self.fields[str(role.id)] = forms.ChoiceField(choices=choices, required = False, 
                widget= RoleSelectWidget(choices=choices, attrs={'name': str(role),'role_id':role.id,
                    'members':members,'style': "width:120px;height:40px;",})) 
            self.fields[str(role.id)].group = 'Groups:'
                        
        for role in lawyers:
            self.fields[str(role.id)] = forms.ChoiceField(choices=choices, required = False, 
                widget= RoleSelectWidget(choices=choices, attrs={'name': str(role),'role_id':role.id,
                    'style': "width:120px;height:40px;",})) 
            self.fields[str(role.id)].group = 'Lawyers:'

        for role in other:
            self.fields[str(role.id)] = forms.ChoiceField(choices=choices, required = False, 
                widget= RoleSelectWidget(choices=choices, attrs={'name': str(role),'role_id':role.id,
                    'style': "width:120px;height:40px;",})) 
            self.fields[str(role.id)].group = ''

                        
                
                
                

        
    

    
