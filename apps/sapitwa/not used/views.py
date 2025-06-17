import logging
import json
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.urls import reverse#, reverse_lazy
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from mayan.apps.common.generics import SingleObjectDeleteView
from mayan.apps.acls.permissions import permission_acl_view, permission_acl_edit
from mayan.apps.acls.models import AccessControlList
from mayan.apps.common.models import SharedUploadedFile

from mayan.apps.documents.models import (
    DocumentType, Document, DocumentVersion
)
from mayan.apps.documents.permissions import (
    permission_document_create
)
from mayan.apps.permissions.models import StoredPermission, Role
from mayan.apps.navigation.classes import Link, ResolvedLink
from mayan.apps.sources.exceptions import SourceException
from mayan.apps.sources.forms import (
    NewDocumentForm, WebFormUploadForm, WebFormUploadFormHTML5
)
from mayan.apps.sources.literals import SOURCE_UNCOMPRESS_CHOICE_ASK, SOURCE_UNCOMPRESS_CHOICE_Y
from mayan.apps.sources.models import (
    InteractiveSource, Source, SaneScanner, StagingFolderSource
)
from mayan.apps.sources.views import UploadBaseView
from mayan.apps.sources.utils import get_form_class, get_upload_form_class #,get_class

from .forms import ShareEditForm, RoleMultipleSelectionForm
from .links import link_permissions_create
from .utils import create_document, get_user_role
from .tasks import task_post_upload_process, task_post_web_upload_process, task_add_ro_permissions, task_add_rw_permissions
from .models import TempDocument

logger = logging.getLogger(name=__name__)
class UploadInteractiveView(UploadBaseView):
    def create_source_form_form(self, **kwargs):
        if hasattr(self.source, 'uncompress'):
            show_expand = self.source.uncompress == SOURCE_UNCOMPRESS_CHOICE_ASK
        else:
            show_expand = False

        return self.get_form_classes()['source_form'](
            prefix=kwargs['prefix'],
            source=self.source,
            show_expand=show_expand,
            data=kwargs.get('data', None),
            files=kwargs.get('files', None),
        )

    def create_document_form_form(self, **kwargs):
        return self.get_form_classes()['document_form'](
            prefix=kwargs['prefix'],
            document_type=self.document_type,
            data=kwargs.get('data', None),
            files=kwargs.get('files', None),
        )

    def dispatch(self, request, *args, **kwargs):
        self.subtemplates_list = []

        self.document_type = get_object_or_404(
            klass=DocumentType, pk=self.request.GET.get(
                'document_type', self.request.POST.get('document_type')
            )
        )
        AccessControlList.objects.check_access(
            obj=self.document_type, permissions=(permission_document_create,),
            user=request.user
        )

        self.tab_links = UploadBaseView.get_active_tab_links()

        try:
            return super(
                UploadInteractiveView, self
            ).dispatch(request, *args, **kwargs)
        except Exception as exception:
            if request.is_ajax():
                return JsonResponse(
                    data={'error': force_text(exception)}, status=500
                )
            else:
                raise

    def forms_valid(self, forms):
        if self.source.can_compress:
            if self.source.uncompress == SOURCE_UNCOMPRESS_CHOICE_ASK:
                expand = forms['source_form'].cleaned_data.get('expand')
            else:
                if self.source.uncompress == SOURCE_UNCOMPRESS_CHOICE_Y:
                    expand = True
                else:
                    expand = False
        else:
            expand = False
        try:
            uploaded_file = self.source.get_upload_file_object(
                forms['source_form'].cleaned_data
            )
        except SourceException as exception:
            messages.error(message=exception, request=self.request)
        else:
            shared_uploaded_file = SharedUploadedFile.objects.create(
                file=uploaded_file.file
            )

            if not self.request.user.is_anonymous:
                user = self.request.user
                user_id = self.request.user.pk
            else:
                user = None
                user_id = None

            try:
                self.source.clean_up_upload_file(uploaded_file)
            except Exception as exception:
                messages.error(message=exception, request=self.request)
            querystring = self.request.GET.copy()
            querystring.update(self.request.POST)

            try:
                Document.execute_pre_create_hooks(
                    kwargs={
                        'document_type': self.document_type,
                        'user': user
                    }
                )

                DocumentVersion.execute_pre_create_hooks(
                    kwargs={
                        'document_type': self.document_type,
                        'shared_uploaded_file': shared_uploaded_file,
                        'user': user
                    }
                )
                temp_document = TempDocument.objects.get(pk = querystring['temp_document'])
                task_post_web_upload_process.delay(shared_uploaded_file.pk,querystring['temp_document'])

            except Exception as exception:
                message = _(
                    'Error executing document upload task; '
                    '%(exception)s'
                ) % {
                    'exception': exception,
                }
                logger.critical(msg=message, exc_info=True)
                raise type(exception)(message)
            else:
                messages.success(
                    message=_(
                        'New document queued for upload and will be available '
                        'shortly.'
                    ), request=self.request
                )

        return HttpResponseRedirect(
            redirect_to='{}?{}'.format(
                reverse(
                    viewname=self.request.resolver_match.view_name,
                    kwargs=self.request.resolver_match.kwargs
                ), self.request.META['QUERY_STRING']
            ),
        )

    def get_context_data(self, **kwargs):
        context = super(UploadInteractiveView, self).get_context_data(**kwargs)
        context['title'] = _(
            'Upload a document of type "%(document_type)s" from '
            'source: %(source)s'
        ) % {'document_type': self.document_type, 'source': self.source.label}

        if not isinstance(self.source, StagingFolderSource) and not isinstance(self.source, SaneScanner):
            context['subtemplates_list'][0]['context'].update(
                {
                    'form_action': '{}?{}'.format(
                        reverse(
                            viewname=self.request.resolver_match.view_name,
                            kwargs=self.request.resolver_match.kwargs
                        ), self.request.META['QUERY_STRING']
                    ),
                    'form_css_classes': 'dropzone',
                    'form_disable_submit': True,
                    'form_id': 'html5upload',
                }
            )
        return context

    def get_form_classes(self):
        source_form_class = get_upload_form_class(
            source_type_name=self.source.source_type
        )

        # Override source form class to enable the HTML5 file uploader
        if source_form_class == WebFormUploadForm:
            source_form_class = WebFormUploadFormHTML5

        return {
            'document_form': NewDocumentForm,
            'source_form': source_form_class
        }

class PermissionDeleteView(SingleObjectDeleteView):
    model = AccessControlList
    object_permission = permission_acl_edit
    pk_url_kwarg = 'acl_id'

    def get_extra_context(self):
        return {
            'acl': self.object,
            'navigation_object_list': ('object', 'acl'),
            'object': self.object.content_object,
            'title': _('Delete Permission: %s') % self.object,
        }

    def get_post_action_redirect(self):
        return reverse(
            viewname='sapitwa:permissions_list', kwargs={
                'object_id': self.object.object_id
            }
        )

def permissions_edit_view(request,acl_id):

    try:
        acl = AccessControlList.objects.get(pk=acl_id)
    except AccessControlList.DoesNotExist:
        raise Http404
    AccessControlList.objects.check_access(acl,(permission_acl_edit,),request.user)
    get_success_url = '/sapitwa/permissions/'+str(acl.content_object.pk)+'/list/'

    if request.method == 'POST':
        form = ShareEditForm(request.POST)
        if form.is_valid():
            selected = form.cleaned_data.get("permission")
            if selected == 'none':
                acl.delete()
            if selected == 'limited':
                task_add_ro_permissions(acl)
            if selected == 'full':
                task_add_rw_permissions(acl)
        return HttpResponseRedirect(get_success_url)
    else:
        form = ShareEditForm()
        rw = False
        sp = StoredPermission.objects.get(name='acl_edit')
        if sp in acl.permissions.all():
            rw = True
        context = {
            'rw': rw,
            'form' : form,
            'permissions_edit':True,
            'object' : acl.content_object,
            'hide_header' : True,
            'hide_links' : False,
            'hide_object' : True,
            'get_success_url': get_success_url,
            'title': _(
                    'Edit permissions for %s for document %s:' % (acl.role,acl.content_object)
            ),
        }
        return render(request, 'sapitwa/generic_list.html',context = context)

def permissions_create_view(request, object_id):

    try:
        document = Document.objects.get(pk = object_id)
    except Document.DoesNotExist:
        raise Http404

    if request.method == 'POST':
        form = RoleMultipleSelectionForm(request.POST)
        if form.is_valid():
            rw_selected = form.cleaned_data.get('read_write_access')
            ro_selected = form.cleaned_data.get('read_only_access')
            for r in rw_selected:
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=document.pk,content_type=ContentType.objects.get_for_model(document), role=r
                )
                task_add_rw_permissions(acl)
            for r in ro_selected:
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=document.pk,content_type=ContentType.objects.get_for_model(document), role=r
                )
                task_add_ro_permissions(acl)
        return HttpResponseRedirect(reverse('sapitwa:permissions_list',args=(document.id,)))
    else:
        try:
            document = Document.objects.get(pk = object_id)
        except Document.DoesNotExist:
            raise Http404
        object_content_type = get_object_or_404(
            ContentType, app_label='documents',
            model='document'
        )

        acls = AccessControlList.objects.filter(content_type=object_content_type,object_id=document.pk)

        roles = []
        for a in acls:
            roles.append(a.role.pk)
        rem_roles = Role.objects.all().exclude(id__in = roles)
        if not rem_roles:
            no_results_title = _('Document is already shared with everyone.')
        else:
            no_results_title = ''
        form = RoleMultipleSelectionForm(roles = rem_roles)

        context = {
            'form' : form,
            'permissions_create':True,
            'object' : document,
            'hide_header' : True,
            'hide_links' : False,
            'hide_object' : True,
            'no_results_title' : no_results_title,
            'title': _(
                    'Share this document \n%s:' % (document)
            ),
        }
        return render(request, 'sapitwa/generic_list.html',context = context)

def permissions_list_view(request,object_id):
    try:
        content_object = Document.objects.get(
            pk=object_id
        )
    except Document.DoesNotExist:
        raise Http404
    AccessControlList.objects.check_access(content_object,(permission_acl_view,),request.user)

    object_content_type = get_object_or_404(
        ContentType, app_label='documents',
        model='document'
    )
    acls = AccessControlList.objects.filter(
                    content_type=object_content_type,
                    object_id=content_object.pk
                )
    user_role = get_user_role(request.user)
    sp = StoredPermission.objects.get(name='acl_edit')
    rw =[]
    ro = []
    for item in acls:
        if user_role == item.role:
            continue
        if sp in item.permissions.all():
               rw.append(item)
        else:
            ro.append(item)
    #display delete, edit buttons

    try:
        acl_edit = AccessControlList.objects.check_access(content_object,(permission_acl_edit,),request.user)
    except:
        acl_edit = False
    context = {
        'object_list_rw': rw,
        'object_list_ro': ro,
        'acl_edit' : acl_edit,
        'list_roles':True,
        'object' : content_object,
        'no_results_title': _('Document is not shared'),
        'no_results_main_link': link_permissions_create.resolve(
            context=RequestContext(
                request, {'object': content_object}
            )
        ),
        'hide_header' : True,
        'hide_links' : False,
        'hide_object' : True,
        'title': _(
                ' %s is shared with:' % content_object
        ),
    }
    return render(request, 'sapitwa/generic_list.html',context = context)
