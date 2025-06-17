from __future__ import unicode_literals
import logging
# ~ import time
import json
import datetime
from dateutil.parser import parse
from django.utils.dateformat import DateFormat
from furl import furl

from os.path import splitext
from formtools.wizard.views import SessionWizardView
from django.contrib import messages #??
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import classonlymethod
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text

from django.apps import apps
from acls.models import AccessControlList
#from common.http import URL
from documents.models import Document, DocumentType
from documents.permissions import permission_document_create #??
#from tags.forms import TagMultipleSelectionForm
from tags.models import Tag
from tags.permissions import permission_tag_attach #?
from sources.icons import icon_wizard_submit

from .forms import DocumentTypeSelectForm, DocumentMetadataFormSet, RoleMultipleSelectionForm, TagMultipleSelectionForm
from .models import TempDocument
from .utils import get_zip_info
from .tasks import task_post_upload_process

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
    def post_upload_process(cls, pending_document, querystring=None):
        for step in cls.get_all():
            step.step_post_upload_process(
                pending_document=pending_document, querystring=querystring
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
    def step_post_upload_process(cls, pending_document, querystring=None):
        pass

from common.utils import get_aware_str_from_unaware
class WizardStepDocumentType(WizardStep):
    form_class = DocumentTypeSelectForm
    label = _('Select document type')
    name = 'document_type_selection'
    number = 0

    @classmethod
    def condition(cls, wizard):
        return True

    @classmethod
    def done(cls, wizard):
        result = {}
        cleaned_data = wizard.get_cleaned_data_for_step(cls.name)
        if cleaned_data:
            wizard.temp_document.document_type = cleaned_data.get('document_type')
            if 'last_modified' in cleaned_data:
                date = cleaned_data['last_modified'].upper().replace("SEPT", "SEP")
                try:
                    last_modified = datetime.datetime.strptime(cleaned_data['last_modified'], "%d.%m.%Y %H:%M")
                    last_modified = timezone.make_aware(last_modified)
                except:
                    try:
                        last_modified = datetime.datetime.strptime(date, "%d. %B %Y, %H:%M")
                        last_modified = timezone.make_aware(last_modified)
                    except:
                        try:
                            last_modified = datetime.datetime.strptime(date, "%d. %b. %Y, %H:%M")
                            last_modified = timezone.make_aware(last_modified)
                        except:
                            last_modified =''

            else:
                last_modified = ''
            wizard.temp_document.last_modified = last_modified

            if 'label' in cleaned_data:
                label = cleaned_data['label']+cleaned_data['extension']
                wizard.temp_document.label = label
            if 'register_file' in cleaned_data:
                register_entry = cleaned_data['register_file']
                wizard.temp_document.register_file = register_entry.first()
            if 'quotation_file' in cleaned_data:
                quotation_file = cleaned_data['quotation_file']
                wizard.temp_document.quotation_file = quotation_file.first()
        return result

    @classmethod
    def get_form_kwargs(cls, wizard):
        return {
            'permission': permission_document_create,
            'user': wizard.request.user,
            'document':wizard.document,
            'email_info':wizard.email_info,
            'email_subject':wizard.email_subject,
            'file_timestamps':wizard.file_timestamps,
            'last_modified' : wizard.last_modified,
            'user_role' : wizard.role
        }

WizardStep.register(WizardStepDocumentType)

class DocumentWizard(SessionWizardView):
    template_name = 'appearance/generic_wizard.html'

    @classonlymethod
    def as_view(cls, *args, **kwargs):
        cls.form_list = WizardStep.get_choices(attribute_name='form_class')
        cls.condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        return super(DocumentWizard, cls).as_view(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.role = None
        if not request.user.is_superuser:
            try:
                self.role  = Role.objects.get(label=self.user.first_name+" "+self.user.last_name)
            except Role.DoesNotExist:
                return HttpResponseRedirect("/")

        doc_id =kwargs['doc_id']
        uuid = kwargs['uuid']
        try:
            document = Document.objects.raw("Select * from documents_document where id={0}".format(doc_id))[0]
        except IndexError:
            logger.error('DocumentWizard: Document does not exist. user: %s, doc id: %s', self.user, doc_id )
            return HttpResponseRedirect("/")
        if uuid != str(document.uuid):
            logger.error('DocumentWizard: URL UUID and document UUID do not match: user: %s, doc id %s, uuid %s', self.user, doc.id, uuid )
            return HttpResponseRedirect("/")
        if not document.tempdocument_set.all():
            # Redirect as there is no need to run the wizard
            return HttpResponseRedirect("/")
        if not document.tempdocument_set.all().first().user == self.user:
            return HttpResponseRedirect("/")
        self.file_timestamps, self.email_info, self.email_subject = get_zip_info(self.user, document.tempdocument_set.all()[0].uploaded_file)
        self.step_count = len(self.form_list)
        # ~ if self.email_info:
            # ~ self.step_count -= 1
        if not Tag.objects.exists():
            self.step_count -= 1
        self.last_modified = document.tempdocument_set.all().first().last_modified

        self.document = document
        form_list = WizardStep.get_choices(attribute_name='form_class')
        condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        result = self.__class__.get_initkwargs(form_list=form_list, condition_dict=condition_dict)
        self.form_list = result['form_list']
        self.condition_dict = result['condition_dict']
        return super(
            DocumentWizard, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(
            DocumentWizard, self
        ).get_context_data(form=form, **kwargs)
        wizard_step = WizardStep.get(name=self.steps.current)
        context.update({
            'step_title': _(
                'Step %(step)d of %(total_steps)d: %(step_label)s'
            ) % {
                'step': self.steps.step1, 'total_steps': self.step_count,
                'step_label': wizard_step.label,
            },
            'submit_label': _('Next step'),
            'submit_icon_class': icon_wizard_submit,
            'title': _('Document upload wizard'),
        })
        return context

    def get_form_initial(self, step):
        return WizardStep.get(name=step).get_form_initial(wizard=self) or {}

    def get_form_kwargs(self, step):
        return WizardStep.get(name=step).get_form_kwargs(wizard=self) or {}

    def done(self, form_list, **kwargs):
        user = kwargs.pop('user', None)
        self.temp_document = self.document.tempdocument_set.all().first()
        self.temp_document.role = self.role
        query_dict = {}

        for step in WizardStep.get_all():
            step.done(wizard=self)
        self.temp_document.save()
        task_post_upload_process.delay(document_pk = self.document.pk,email = self.email_info,
            file_timestamps = self.file_timestamps, temp_document_pk = self.temp_document.pk)
        # ~ task_post_upload_process(document_pk = self.document.pk,email = self.email_info,
            # ~ file_timestamps = self.file_timestamps, temp_document_pk = self.temp_document.pk)
        if self.file_timestamps:
            message = 'Documents uploaded successfully. They will be accessible soon.'
        else:
            message = 'Document uploaded successfully. It will be accessible soon.'
        messages.success(
                message=_(message),
                request=self.request
            )
        return HttpResponseRedirect(reverse('documents:document_list_recent_added'))

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
                        if not "Edit documents" in get_permission_titles(acl):
                            return False
        return True

class WizardStepMetadata(WizardStep):
    form_class = DocumentMetadataFormSet
    label = _('Enter document metadata')
    name = 'metadata_entry'
    number = 1

    @classmethod
    def condition(cls, wizard):

        if wizard.email_info:
            document_type = DocumentType.objects.filter(label='Email').first()
        else:
            """
            Skip step if document type has no associated metadata
            """
            cleaned_data = wizard.get_cleaned_data_for_step(WizardStepDocumentType.name) or {}
            document_type = cleaned_data.get('document_type')

        if document_type:
            return document_type.metadata.exists()

    @classmethod
    def get_form_initial(cls, wizard):
        initial = []
        if wizard.email_info:
            step_data = {'document_type': DocumentType.objects.get(label='Email')}
        else:
            step_data = wizard.get_cleaned_data_for_step(WizardStepDocumentType.name)
        if step_data:
            document_type = step_data['document_type']
            for document_type_metadata_type in document_type.metadata.all():
                if not wizard.document and document_type_metadata_type.metadata_type.name == 'document_name':
                    continue
                if wizard.email_info:
                    if document_type_metadata_type.metadata_type.name == 'email_from':
                        document_type_metadata_type.metadata_type.default = wizard.email_info.get('from')
                    elif document_type_metadata_type.metadata_type.name == 'email_to':
                        document_type_metadata_type.metadata_type.default = wizard.email_info.get('to')
                    elif document_type_metadata_type.metadata_type.name == 'email_subject':
                        document_type_metadata_type.metadata_type.default = wizard.email_info.get('subject')
                    elif document_type_metadata_type.metadata_type.name == 'email_date':
                        df = DateFormat(timezone.localtime(parse(wizard.email_info.get('sent'))))
                        document_type_metadata_type.metadata_type.default = str(df.format('d.m.Y H:i'))
                elif wizard.document and not wizard.file_timestamps:
                    if document_type_metadata_type.metadata_type.name == 'document_name':
                        file_name,extension = splitext(wizard.document.label)
                        document_type_metadata_type.metadata_type.default = file_name
                elif wizard.file_timestamps:
                    if document_type_metadata_type.metadata_type.name == 'document_name':
                        continue
                    if document_type_metadata_type.metadata_type.name == 'document_timestamp':
                        continue

                initial.append(
                    {
                        'document_type': document_type,
                        'metadata_type': document_type_metadata_type.metadata_type,
                    }
                )
        return initial

    @classmethod
    def done(cls, wizard):
        result = {}
        cleaned_data = wizard.get_cleaned_data_for_step(cls.name)

        if cleaned_data:
            result={'metadata': cleaned_data}
        wizard.temp_document.metadata = json.dumps(result)
        return result

    @classmethod
    def step_post_upload_process(cls, pending_document, querystring=None):
        pass

WizardStep.register(WizardStepMetadata)

class WizardStepTags(WizardStep):
    form_class = TagMultipleSelectionForm
    label = _('Select tags')
    name = 'tag_selection'
    number = 2

    @classmethod
    def condition(cls, wizard):
        Tag = apps.get_model(app_label='tags', model_name='Tag')
        return Tag.objects.exists()

    @classmethod
    def get_form_kwargs(self, wizard):
        return {
            'help_text': _('Tags to be attached.'),
            'model': Tag,
            'permission': permission_tag_attach,
            'user': wizard.request.user
        }

    @classmethod
    def done(cls, wizard):
        result = {}
        cleaned_data = wizard.get_cleaned_data_for_step(cls.name)
        if cleaned_data:
            result['tags'] = [
                force_text(tag.pk) for tag in cleaned_data['tags']
            ]
        wizard.temp_document.tags = json.dumps(result)
        return result

    @classmethod
    def step_post_upload_process(cls, document, querystring=None):
        pass

WizardStep.register(step=WizardStepTags)
from permissions.models import Role
class WizardStepRoles(WizardStep):
    form_class = RoleMultipleSelectionForm
    label = _('Share the document with:')
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
            'user_role': wizard.role,
        }

    @classmethod
    def done(cls, wizard):
        cleaned_data = wizard.get_cleaned_data_for_step(cls.name)
        result = {}
        if cleaned_data:
            role_rw = []
            for role in cleaned_data.get('read_write_access'):
                role_rw.append(role.id)
            role_ro = []
            for role in cleaned_data.get('read_only_access'):
                role_ro.append(role.id)
            result = {'role_rw':role_rw,
                       'role_ro':role_ro}
        wizard.temp_document.permissions = json.dumps(result)
        return result

    @classmethod
    def step_post_upload_process(cls, document, querystring=None):
        pass

WizardStep.register(WizardStepRoles)

#Called when using the web interface
class DocumentWebCreateWizard(SessionWizardView):
    template_name = 'appearance/generic_wizard.html'
    email_subject = ''

    @classonlymethod
    def as_view(cls, *args, **kwargs):
        cls.form_list = WizardStep.get_choices(attribute_name='form_class')
        cls.condition_dict = dict(WizardStep.get_choices(attribute_name='condition'))
        return super(DocumentWebCreateWizard, cls).as_view(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.user = request.user
        self.role = None
        self.email_info = None
        self.document = None
        self.file_timestamps = None
        self.last_modified = None
        if not request.user.is_superuser:
            try:
                self.role  = Role.objects.get(label=self.user.first_name+" "+self.user.last_name)
            except Role.DoesNotExist:
                return HttpResponseRedirect("/")
        #self.temp_document.save()

        InteractiveSource = apps.get_model(
            app_label='sources', model_name='InteractiveSource'
        )

        form_list = WizardStep.get_choices(attribute_name='form_class')
        condition_dict = dict(
            WizardStep.get_choices(attribute_name='condition')
        )

        result = self.__class__.get_initkwargs(
            condition_dict=condition_dict, form_list=form_list
        )
        self.form_list = result['form_list']
        self.condition_dict = result['condition_dict']

        if not InteractiveSource.objects.filter(enabled=True).exists():
            messages.error(
                message=_(
                    'No interactive document sources have been defined or '
                    'none have been enabled, create one before proceeding.'
                ),
                request=request
            )
            return HttpResponseRedirect(
                redirect_to=reverse(viewname='sources:setup_source_list')
            )

        return super(
            DocumentWebCreateWizard, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super(
            DocumentWebCreateWizard, self
        ).get_context_data(form=form, **kwargs)

        wizard_step = WizardStep.get(name=self.steps.current)

        context.update(
            {
                'form_css_classes': 'form-hotkey-double-click',
                'step_title': _(
                    'Step %(step)d of %(total_steps)d: %(step_label)s'
                ) % {
                    'step': self.steps.step1, 'total_steps': len(self.form_list),
                    'step_label': wizard_step.label,
                },
                'submit_label': _('Next step'),
                'submit_icon_class': icon_wizard_submit,
                'title': _('Document upload wizard'),
                'wizard_step': wizard_step,
                'wizard_steps': WizardStep.get_all(),
            }
        )
        return context

    def get_form_initial(self, step):
        return WizardStep.get(name=step).get_form_initial(wizard=self) or {}

    def get_form_kwargs(self, step):
        return WizardStep.get(name=step).get_form_kwargs(wizard=self) or {}

    def done(self, form_list, **kwargs):
        user = kwargs.pop('user', None)
        self.temp_document = TempDocument(user=self.user,role=self.role)
        self.temp_document.save()
        query_dict = {}

        for step in WizardStep.get_all():
            step.done(wizard=self)
        self.temp_document.save()
        url = '?'.join(
            [
                reverse('sources:document_upload_interactive'),
                urlencode(query_dict, doseq=True)
            ]
        )
        query_dict['temp_document'] = self.temp_document.id
        query_dict['document_type'] = self.temp_document.document_type.id
        url = furl(reverse(viewname='sources:document_upload_interactive'))
        # Use equal and not .update() to get the same result as using
        # urlencode(doseq=True)
        url.args = query_dict

        return HttpResponseRedirect(redirect_to=url.tostr())
