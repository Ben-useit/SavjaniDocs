from django.apps import apps
from django.utils.translation import ugettext_lazy as _

from navigation.classes import Link

from acls.permissions import permission_acl_view, permission_acl_edit

from .icons import icon_shares_edit,icon_shares_list
from mayan_statistics.permissions import permission_statistics_view
from mayan_statistics.icons import icon_view

def get_kwargs_factory(variable_name):
    def get_kwargs(context):
        ContentType = apps.get_model(
            app_label='contenttypes', model_name='ContentType'
        )

        content_type = ContentType.objects.get_for_model(
            context[variable_name]
        )
        return {
            'app_label': '"{}"'.format(content_type.app_label),
            'model_name': '"{}"'.format(content_type.model),
            'object_id': '{}.pk'.format(variable_name)
        }

    return get_kwargs

link_permissions_list = Link(
    args='resolved_object.pk',
    icon_class=icon_shares_list,
    permissions=(permission_acl_view,), text=_('Shares'), view='sapitwa:permissions_list'
)
link_permissions_edit = Link(
    args='resolved_object.pk', icon_class=icon_shares_edit,
    permissions=(permission_acl_edit,),
    text=_('Edit'), view='sapitwa:permissions_edit'
)
link_permissions_create = Link(
    args='resolved_object.pk',
    icon_class=icon_shares_list,
    permissions=(permission_acl_edit,), text=_('Add user to share this document with'),
    view='sapitwa:permissions_create'
)
link_document_statistics = Link(
    icon_class=icon_view,
    permissions=(permission_statistics_view,),
    text=_('Upload statistics'), view='sapitwa:document_statistic'
)

link_document_multiple_delete_signature_images = Link(
    text=_('Delete image'),
    view='sapitwa:signature_image_delete_view'
)
