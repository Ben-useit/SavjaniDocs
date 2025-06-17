from __future__ import absolute_import, unicode_literals

import itertools
import logging

from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.contrib.auth.models import User


from common.views import (
    AssignRemoveView, SingleObjectCreateView, SingleObjectDeleteView,
    SingleObjectListView
)
from permissions import PermissionNamespace, Permission
from permissions.models import StoredPermission, Role
from permissions.forms import RoleMultipleSelectionForm

from documents.models import Document
from documents.events import event_document_shared

from .classes import ModelPermission
from .icons import icon_acl_list
from .links import link_acl_create
from .models import AccessControlList
from .permissions import permission_acl_edit, permission_acl_view
from .tasks import task_send_mail, task_get_role_context

from .literals import get_help_text

logger = logging.getLogger(__name__)

from documents.models import Document
from documents.events import event_document_shared

from .classes import ModelPermission
from .models import AccessControlList
from .permissions import permission_acl_edit, permission_acl_view

class ACLCreateView(SingleObjectCreateView):
    fields = ('role',)
    model = AccessControlList

    def dispatch(self, request, *args, **kwargs):
        self.object_content_type = get_object_or_404(
            ContentType, app_label=self.kwargs['app_label'],
            model=self.kwargs['model']
        )

        try:
            self.content_object = self.object_content_type.get_object_for_this_type(
                pk=self.kwargs['object_id']
            )
        except self.object_content_type.model_class().DoesNotExist:
            raise Http404

        AccessControlList.objects.check_access(
            permissions=permission_acl_edit, user=request.user,
            obj=self.content_object
        )

        return super(ACLCreateView, self).dispatch(request, *args, **kwargs)

    def get_instance_extra_data(self):
        return {
            'content_object': self.content_object
        }

    def form_valid(self, form):
        try:
            acl = AccessControlList.objects.get(
                content_type=self.object_content_type,
                object_id=self.content_object.pk,
                role=form.cleaned_data['role']
            )
        except AccessControlList.DoesNotExist:
            return super(ACLCreateView, self).form_valid(form)
        else:
            return HttpResponseRedirect(
                reverse('acls:acl_permissions', args=(acl.pk,))
            )

    def get_extra_context(self):
        return {
            'object': self.content_object,
            'title': _(
                'New access control lists for: %s'
            ) % self.content_object
        }

    def get_success_url(self):
        if self.object.pk:
            return reverse('acls:acl_permissions', args=(self.object.pk,))
        else:
            return super(ACLCreateView, self).get_success_url()

class ACLEditView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            object_id = self.kwargs['object_id']

            #get the role of the current user first
            role = None
            if not request.user.is_superuser:
                try:
                    role = Role.objects.get(label=request.user.first_name+" "+request.user.last_name)
                except Role.DoesNotExist:
                    logger.error("There is NO role with the same for this user: %s", user)
                    messages.error(
                        request, 'Could not share this document.'
                    )
                    return HttpResponseRedirect(reverse("documents:document_preview", args=[self.kwargs['object_id'],]))
                    
            
            object_content_type = get_object_or_404(
                ContentType, app_label='documents',
                model='document'
            )   
            acl = AccessControlList.objects.filter(
                    content_type=object_content_type,
                    object_id=object_id
                ).delete()

            #give current user full access
            if role:
                acl = AccessControlList.objects.create(
                      object_id=object_id,content_type=object_content_type, role=role
                    )
                acl.add_full_doc_permissions()

            document = Document.objects.get(pk = object_id)   

            for key, value in request.POST.iteritems():
                if key.startswith('role_'):
                    if key.startswith('role_selection-submit'):
                        continue
                    if value == '1':
                        full_permission = False
                    elif value == '2':
                        full_permission = True
                    else:
                        continue
                    role = None
                    role_id = key.strip('role_selection-')
                    try:
                        role = Role.objects.get(pk=role_id)
                    except Role.DoesNotExist:
                        pass
                    if role:                       
                        acl_new = AccessControlList.objects.create(
                            object_id=object_id,content_type=object_content_type, role=role
                        )
                        if full_permission:
                            acl_new.add_full_doc_permissions() 
                        else:
                            acl_new.add_doc_permissions()
                        messages.success(
                            request, 'Document shared with %s successfully.' % role.label
                        )
            event_document_shared.commit(
                actor=request.user, target=document, action_object=document.document_type
            )
                        
            return HttpResponseRedirect(reverse("documents:document_preview", args=[self.kwargs['object_id'],]))
        else:
          
            try:
                self.content_object = Document.objects.get(
                    pk=self.kwargs['object_id']
                )
            except Document.DoesNotExist:
                raise Http404



            AccessControlList.objects.check_access(
                permissions=permission_acl_view, user=request.user,
                obj=self.content_object
            )
            self.roles = task_get_role_context(request,self.kwargs['object_id'])
            return super(ACLEditView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'hide_object': True,
            'no_results_icon': icon_acl_list,
            'no_results_main_link': link_acl_create.resolve(
                context=RequestContext(
                    self.request, {'resolved_object': self.content_object}
                )
            ),
            'no_results_title': _(
                'There are no sharing options for this object'
            ),
            'no_results_text': _(
                'ACL stands for Access Control List and is a precise method '
                ' to control user access to objects in the system.'
            ),
            'object': self.content_object,
            'role_selection' : True,
            'title': _('Change sharing settings for: %s' % self.content_object),
            'help_collapse': get_help_text(),
        }

    def get_context_data(self, **kwargs):
        context = super(ACLEditView, self).get_context_data(**kwargs)
        context.update(self.roles)    
        return context
        
    def get_object_list(self):
        return AccessControlList.objects.none() #get_role_context
        
class ACLDeleteView(SingleObjectDeleteView):
    model = AccessControlList

    def dispatch(self, request, *args, **kwargs):
        acl = get_object_or_404(AccessControlList, pk=self.kwargs['pk'])

        AccessControlList.objects.check_access(
            permissions=permission_acl_edit, user=request.user,
            obj=acl.content_object
        )

        return super(ACLDeleteView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'object': self.get_object().content_object,
            'title': _('Delete ACL: %s') % self.get_object(),
        }

    def get_post_action_redirect(self):
        instance = self.get_object()
        return reverse(
            'acls:acl_list', args=(
                instance.content_type.app_label,
                instance.content_type.model, instance.object_id
            )
        )


class ACLListView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        self.object_content_type = get_object_or_404(
            ContentType, app_label=self.kwargs['app_label'],
            model=self.kwargs['model']
        )

        try:
            self.content_object = self.object_content_type.get_object_for_this_type(
                pk=self.kwargs['object_id']
            )
        except self.object_content_type.model_class().DoesNotExist:
            raise Http404

        AccessControlList.objects.check_access(
            permissions=permission_acl_view, user=request.user,
            obj=self.content_object
        )

        return super(ACLListView, self).dispatch(request, *args, **kwargs)

    def get_extra_context(self):
        return {
            'hide_object': True,
            'no_results_icon': icon_acl_list,
            'no_results_main_link': link_acl_create.resolve(
                context=RequestContext(
                    self.request, {'resolved_object': self.content_object}
                )
            ),
            'no_results_title': _(
                'There are no ACLs for this object'
            ),
            'no_results_text': _(
                'ACL stands for Access Control List and is a precise method '
                ' to control user access to objects in the system.'
            ),
            'object': self.content_object,
            'title': _('Access control lists for: %s' % self.content_object),
        }

    def get_object_list(self):
        return AccessControlList.objects.filter(
            content_type=self.object_content_type,
            object_id=self.content_object.pk
        )


class ACLPermissionsView(AssignRemoveView):
    grouped = True
    left_list_title = _('Available permissions')
    right_list_title = _('Granted permissions')

    @staticmethod
    def generate_choices(entries):
        results = []

        entries = sorted(
            entries, key=lambda x: (
                x.get_volatile_permission().namespace.label,
                x.get_volatile_permission().label
            )
        )

        for namespace, permissions in itertools.groupby(entries, lambda entry: entry.namespace):
            permission_options = [
                (force_text(permission.pk), permission) for permission in permissions
            ]
            results.append(
                (PermissionNamespace.get(namespace), permission_options)
            )

        return results

    def add(self, item):
        permission = get_object_or_404(StoredPermission, pk=item)
        self.get_object().permissions.add(permission)

    def dispatch(self, request, *args, **kwargs):
        acl = get_object_or_404(AccessControlList, pk=self.kwargs['pk'])

        AccessControlList.objects.check_access(
            permissions=permission_acl_edit, user=request.user,
            obj=acl.content_object
        )

        return super(
            ACLPermissionsView, self
        ).dispatch(request, *args, **kwargs)

    def get_available_list(self):
        return ModelPermission.get_for_instance(
            instance=self.get_object().content_object
        ).exclude(id__in=self.get_granted_list().values_list('pk', flat=True))

    def get_disabled_choices(self):
        """
        Get permissions from a parent's acls but remove the permissions we
        already hold for this object
        """
        return map(
            str, set(
                self.get_object().get_inherited_permissions().values_list(
                    'pk', flat=True
                )
            ).difference(
                self.get_object().permissions.values_list('pk', flat=True)
            )
        )

    def get_extra_context(self):
        return {
            'object': self.get_object().content_object,
            'title': _('Role "%(role)s" permission\'s for "%(object)s"') % {
                'role': self.get_object().role,
                'object': self.get_object().content_object,
            },
        }

    def get_granted_list(self):
        """
        Merge or permissions we hold for this object and the permissions we
        hold for this object's parent via another ACL
        """
        merged_pks = self.get_object().permissions.values_list('pk', flat=True) | self.get_object().get_inherited_permissions().values_list('pk', flat=True)
        return StoredPermission.objects.filter(pk__in=merged_pks)

    def get_object(self):
        return get_object_or_404(AccessControlList, pk=self.kwargs['pk'])

    def get_right_list_help_text(self):
        if self.get_object().get_inherited_permissions():
            return _(
                'Disabled permissions are inherited from a parent object.'
            )

        return None

    def left_list(self):
        Permission.refresh()
        return ACLPermissionsView.generate_choices(self.get_available_list())

    def remove(self, item):
        permission = get_object_or_404(StoredPermission, pk=item)
        self.get_object().permissions.remove(permission)

    def right_list(self):
        return ACLPermissionsView.generate_choices(self.get_granted_list())



def add_permissions(request, object_id, user_id):
    object_content_type = get_object_or_404(
        ContentType, app_label='documents',
        model='document'
    )     
    try:
        content_object = object_content_type.get_object_for_this_type(
            pk=object_id
        )
    except object_content_type.model_class().DoesNotExist:
        raise Http404
    
    AccessControlList.objects.check_access(
            permissions=permission_acl_edit, user=request.user,
            obj=content_object
    )

    try:
        user = User.objects.get(pk = user_id)
        username = user.first_name+" "+user.last_name
        document = Document.objects.get(pk = object_id )
    except:
        return HttpResponseRedirect('/') 
    
    if request.method == "POST":
        if request.POST['dropdown'] == 'Yes':
            role = Role.objects.get(label=str(username))
            acl, created = AccessControlList.objects.get_or_create(
            object_id=object_id,content_type=object_content_type, role=role
            )
            acl.add_doc_permissions()
            messages.success(
                request, 'Document shared with %s successfully.' % role.label
            )
            task_send_mail(request.user,user,document,True)
        else:
            messages.success(
                request, 'Document sharing rejected with %s successfully.' % role.label
            )            
            task_send_mail(request.user,user,document,False)
        return HttpResponseRedirect(reverse('acls:acl_list',args=('documents','document',object_id,)))
        
    else:
        try:
            document = Document.objects.get(pk = object_id)
            title = 'Request for document permission'
            
        except Document.DoesNotExist:
            pass       
        return render(request, 'appearance/generic_form.html' ,
            {'add_permission' : True, 'doc' : document, 'username' : username, 'title': title })  
            
