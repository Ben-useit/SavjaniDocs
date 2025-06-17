from __future__ import absolute_import, unicode_literals

import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext, ugettext_lazy as _

from common.utils import return_attrib, return_related
from permissions import Permission
from permissions.models import StoredPermission

from .exceptions import PermissionNotValidForClass
from .classes import ModelPermission

logger = logging.getLogger(__name__)

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models.functions import Concat
class AccessControlListManager(models.Manager):

    """
    Implement a 3 tier permission system, involving a permissions, an actor
    and an object
    """
    def _get_acl_filters(
        self, queryset, stored_permission, user, related_field_name=None
    ):
        """
        This method does the bulk of the work. It generates filters for the
        AccessControlList model to determine if there are ACL entries for the
        members of the queryset's model provided.
        """
        # Determine which of the cases we need to address
        # 1: No related field
        # 2: Related field
        # 3: Related field that is Generic Foreign Key
        # 4: No related field, but has an inherited related field, solved by
        # recursion, branches to #2 or #3.
        # 5: Inherited field of a related field
        # 6: Inherited field of a related field that is Generic Foreign Key
        # -- Not addressed yet --
        # 7: Has a related function
        result = []

        if related_field_name:
            related_field = get_related_field(
                model=queryset.model, related_field_name=related_field_name
            )

            if isinstance(related_field, GenericForeignKey):
                # Case 3: Generic Foreign Key, multiple ContentTypes + object
                # id combinations
                # Also handles case #6 using the parent related field
                # reference template.

                # Craft a double underscore reference to a previous related
                # field in the case where multiple related fields are
                # associated.
                # Example: object_layer__content_type
                recuisive_related_reference = '__'.join(related_field_name.split('__')[0:-1])

                # If there is at least one parent related field we add a
                # double underscore to make it a valid filter template.
                if recuisive_related_reference:
                    recuisive_related_reference = '{}__'.format(recuisive_related_reference)

                content_type_object_id_queryset = queryset.annotate(
                    ct_fk_combination=Concat(
                        '{}{}'.format(
                            recuisive_related_reference, related_field.ct_field
                        ), Value('-'),
                        '{}{}'.format(
                            recuisive_related_reference, related_field.fk_field
                        ), output_field=CharField()
                    )
                ).values('ct_fk_combination')

                acl_filter = self.annotate(
                    ct_fk_combination=Concat(
                        'content_type', Value('-'), 'object_id',
                        output_field=CharField()
                    )
                ).filter(
                    permissions=stored_permission, role__groups__user=user,
                    ct_fk_combination__in=content_type_object_id_queryset
                ).values('object_id')

                field_lookup = '{}object_id__in'.format(recuisive_related_reference)
                result.append(Q(**{field_lookup: acl_filter}))
            else:
                # Case 2: Related field of a single type, single ContentType,
                # multiple object id
                content_type = ContentType.objects.get_for_model(
                    model=related_field.related_model
                )
                field_lookup = '{}_id__in'.format(related_field_name)
                acl_filter = self.filter(
                    content_type=content_type, permissions=stored_permission,
                    role__groups__user=user
                ).values('object_id')
                # Don't add empty filters otherwise the default AND operator
                # of the Q object will return an empty queryset when reduced
                # and filter out objects that should be in the final queryset.
                if acl_filter:
                    result.append(Q(**{field_lookup: acl_filter}))

                # Case 5: Related field, has an inherited related field itself
                # Bubble up permssion check
                # Recurse and reduce
                # TODO: Add relationship support: OR or AND
                # TODO: OR for document pages, version, doc, and types
                # TODO: AND for new cabinet levels ACLs
                try:
                    related_field_model_related_fields = (
                        ModelPermission.get_inheritance(
                            model=related_field.related_model
                        ),
                    )
                except KeyError:
                    pass
                else:
                    relation_result = []
                    for related_field_model_related_field_name in related_field_model_related_fields:
                        related_field_name = '{}__{}'.format(related_field_name, related_field_model_related_field_name)
                        related_field_inherited_acl_queries = self._get_acl_filters(
                            queryset=queryset,
                            stored_permission=stored_permission, user=user,
                            related_field_name=related_field_name
                        )
                        if related_field_inherited_acl_queries:
                            relation_result.append(
                                reduce(
                                    operator.and_,
                                    related_field_inherited_acl_queries
                                )
                            )

                    if relation_result:
                        result.append(reduce(operator.or_, relation_result))
        else:
            # Case 1: Original model, single ContentType, multiple object id
            content_type = ContentType.objects.get_for_model(
                model=queryset.model
            )
            field_lookup = 'id__in'
            acl_filter = self.filter(
                content_type=content_type, permissions=stored_permission,
                role__groups__user=user
            ).values('object_id')
            result.append(Q(**{field_lookup: acl_filter}))

            # Case 4: Original model, has an inherited related field
            try:
                related_fields = (
                    ModelPermission.get_inheritance(
                        model=queryset.model
                    ),
                )
            except KeyError:
                pass
            else:
                relation_result = []

                for related_field_name in related_fields:
                    inherited_acl_queries = self._get_acl_filters(
                        queryset=queryset, stored_permission=stored_permission,
                        related_field_name=related_field_name, user=user
                    )
                    if inherited_acl_queries:
                        relation_result.append(
                            reduce(operator.and_, inherited_acl_queries)
                        )

                if relation_result:
                    result.append(reduce(operator.or_, relation_result))

            # Case 7: Has a function
            try:
                field_query_function = ModelPermission.get_field_query_function(
                    model=queryset.model
                )
            except KeyError:
                pass
            else:
                function_results = field_query_function()

                # Filter by the model's content type
                content_type = ContentType.objects.get_for_model(
                    model=queryset.model
                )
                acl_filter = self.filter(
                    content_type=content_type, permissions=stored_permission,
                    role__groups__user=user
                ).values('object_id')
                # Obtain an queryset of filtered, authorized model instances
                acl_queryset = queryset.model._meta.default_manager.filter(
                    id__in=acl_filter
                ).filter(**function_results['acl_filter'])

                if 'acl_values' in function_results:
                    acl_queryset = acl_queryset.values(
                        *function_results['acl_values']
                    )

                # Get the final query using the filtered queryset as the
                # reference
                result.append(
                    Q(**{function_results['field_lookup']: acl_queryset})
                )

        return result


    """
    Implement a 3 tier permission system, involving a permissions, an actor
    and an object
    """
    def check_access(self, permissions, user, obj, related=None):
        if user.is_superuser or user.is_staff:
            logger.debug(
                'Permissions "%s" on "%s" granted to user "%s" as superuser '
                'or staff', permissions, obj, user
            )
            return True

        try:
            return Permission.check_permissions(
                requester=user, permissions=permissions
            )
        except PermissionDenied:
            try:
                stored_permissions = [
                    permission.stored_permission for permission in permissions
                ]
            except TypeError:
                # Not a list of permissions, just one
                stored_permissions = (permissions.stored_permission,)

            if related:
                obj = return_attrib(obj, related)

            try:
                parent_accessor = ModelPermission.get_inheritance(
                    model=obj._meta.model
                )
            except AttributeError:
                # AttributeError means non model objects: ie Statistics
                # These can't have ACLs so we raise PermissionDenied
                raise PermissionDenied(_('Insufficient access for: %s') % obj)
            except KeyError:
                pass
            else:
                try:
                    return self.check_access(
                        obj=getattr(obj, parent_accessor),
                        permissions=permissions, user=user
                    )
                except AttributeError:
                    # Has no such attribute, try it as a related field
                    try:
                        return self.check_access(
                            obj=return_related(
                                instance=obj, related_field=parent_accessor
                            ), permissions=permissions, user=user
                        )
                    except PermissionDenied:
                        pass
                except PermissionDenied:
                    pass

            user_roles = []
            for group in user.groups.all():
                for role in group.roles.all():
                    if set(stored_permissions).intersection(set(self.get_inherited_permissions(role=role, obj=obj))):
                        logger.debug(
                            'Permissions "%s" on "%s" granted to user "%s" through role "%s" via inherited ACL',
                            permissions, obj, user, role
                        )
                        return True

                    user_roles.append(role)

            if not self.filter(content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk, permissions__in=stored_permissions, role__in=user_roles).exists():
                logger.debug(
                    'Permissions "%s" on "%s" denied for user "%s"',
                    permissions, obj, user
                )
                raise PermissionDenied(ugettext('Insufficient access for: %s') % obj)

            logger.debug(
                'Permissions "%s" on "%s" granted to user "%s" through roles "%s" by direct ACL',
                permissions, obj, user, user_roles
            )

    def filter_by_access(self, permission, user, queryset):
        if user.is_superuser or user.is_staff:
            logger.debug(
                'Unfiltered queryset returned to user "%s" as superuser or staff',
                user
            )
            return queryset

        try:
            Permission.check_permissions(
                requester=user, permissions=(permission,)
            )
        except PermissionDenied:
            user_roles = []
            for group in user.groups.all():
                for role in group.roles.all():
                    user_roles.append(role)

            try:
                parent_accessor = ModelPermission.get_inheritance(
                    model=queryset.model
                )
            except KeyError:
                parent_acl_query = Q()
            else:
                instance = queryset.first()
                if instance:
                    parent_object = return_related(
                        instance=instance, related_field=parent_accessor
                    )

                    try:
                        # Try to see if parent_object is a function
                        parent_object()
                    except TypeError:
                        # Is not a function, try it as a field
                        parent_content_type = ContentType.objects.get_for_model(
                            parent_object
                        )
                        parent_queryset = self.filter(
                            content_type=parent_content_type, role__in=user_roles,
                            permissions=permission.stored_permission
                        )
                        parent_acl_query = Q(
                            **{
                                '{}__pk__in'.format(
                                    parent_accessor
                                ): parent_queryset.values_list(
                                    'object_id', flat=True
                                )
                            }
                        )
                    else:
                        # Is a function. Can't perform Q object filtering.
                        # Perform iterative filtering.
                        result = []
                        for entry in queryset:
                            try:
                                self.check_access(permissions=permission, user=user, obj=entry)
                            except PermissionDenied:
                                pass
                            else:
                                result.append(entry.pk)

                        return queryset.filter(pk__in=result)
                else:
                    parent_acl_query = Q()

            # Directly granted access
            content_type = ContentType.objects.get_for_model(queryset.model)
            acl_query = Q(pk__in=self.filter(
                content_type=content_type, role__in=user_roles,
                permissions=permission.stored_permission
            ).values_list('object_id', flat=True))
            logger.debug(
                'Filtered queryset returned to user "%s" based on roles "%s"',
                user, user_roles
            )
            return queryset.filter(parent_acl_query | acl_query)
        else:
            return queryset

    def get_inherited_permissions(self, role, obj):
        try:
            instance = obj.first()
        except AttributeError:
            instance = obj
        else:
            if not instance:
                return StoredPermission.objects.none()

        try:
            parent_accessor = ModelPermission.get_inheritance(type(instance))
        except KeyError:
            return StoredPermission.objects.none()
        else:
            try:
                parent_object = return_attrib(
                    obj=instance, attrib=parent_accessor
                )
            except AttributeError:
                # Parent accessor is not an attribute, try it as a related
                # field.
                parent_object = return_related(
                    instance=instance, related_field=parent_accessor
                )
            content_type = ContentType.objects.get_for_model(parent_object)
            try:
                return self.get(
                    role=role, content_type=content_type,
                    object_id=parent_object.pk
                ).permissions.all()
            except self.model.DoesNotExist:
                return StoredPermission.objects.none()

    def grant(self, permission, role, obj):
        class_permissions = ModelPermission.get_for_class(klass=obj.__class__)
        if permission not in class_permissions:
            raise PermissionNotValidForClass

        content_type = ContentType.objects.get_for_model(model=obj)
        acl, created = self.get_or_create(
            content_type=content_type, object_id=obj.pk,
            role=role
        )

        acl.permissions.add(permission.stored_permission)

    def revoke(self, permission, role, obj):
        content_type = ContentType.objects.get_for_model(model=obj)
        acl, created = self.get_or_create(
            content_type=content_type, object_id=obj.pk,
            role=role
        )

        acl.permissions.remove(permission.stored_permission)

        if acl.permissions.count() == 0:
            acl.delete()

    def restrict_queryset(self, permission, queryset, user):
        if not user.is_authenticated:
            return queryset.none()

        # Check directly granted permission via a role
        try:
            Permission.check_user_permissions(
                permissions=(permission,), user=user
            )
        except PermissionDenied:
            acl_filters = self._get_acl_filters(
                queryset=queryset,
                stored_permission=permission.stored_permission, user=user
            )

            final_query = None
            for acl_filter in acl_filters:
                if final_query is None:
                    final_query = acl_filter
                else:
                    final_query = final_query | acl_filter

            return queryset.filter(final_query)
        else:
            # User has direct permission assignment via a role, is superuser or
            # is staff. Return the entire queryset.
            return queryset
