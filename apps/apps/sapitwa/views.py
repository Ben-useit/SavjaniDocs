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

from common.generics import ConfirmView, SimpleView,SingleObjectDeleteView,SingleObjectCreateView
from acls.permissions import permission_acl_view, permission_acl_edit
from acls.models import AccessControlList
from common.models import SharedUploadedFile

from documents.models import (
    DocumentType, Document, DocumentVersion
)
from mayan.apps.documents.permissions import (
    permission_document_create
)
from permissions.models import StoredPermission, Role
from navigation.classes import Link, ResolvedLink
from register.permissions import permission_register_view
from sources.exceptions import SourceException
from sources.forms import (
    NewDocumentForm, WebFormUploadForm, WebFormUploadFormHTML5
)
from sources.literals import SOURCE_UNCOMPRESS_CHOICE_ASK, SOURCE_UNCOMPRESS_CHOICE_Y
from sources.models import (
    InteractiveSource, Source, SaneScanner, StagingFolderSource
)
from sources.views import UploadBaseView
from sources.utils import get_form_class, get_upload_form_class #,get_class

from .forms import ShareEditForm, RoleMultipleSelectionForm, DocumentStatisticForm
from .links import link_permissions_create
from .utils import create_document, get_user_role
from .tasks import task_post_upload_process, task_post_web_upload_process, task_add_ro_permissions, task_add_rw_permissions
from .models import TempDocument, UserStats

logger = logging.getLogger(name=__name__)


from datetime import datetime, timedelta
import calendar
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from dateutil.parser import parse
from actstream.models import Action,any_stream
from django.contrib.auth.models import User


class SignatureImageDeleteView(ConfirmView):

    success_message = 'Image deleted.'
    success_message_plural = 'Images deleted.'
    action_cancel_redirect = post_action_redirect = reverse_lazy(
        'documents:document_list'
    )
    def dispatch(self, request, *args, **kwargs):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        return super(SignatureImageDeleteView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'title': _('Delete the images?'),
            'next' : self.post_action_redirect
        }

    def get_post_action_redirect(self):
        return reverse('documents:document_list')

    def view_action(self):
        id_list = self.request.GET.get(
            'id_list', self.request.POST.get('id_list', '')
        )
        images_to_delete = {}
        docs = Document.objects.filter(pk__in=id_list.split(','))
        doc_errors = []
        checksums = []
        for doc in docs:
            if doc.latest_version:
                duplicates = Document.objects.filter(versions__checksum = doc.latest_version.checksum )
                checksums.append(doc.latest_version.checksum)
                for d in duplicates:
                    images_to_delete[d] = True
                    #d.delete(to_trash=False)
            else:
                doc_errors.append(doc)
        for k,v in images_to_delete.items():
            #k.delete(to_trash=False)
            k.delete()
        messages.success(
            self.request, _('Done.')
        )

class DocumentStatisticView(SingleObjectCreateView):
    model = Document
    form_class = DocumentStatisticForm

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        return super(DocumentStatisticView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(DocumentStatisticView, self).get_form_kwargs()
        return kwargs

    def get_extra_context(self):
        return {
            'title': _('Create Statistics'),
        }
    def get_success_url(self):
        return reverse_lazy('sapitwa:show_statistics', args = (self.from_dt.year,self.from_dt.month,self.from_dt.day,self.to_dt.year,self.to_dt.month,self.to_dt.day))

    def form_valid(self, form):
        if form.is_valid():
            if 'week' in form.cleaned_data:
                if form.cleaned_data['week'] != '':
                    week = form.cleaned_data['week']
                    dt = datetime.strptime(week, "%d.%m.%Y").date()
                    self.from_dt = dt - timedelta(days=dt.weekday())
                    self.to_dt = self.from_dt + timedelta(days=6)
                    return HttpResponseRedirect(self.get_success_url())
            if 'month' in form.cleaned_data:
                if form.cleaned_data['month'] != '':
                    month = form.cleaned_data['month']
                    dt = datetime.strptime(month, "%d.%m.%Y").date()
                    a,b = calendar.monthrange(dt.year, dt.month)
                    self.from_dt=datetime.strptime('01.'+str(dt.month)+'.'+str(dt.year), "%d.%m.%Y").date()
                    self.to_dt=datetime.strptime(str(b)+'.'+str(dt.month)+'.'+str(dt.year), "%d.%m.%Y").date()
                    return HttpResponseRedirect(self.get_success_url())
            if 'from' in form.cleaned_data:
                if form.cleaned_data['from'] != '':
                    date_from = form.cleaned_data['from']
                    self.from_dt = datetime.strptime(date_from, "%d.%m.%Y").date()
                else:
                    self.from_dt = datetime.strptime('27.12.2017', "%d.%m.%Y").date()
            if 'to' in form.cleaned_data:
                if form.cleaned_data['to'] != '':
                    date_to = form.cleaned_data['to']
                    self.to_dt = datetime.strptime(date_to, "%d.%m.%Y").date()
                else:
                    self.to_dt = datetime.now().date()
        return HttpResponseRedirect(self.get_success_url())


class ShowStatisticView(SimpleView):
    model = Document
    template_name = 'sapitwa/statistic_result.html'
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        from_year= kwargs.pop('year_from', None)
        from_month=kwargs.pop('month_from', None)
        from_day=kwargs.pop('day_from', None)
        to_year=kwargs.pop('year_to', None)
        to_month=kwargs.pop('month_to', None)
        to_day=kwargs.pop('day_to', None)
        week = kwargs.pop('week', None)
        month = kwargs.pop('month', None )
        date_from = date_to = None
        if from_year and from_month and from_day:
            date_from = datetime(int(from_year),int(from_month),int(from_day))
        if to_year and to_month and to_day:
            date_to = datetime(int(to_year),int(to_month),int(to_day))

        stats = UserStats.objects.filter(date__gte=date_from,date__lte=date_to)
        users = User.objects.all()
        result = {}
        for u in users:
            result[u] = 0
        for s in stats:
            result[s.user] += s.number
        self.date_from = date_from
        self.date_to = date_to
        self.result = result
        return super(ShowStatisticView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        context = {
            'hide_object': True,
            'result' : self.result,
            'no_results_title': _('No results'),
            'title': _('Upload Statistics for period: %s.%s %s - %s.%s %s') %
            (self.date_from.day,self.date_from.month,self.date_from.year,self.date_to.day,self.date_to.month,self.date_to.year),
        }

        # ~ if self.search_model.list_mode == LIST_MODE_CHOICE_ITEM:
            # ~ context['list_as_items'] = True

        return context
        return context

class UploadWebInteractiveView(UploadBaseView):
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
                UploadWebInteractiveView, self
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
        context = super(UploadWebInteractiveView, self).get_context_data(**kwargs)
        context['title'] = _(
            'Upload a document of type "%(document_type)s" from '
            'source: %(source)s'
        ) % {'document_type': self.document_type, 'source': self.source.label}

        if not isinstance(self.source, StagingFolderSource) and not isinstance(self.source, SaneScanner):
            context['subtemplates_list'][0]['context'].update(
                {
                    'form_action': '{}?{}'.format(
                        reverse(
                            self.request.resolver_match.view_name,
                            kwargs=self.request.resolver_match.kwargs
                        ), self.request.META['QUERY_STRING']
                    ),
                    'form_class': 'dropzone',
                    'form_disable_submit': True,
                    'form_id': 'html5upload',
                }
            )
        return context

    def get_form_classes(self):
        source_form_class = get_upload_form_class(self.source.source_type)

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

from register.models import Register, Quotation
from dal import autocomplete
from dal_select2.views import Select2QuerySetView
import operator
from django.db.models import Q
class RegisterFileAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Register.objects.none()

        qs = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=Register.objects.all())


        if self.q:
            q_list = [Q(file_no__icontains=self.q), Q(_file_no_bak__icontains=self.q)]
            qs = qs.filter(reduce(operator.or_, q_list))

        return qs

class QuotationFileAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Quotation.objects.none()

        qs = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=self.request.user, queryset=Quotation.objects.all())

        if self.q:
            qs = qs.filter(file_no__icontains=self.q)

        return qs
                
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
