from __future__ import unicode_literals

from furl import furl
import logging
from ast import literal_eval

from django.apps import apps
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType


from django.contrib.auth.models import User





from sources.wizards import WizardStep

from .forms import RoleMultipleSelectionForm
from acls.models import AccessControlList


from documents.events import event_document_shared

logger = logging.getLogger(__name__)

class WizardStepRoles(WizardStep):
    form_class = RoleMultipleSelectionForm
    label = _('Share document with other users or groups')
    name = 'role_selection'
    number = 4

    @classmethod
    def condition(cls, wizard):
        Role = apps.get_model(app_label='permissions', model_name='Role')
        return Role.objects.exists()

    @classmethod
    def get_form_kwargs(self, wizard):
        return {
            'help_text': _(''),
            'user': wizard.request.user,
            'choices': [("0", "No"), ("1", "Read Only"),("2", "Full")],
        }
    
        
    @classmethod
    def done(cls, wizard):
        result = {}
        cleaned_data = wizard.get_cleaned_data_for_step(cls.name)
        cls.user = wizard.request.user
        if cleaned_data:
            result['roles'] = []
            for key, value in cleaned_data.iteritems():
                if value == '1' or value == '2':
                    result['roles'].append((force_text(key),value))
        return result

    @classmethod
    def step_post_upload_process(cls, document, querystring=None):
        
        furl_instance = furl(querystring)
        Role = apps.get_model(app_label='permissions', model_name='Role')
        role_list = furl_instance.args.getlist('roles')
        for item in role_list:
            role = Role.objects.get(pk = literal_eval(item)[0])                 

            acl = AccessControlList.objects.create(
               object_id=document.pk,content_type=ContentType.objects.get_for_model(document), role=role
            )  
            if literal_eval(item)[1] == '2':
                acl.add_full_doc_permissions() 
            elif literal_eval(item)[1] == '1':
                acl.add_doc_permissions() 
            else:
                continue
                
        event_document_shared.commit(
            actor=cls.user, target=document, action_object=document.document_type
        )

            


WizardStep.register(WizardStepRoles)
