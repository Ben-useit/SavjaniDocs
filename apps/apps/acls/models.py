from __future__ import absolute_import, unicode_literals

import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from permissions.models import Role, StoredPermission

from .managers import AccessControlListManager

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class AccessControlList(models.Model):
    """
    ACL means Access Control List it is a more fine-grained method of
    granting access to objects. In the case of ACLs, they grant access using
    3 elements: actor, permission, object. In this case the actor is the role,
    the permission is the Mayan permission and the object can be anything:
    a document, a folder, an index, etc. This means = "Grant X permissions
    to role Y for object Z". This model holds the permission, object, actor
    relationship for one access control list.
    Fields:
    * Role - Custom role that is being granted a permission. Roles are created
    in the Setup menu.
    """
    content_type = models.ForeignKey(
        on_delete=models.CASCADE, related_name='object_content_type',
        to=ContentType
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey(
        ct_field='content_type', fk_field='object_id',
    )
    # TODO: limit choices to the permissions valid for the content_object
    permissions = models.ManyToManyField(
        blank=True, related_name='acls', to=StoredPermission,
        verbose_name=_('Permissions')
    )
    role = models.ForeignKey(
        on_delete=models.CASCADE, related_name='acls', to=Role,
        verbose_name=_('Role')
    )

    objects = AccessControlListManager()

    class Meta:
        ordering = ('pk',)
        unique_together = ('content_type', 'object_id', 'role')
        verbose_name = _('Access entry')
        verbose_name_plural = _('Access entries')

    def __str__(self):
        return _(
            'Permissions "%(permissions)s" to role "%(role)s" for "%(object)s"'
        ) % {
            'permissions': self.get_permission_titles(),
            'object': self.content_object,
            'role': self.role
        }

    def get_inherited_permissions(self):
        return AccessControlList.objects.get_inherited_permissions(
            role=self.role, obj=self.content_object
        )

    def get_permission_titles(self):
        result = ', '.join(
            [force_text(permission) for permission in self.permissions.all()]
        )

        return result or _('None')
        
    def add_full_doc_permissions(self):
        ro_permissions ='comment_view'
        ro_permissions +=',transformation_view,content_view'
        ro_permissions +=',document_view,document_version_view'
        ro_permissions +=',document_print,document_download,ocr_document'
        ro_permissions +=',events_view,mail_document,metadata_document_view'
        ro_permissions +=',ocr_content_view,tag_view,tag_attach'

        rw_permissions = ro_permissions +''
        rw_permissions +=',comment_create,transformation_delete,document_delete,document_trash'
        rw_permissions +=',document_restore,metadata_document_remove,acl_edit,acl_view'
        rw_permissions +=',comment_delete,transformation_edit,transformation_create,tag_remove'
        rw_permissions +=',document_properties_edit,document_edit,document_version_revert'
        rw_permissions +=',metadata_document_edit,metadata_document_add,tag_remove,document_new_version'
        for p in rw_permissions.split(','):
            self.permissions.add(StoredPermission.objects.get(name=p))
            
    def add_doc_permissions(self):
        ro_permissions ='comment_view'
        ro_permissions +=',transformation_view,content_view'
        ro_permissions +=',document_view,document_version_view'
        ro_permissions +=',document_print,document_download,ocr_document'
        ro_permissions +=',events_view,mail_document,metadata_document_view'
        ro_permissions +=',ocr_content_view,tag_view,tag_attach,acl_view'

        rw_permissions = ro_permissions +''
        rw_permissions +=',comment_create'
        rw_permissions +=',comment_delete,transformation_edit,transformation_create'
        rw_permissions +=',document_properties_edit,document_edit'
        rw_permissions +=',metadata_document_edit,metadata_document_add,document_new_version'
        for p in rw_permissions.split(','):
            self.permissions.add(StoredPermission.objects.get(name=p)) 
