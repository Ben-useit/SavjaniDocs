from __future__ import unicode_literals
import logging
from furl import furl

from django.apps import apps
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import classonlymethod
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _

from formtools.wizard.views import SessionWizardView

from common.utils import get_aware_str_from_unaware

from documents.forms import DocumentTypeSelectForm
from documents.models import Document, DocumentType, DocumentVersion

from acls.models import AccessControlList
from acls.tasks import task_get_role_context
from acls.literals import get_help_text

from register.models import Register
from register.events import event_file_no_document_added

from .icons import icon_wizard_submit

logger = logging.getLogger(__name__)
class WizardStep(object):
    _registry = {}
    _deregistry = {}

    @classmethod
    def deregister(cls, step):
        cls._deregistry[step.name] = step

    @classmethod
    def deregister_all(cls):
        for step in cls.get_all():
            cls.deregister(step=step)

    @classmethod
    def done(cls, wizard):
        return {}

    @classmethod
    def get(cls, name):
        for step in cls.get_all():
            if name == step.name:
                return step

    @classmethod
    def get_all(cls):
        return sorted(
            [
                step for step in cls._registry.values() if step.name not in cls._deregistry
            ], key=lambda x: x.number
        )

    @classmethod
    def get_choices(cls, attribute_name):
        return [
            (step.name, getattr(step, attribute_name)) for step in cls.get_all()
        ]

    @classmethod
    def get_form_initial(cls, wizard):
        return {}

    @classmethod
    def get_form_kwargs(cls, wizard):
        return {}

    @classmethod
    def post_upload_process(cls, document, querystring=None):
        for step in cls.get_all():
            step.step_post_upload_process(
                document=document, querystring=querystring
            )

    @classmethod
    def register(cls, step):
        if step.name in cls._registry:
            raise Exception('A step with this name already exists: %s' % step.name)

        if step.number in [reigstered_step.number for reigstered_step in cls.get_all()]:
            raise Exception('A step with this number already exists: %s' % step.name)

        cls._registry[step.name] = step

    @classmethod
    def reregister(cls, name):
        cls._deregistry.pop(name)

    @classmethod
    def reregister_all(cls):
        cls._deregistry = {}

    @classmethod
    def step_post_upload_process(cls, document, querystring=None):
        pass


class WizardStepDocumentType(WizardStep):
    form_class = DocumentTypeSelectForm
    label = _('Select document type')
    name = 'document_type_selection'
    number = 0

    @classmethod
    def condition(cls, wizard):
        if str(wizard.__class__.__name__) == 'EmailFinalizeWizard':
            cls.label = _('Choose a file no.')
        return True

    @classmethod
    def done(cls, wizard):
        cleaned_data = wizard.get_cleaned_data_for_step(cls.name)
        if cleaned_data:
            #convert last_modified first
            user = wizard.request.user
            if 'last_modified' in cleaned_data:
                last_modified = get_aware_str_from_unaware(cleaned_data['last_modified'])
            else:
                last_modified = None

            if 'label' in cleaned_data:
                label = cleaned_data['label']+cleaned_data['extension']
            else:
                label = None

            if 'register_entry' in cleaned_data:
                register_entry = cleaned_data['register_entry']

            if 'document_type' in cleaned_data:
                document_type = cleaned_data['document_type'].pk
            else:
                document_type = None
            

                        
            return {
                'document_type_id': document_type,
                'last_modified': last_modified,
                'label': label,
                'register_entry' : register_entry
            }

    @classmethod
    def get_form_kwargs(cls, wizard):
        email = False
        if str(wizard.__class__.__name__) == 'EmailFinalizeWizard':
            email = True
        return {'user': wizard.request.user, 'document_pk':wizard.document, 'email': email}


WizardStep.register(WizardStepDocumentType)



class DocumentFinalizeWizard(SessionWizardView):
    template_name = 'appearance/generic_wizard.html'  

    @classonlymethod
    def as_view(cls, *args, **kwargs):
        cls.form_list = WizardStep.get_choices(attribute_name='form_class')
        cls.condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        return super(DocumentFinalizeWizard, cls).as_view(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user        
        if 'doc_id' not in kwargs or 'uuid' not in kwargs:
            return HttpResponseRedirect("/")
            
        if 'doc_id' not in kwargs or 'uuid' not in kwargs:
            return HttpResponseRedirect("/")
            
        doc_ids = [kwargs['doc_id']]
        if not user_has_permission(user=request.user,doc_ids=doc_ids):
            return HttpResponseRedirect("/")                
        if not documents_wizard_ready(doc_ids=doc_ids, document_type='Temp__Upload', uuid=kwargs['uuid']):
            return HttpResponseRedirect("/") 

               
        document = None
        try:
            document = Document.objects.get(pk=kwargs['doc_id'])
        except Document.DoesNotExist:
            return HttpResponseRedirect("/")
      
             
        InteractiveSource = apps.get_model(
            app_label='sources', model_name='InteractiveSource'
        )

        form_list = WizardStep.get_choices(attribute_name='form_class')
        condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        result = self.__class__.get_initkwargs(form_list=form_list, condition_dict=condition_dict)
        self.form_list = result['form_list']
        self.condition_dict = result['condition_dict']
        self.document = document

        if not InteractiveSource.objects.filter(enabled=True).exists():
            messages.error(
                request,
                _(
                    'No interactive document sources have been defined or '
                    'none have been enabled, create one before proceeding.'
                )
            )
            return HttpResponseRedirect(reverse('sources:setup_source_list'))
        self.role_context = task_get_role_context(request,self.document.id)
        return super(
            DocumentFinalizeWizard, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(
            DocumentFinalizeWizard, self
        ).get_context_data(form=form, **kwargs)
        wizard_step = WizardStep.get(name=self.steps.current)
        context.update({
            'step_title': _(
                'Step %(step)d of %(total_steps)d: %(step_label)s'
            ) % {
                'step': self.steps.step1, 'total_steps': 4, #len(self.form_list),
                'step_label': wizard_step.label,
            },
            'submit_label': _('Next step'),
            'submit_icon_class': icon_wizard_submit,
            'title': _('Document upload wizard'),
        })
        if self.steps.current == 'role_selection':
            context.update(self.role_context)
            context.update({'role_selection':True,'help_collapse': get_help_text(), }) 
        return context

    def get_form_initial(self, step):
        return WizardStep.get(name=step).get_form_initial(wizard=self) or {}

    def get_form_kwargs(self, step):
        return WizardStep.get(name=step).get_form_kwargs(wizard=self) or {}

    def done(self, form_list, **kwargs):
        user = kwargs.pop('user', None)
        query_dict = {}

        document = None
        try:
            document = Document.objects.get(pk=kwargs['doc_id'])
        except Document.DoesNotExist:
            return HttpResponseRedirect("/") 
            
        for step in WizardStep.get_all():
            query_dict.update(step.done(wizard=self) or {})

        url = '?'.join(
            [
                reverse('sources:upload_interactive'),
                urlencode(query_dict, doseq=True)
            ]
        )
        doc_type_id = query_dict.get('document_type_id')
        last_modified = query_dict.get('last_modified')
        dt = DocumentType.objects.get(pk=doc_type_id)
        document.label = query_dict.get('label')
        document.document_type = dt
        document.save()  
        
        register_entry = query_dict.get('register_entry')

        try:
            r = Register.objects.get(file_no=register_entry)
            r.documents.add(document)
            r.save()
            event_file_no_document_added.commit(
                actor=self.user, target=document, action_object=r
            )
        except Register.DoesNotExist:
            pass

        WizardStep.post_upload_process(
            document=document, querystring=url
        )
        document.is_stub = False;
        document.save(update_fields=["is_stub"]) 
        v = document.latest_version
        v.timestamp = last_modified
        v.save()
        return HttpResponseRedirect("documents/"+str(document.id)+"/preview") 

class DocumentsFinalizeWizard(SessionWizardView):
    template_name = 'appearance/generic_wizard.html'  

    @classonlymethod
    def as_view(cls, *args, **kwargs):
        cls.form_list = WizardStep.get_choices(attribute_name='form_class')
        cls.condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        return super(DocumentsFinalizeWizard, cls).as_view(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        
        if 'doc_id' not in kwargs or 'uuid' not in kwargs:
            return HttpResponseRedirect("/")
            
        doc_ids = kwargs['doc_id']
        doc_ids = doc_ids.split(',')
        if not user_has_permission(user=request.user,doc_ids=doc_ids):
            return HttpResponseRedirect("/")                
        if not documents_wizard_ready(doc_ids=doc_ids, document_type='Temp__Upload', uuid=kwargs['uuid']):
            return HttpResponseRedirect("/") 

        self.role_context = task_get_role_context(request,None)       
        InteractiveSource = apps.get_model(
            app_label='sources', model_name='InteractiveSource'
        )

        form_list = WizardStep.get_choices(attribute_name='form_class')
        condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        result = self.__class__.get_initkwargs(form_list=form_list, condition_dict=condition_dict)
        self.form_list = result['form_list']
        self.condition_dict = result['condition_dict']
        self.document = None

        if not InteractiveSource.objects.filter(enabled=True).exists():
            messages.error(
                request,
                _(
                    'No interactive document sources have been defined or '
                    'none have been enabled, create one before proceeding.'
                )
            )
            return HttpResponseRedirect(reverse('sources:setup_source_list'))

        return super(
            DocumentsFinalizeWizard, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(
            DocumentsFinalizeWizard, self
        ).get_context_data(form=form, **kwargs)
        wizard_step = WizardStep.get(name=self.steps.current)

        context.update({
            'step_title': _(
                'Step %(step)d of %(total_steps)d: %(step_label)s'
            ) % {
                'step': self.steps.step1, 'total_steps': len(self.form_list),
                'step_label': wizard_step.label,
            },
            'submit_label': _('Next step'),
            'submit_icon_class': icon_wizard_submit,
            'title': _('Document upload wizard'),
        })
        if self.steps.current == 'role_selection':
            context.update(self.role_context)
            context.update({'role_selection':True}) 
        return context

    def get_form_initial(self, step):
        return WizardStep.get(name=step).get_form_initial(wizard=self) or {}

    def get_form_kwargs(self, step):
        return WizardStep.get(name=step).get_form_kwargs(wizard=self) or {}

    def done(self, form_list, **kwargs):
        user = kwargs.pop('user', None)
        query_dict = {}
        doc_ids = pk=kwargs['doc_id']
        doc_ids = doc_ids.split(',')
        for doc_id in doc_ids:
            document = None
            try:
                document = Document.objects.get(pk=doc_id)
            except Document.DoesNotExist:
                return HttpResponseRedirect("/") 
                
            for step in WizardStep.get_all():
                query_dict.update(step.done(wizard=self) or {})

            url = '?'.join(
                [
                    reverse('sources:upload_interactive'),
                    urlencode(query_dict, doseq=True)
                ]
            )
            doc_type_id = query_dict.get('document_type_id')

            dt = DocumentType.objects.get(pk=doc_type_id)
            if query_dict.get('label'):
                document.label = query_dict.get('label')
            document.document_type = dt
            document.save()  
            
            WizardStep.post_upload_process(
                document=document, querystring=url
            )
            document.is_stub = False;
            document.save(update_fields=["is_stub"]) 
        return HttpResponseRedirect(reverse('documents:document_list_recent_added'))

class EmailFinalizeWizard(SessionWizardView):
    template_name = 'appearance/generic_wizard.html'  

    @classonlymethod
    def as_view(cls, *args, **kwargs):
        cls.form_list = WizardStep.get_choices(attribute_name='form_class')   
        cls.condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        return super(EmailFinalizeWizard, cls).as_view(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if 'doc_id' not in kwargs or 'uuid' not in kwargs:
            return HttpResponseRedirect("/")
            
        doc_ids = pk=kwargs['doc_id']
        doc_ids = doc_ids.split(',')
        self.user = request.user
        if not user_has_permission(user=request.user,doc_ids=doc_ids):
            return HttpResponseRedirect("/")
        if not documents_wizard_ready(doc_ids=doc_ids, document_type='Email', uuid=kwargs['uuid']):
            return HttpResponseRedirect("/")
        self.role_context = task_get_role_context(request,None)                 
        InteractiveSource = apps.get_model(
            app_label='sources', model_name='InteractiveSource'
        )

        form_list = WizardStep.get_choices(attribute_name='form_class')
        condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        result = self.__class__.get_initkwargs(form_list=form_list, condition_dict=condition_dict)
        self.form_list = result['form_list']
        self.condition_dict = result['condition_dict']
        self.document = None

        if not InteractiveSource.objects.filter(enabled=True).exists():
            messages.error(
                request,
                _(
                    'No interactive document sources have been defined or '
                    'none have been enabled, create one before proceeding.'
                )
            )
            return HttpResponseRedirect(reverse('sources:setup_source_list'))

        return super(
            EmailFinalizeWizard, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(
            EmailFinalizeWizard, self
        ).get_context_data(form=form, **kwargs)
        wizard_step = WizardStep.get(name=self.steps.current)

        context.update({
            'step_title': _(
                'Step %(step)d of %(total_steps)d: %(step_label)s'
            ) % {
                'step': self.steps.step1, 'total_steps': 4,
                'step_label': wizard_step.label,
            },
            'submit_label': _('Next step'),
            'submit_icon_class': icon_wizard_submit,
            'title': _('Email upload wizard'),
        })
        if self.steps.current == 'role_selection':
            context.update(self.role_context)
            context.update({'role_selection':True}) 
        return context

    def get_form_initial(self, step):
        return WizardStep.get(name=step).get_form_initial(wizard=self) or {}

    def get_form_kwargs(self, step):
        return WizardStep.get(name=step).get_form_kwargs(wizard=self) or {}

    def done(self, form_list, **kwargs):
        query_dict = {}
        doc_ids = pk=kwargs['doc_id']
        doc_ids = doc_ids.split(',')
        for doc_id in doc_ids:
            document = None
            try:
                document = Document.objects.get(pk=doc_id)
            except Document.DoesNotExist:
                return HttpResponseRedirect("/") 
                
            for step in WizardStep.get_all():
                query_dict.update(step.done(wizard=self) or {})
            url = '?'.join(
                [
                    reverse('sources:upload_interactive'),
                    urlencode(query_dict, doseq=True)
                ]
            )           
            WizardStep.post_upload_process(
                document=document, querystring=url
            )
            document.is_stub = False;
            document.save(update_fields=["is_stub"]) 
            register_entry = query_dict.get('register_entry')       

            try:
                r = Register.objects.get(file_no=register_entry)
                r.documents.add(document)
                r.save()
                event_file_no_document_added.commit(
                    actor=self.user, target=document, action_object=r
                )
            except Register.DoesNotExist:
                pass        
        return HttpResponseRedirect(reverse('documents:document_list_recent_added'))


class DocumentCreateWizard(SessionWizardView):
    template_name = 'appearance/generic_wizard.html'

    @classonlymethod
    def as_view(cls, *args, **kwargs):
        cls.form_list = WizardStep.get_choices(attribute_name='form_class')
        cls.condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        return super(DocumentCreateWizard, cls).as_view(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        InteractiveSource = apps.get_model(
            app_label='sources', model_name='InteractiveSource'
        )

        form_list = WizardStep.get_choices(attribute_name='form_class')
        condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))

        result = self.__class__.get_initkwargs(form_list=form_list, condition_dict=condition_dict)
        self.form_list = result['form_list']
        self.condition_dict = result['condition_dict']

        if not InteractiveSource.objects.filter(enabled=True).exists():
            messages.error(
                request,
                _(
                    'No interactive document sources have been defined or '
                    'none have been enabled, create one before proceeding.'
                )
            )
            return HttpResponseRedirect(reverse('sources:setup_source_list'))

        return super(
            DocumentCreateWizard, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(
            DocumentCreateWizard, self
        ).get_context_data(form=form, **kwargs)

        wizard_step = WizardStep.get(name=self.steps.current)

        context.update({
            'step_title': _(
                'Step %(step)d of %(total_steps)d: %(step_label)s'
            ) % {
                'step': self.steps.step1, 'total_steps': 4,
                'step_label': wizard_step.label,
            },
            'submit_label': _('Next step'),
            'submit_icon_class': icon_wizard_submit,
            'title': _('Document upload wizard'),
            'wizard_step': wizard_step,
            'wizard_steps': WizardStep.get_all(),
        })
        return context

    def get_form_initial(self, step):
        return WizardStep.get(name=step).get_form_initial(wizard=self) or {}

    def get_form_kwargs(self, step):
        return WizardStep.get(name=step).get_form_kwargs(wizard=self) or {}

    def done(self, form_list, **kwargs):
        query_dict = {}

        for step in WizardStep.get_all():
            query_dict.update(step.done(wizard=self) or {})

        url = furl(reverse('sources:upload_interactive'))
        # Use equal and not .update() to get the same result as using
        # urlencode(doseq=True)
        url.args = query_dict

        return HttpResponseRedirect(url)

def user_has_permission(doc_ids,user):
        if not user.is_superuser:
            Role = apps.get_model(
                app_label='permissions', model_name='Role'
            )
            role = None
            try:
                role = Role.objects.get(label=user.first_name+" "+user.last_name)
            except Role.DoesNotExist:
                return False
            else:
                acls = AccessControlList.objects.filter(role_id = role.id,object_id__in=doc_ids)
                if acls.count() != len(doc_ids):
                    return False
                else:
                    for acl in acls:
                        if not "Edit documents" in acl.get_permission_titles():
                            return False
        return True
    
def documents_wizard_ready(doc_ids, document_type, uuid):
    
    correct_UUID = False
    for doc_id in doc_ids:

        document = None
        try:
            document = Document.objects.get(pk=doc_id)
        except Document.DoesNotExist:
            return False
        if document.document_type.label != document_type:
            return False  
        #if not document.is_stub: 
        #    return False   

        if uuid == str(document.uuid):
            correct_UUID = True
    return correct_UUID
