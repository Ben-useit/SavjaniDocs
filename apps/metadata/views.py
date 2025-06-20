from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_text
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _, ungettext

from acls.models import AccessControlList
from common.generics import (
    FormView, MultipleObjectFormActionView, SingleObjectCreateView,
    SingleObjectDeleteView, SingleObjectEditView, SingleObjectListView
)
from documents.models import Document, DocumentType
from documents.permissions import (
    permission_document_type_edit
)

from .api import save_metadata_list
from .forms import (
    DocumentAddMetadataForm, DocumentMetadataFormSet,
    DocumentMetadataRemoveFormSet,
    DocumentTypeMetadataTypeRelationshipFormSet, MetadataTypeForm
)
from .icons import (
    icon_document_metadata_add, icon_document_metadata_edit,
    icon_document_metadata_remove, icon_metadata
)
from .links import (
    link_metadata_add, link_metadata_multiple_add,
    link_setup_metadata_type_create
)
from .models import DocumentMetadata, MetadataType
from .permissions import (
    permission_metadata_document_add, permission_metadata_document_edit,
    permission_metadata_document_remove, permission_metadata_document_view,
    permission_metadata_type_create, permission_metadata_type_delete,
    permission_metadata_type_edit, permission_metadata_type_view
)


class DocumentMetadataAddView(MultipleObjectFormActionView):
    form_class = DocumentAddMetadataForm
    model = Document
    object_permission = permission_metadata_document_add
    success_message = _('Metadata add request performed on %(count)d document')
    success_message_plural = _(
        'Metadata add request performed on %(count)d documents'
    )

    def dispatch(self, request, *args, **kwargs):
        result = super(
            DocumentMetadataAddView, self
        ).dispatch(request, *args, **kwargs)

        queryset = self.get_queryset()

        for document in queryset:
            document.add_as_recent_document_for_user(request.user)

        if len(set([document.document_type.pk for document in queryset])) > 1:
            messages.error(
                request, _('Selected documents must be of the same type.')
            )
            return HttpResponseRedirect(self.previous_url)

        return result

    def form_valid(self, form):
        result = super(DocumentMetadataAddView, self).form_valid(form=form)

        queryset = self.get_queryset()

        if self.action_count == 1:
            return HttpResponseRedirect(
                reverse('metadata:metadata_edit', args=(queryset.first().pk,)),
            )
        elif self.action_count > 1:
            return HttpResponseRedirect(
                '%s?%s' % (
                    reverse('metadata:metadata_multiple_edit'),
                    urlencode(
                        {
                            'id_list': ','.join(
                                map(
                                    force_text,
                                    queryset.values_list('pk', flat=True)
                                )
                            )
                        }
                    )
                )
            )

        return result

    def get_extra_context(self):
        queryset = self.get_queryset()
        result = {
            'submit_icon_class': icon_document_metadata_add,
            'submit_label': _('Add'),
            'title': ungettext(
                'Add metadata types to document',
                'Add metadata types to documents',
                queryset.count()
            )
        }

        if queryset.count() == 1:
            result.update(
                {
                    'object': queryset.first(),
                    'title': _(
                        'Add metadata types to document: %s'
                    ) % queryset.first()
                }
            )

        return result

    def get_form_extra_kwargs(self):
        queryset = self.get_queryset()
        result = {}

        if queryset.count():
            result.update(
                {
                    'document_type': queryset.first().document_type,
                }
            )

        if queryset.count() == 1:
            result.update(
                {
                    'queryset': MetadataType.objects.get_for_document_type(
                        document_type=queryset.first().document_type
                    ).exclude(
                        pk__in=MetadataType.objects.get_for_document(
                            document=queryset.first()
                        )
                    )
                }
            )

        return result

    def object_action(self, form, instance):
        for metadata_type in form.cleaned_data['metadata_type']:
            try:
                created = False
                try:
                    DocumentMetadata.objects.get(
                        document=instance,
                        metadata_type=metadata_type,
                    )
                except DocumentMetadata.DoesNotExist:
                    document_metadata = DocumentMetadata(
                        document=instance,
                        metadata_type=metadata_type,
                    )
                    document_metadata.save(_user=self.request.user)
                    created = True
            except Exception as exception:
                messages.error(
                    self.request,
                    _(
                        'Error adding metadata type '
                        '"%(metadata_type)s" to document: '
                        '%(document)s; %(exception)s'
                    ) % {
                        'metadata_type': metadata_type,
                        'document': instance,
                        'exception': ', '.join(
                            getattr(exception, 'messages', exception)
                        )
                    }
                )
            else:
                if created:
                    messages.success(
                        self.request,
                        _(
                            'Metadata type: %(metadata_type)s '
                            'successfully added to document %(document)s.'
                        ) % {
                            'metadata_type': metadata_type,
                            'document': instance
                        }
                    )
                else:
                    messages.warning(
                        self.request, _(
                            'Metadata type: %(metadata_type)s already '
                            'present in document %(document)s.'
                        ) % {
                            'metadata_type': metadata_type,
                            'document': instance
                        }
                    )


class DocumentMetadataEditView(MultipleObjectFormActionView):
    form_class = DocumentMetadataFormSet
    model = Document
    object_permission = permission_metadata_document_edit
    success_message = _(
        'Metadata edit request performed on %(count)d document'
    )
    success_message_plural = _(
        'Metadata edit request performed on %(count)d documents'
    )

    def dispatch(self, request, *args, **kwargs):
        result = super(
            DocumentMetadataEditView, self
        ).dispatch(request, *args, **kwargs)

        queryset = self.get_queryset()

        for document in queryset:
            document.add_as_recent_document_for_user(request.user)

        if len(set([document.document_type.pk for document in queryset])) > 1:
            messages.error(
                request, _('Selected documents must be of the same type.')
            )
            return HttpResponseRedirect(self.previous_url)

        return result

    def form_valid(self, form):
        result = super(DocumentMetadataEditView, self).form_valid(form=form)

        queryset = self.get_queryset()

        if self.action_count == 1:
            return HttpResponseRedirect(
                reverse('metadata:metadata_edit', args=(queryset.first().pk,)),
            )
        elif self.action_count > 1:
            return HttpResponseRedirect(
                '%s?%s' % (
                    reverse('metadata:metadata_multiple_edit'),
                    urlencode(
                        {
                            'id_list': ','.join(
                                map(
                                    force_text, queryset.values_list(
                                        'pk', flat=True
                                    )
                                )
                            )
                        }
                    )
                )
            )

        return result

    def get_extra_context(self):
        queryset = self.get_queryset()

        id_list = ','.join(
            map(
                force_text,
                queryset.values_list('pk', flat=True)
            )
        )

        if queryset.count() == 1:
            no_results_main_link = link_metadata_add.resolve(
                context=RequestContext(
                    request=self.request, dict_={'object': queryset.first()}
                )
            )
        else:
            no_results_main_link = link_metadata_multiple_add.resolve(
                context=RequestContext(request=self.request)
            )
            no_results_main_link.url = '{}?id_list={}'.format(
                no_results_main_link.url, id_list
            )

        result = {
            'form_display_mode_table': True,
            'no_results_icon': icon_metadata,
            'no_results_main_link': no_results_main_link,
            'no_results_text': _(
                'Add metadata types available for this document\'s type '
                'and assign them corresponding values.'
            ),
            'no_results_title': _('There is no metadata to edit'),
            'submit_icon_class': icon_document_metadata_edit,
            'submit_label': _('Save'),
            'title': ungettext(
                'Edit document metadata',
                'Edit documents metadata',
                queryset.count()
            )
        }

        if queryset.count() == 1:
            result.update(
                {
                    'object': queryset.first(),
                    'title': _(
                        'Edit metadata for document: %s'
                    ) % queryset.first()
                }
            )

        return result

    def get_initial(self):
        queryset = self.get_queryset()

        metadata_dict = {}
        initial = []

        for document in queryset:
            document.add_as_recent_document_for_user(self.request.user)

            for document_metadata in document.metadata.all():
                metadata_dict.setdefault(
                    document_metadata.metadata_type, set()
                )

                if document_metadata.value:
                    metadata_dict[
                        document_metadata.metadata_type
                    ].add(document_metadata.value)

        for key, value in metadata_dict.items():
            initial.append({
                'document_type': document.document_type,
                'metadata_type': key,
                'value': ', '.join(value) if value else '',
            })

        return initial

    def object_action(self, form, instance):
        errors = []
        for form in form.forms:
            if form.cleaned_data['update']:
                try:
                    save_metadata_list(
                        metadata_list=[form.cleaned_data], document=instance,
                        _user=self.request.user
                    )
                except Exception as exception:
                    errors.append(exception)

        for error in errors:
            if settings.DEBUG:
                raise
            else:
                if isinstance(error, ValidationError):
                    exception_message = ', '.join(error.messages)
                else:
                    exception_message = force_text(error)

                messages.error(
                    self.request, _(
                        'Error editing metadata for document: '
                        '%(document)s; %(exception)s.'
                    ) % {
                        'document': instance,
                        'exception': exception_message
                    }
                )
        else:
            messages.success(
                self.request,
                _(
                    'Metadata for document %s edited successfully.'
                ) % instance
            )


class DocumentMetadataListView(SingleObjectListView):
    def dispatch(self, request, *args, **kwargs):
        AccessControlList.objects.check_access(
            permissions=permission_metadata_document_view,
            user=self.request.user, obj=self.get_document()
        )

        return super(DocumentMetadataListView, self).dispatch(
            request, *args, **kwargs
        )

    def get_document(self):
        return get_object_or_404(Document, pk=self.kwargs['pk'])

    def get_extra_context(self):
        document = self.get_document()
        return {
            'hide_link': True,
            'object': document,
            'no_results_icon': icon_metadata,
            'no_results_main_link': link_metadata_add.resolve(
                context=RequestContext(
                    request=self.request, dict_={'object': document}
                )
            ),
            'no_results_text': _(
                'Add metadata types this document\'s type '
                'to be able to add them to individual documents. '
                'Once added to individual document, you can then edit their '
                'values.'
            ),
            'no_results_title': _('This document doesn\'t have any metadata'),
            'title': _('Metadata for document: %s') % document,
        }

    def get_object_list(self):
        return self.get_document().metadata.all()


class DocumentMetadataRemoveView(MultipleObjectFormActionView):
    form_class = DocumentMetadataRemoveFormSet
    model = Document
    object_permission = permission_metadata_document_remove
    success_message = _(
        'Metadata remove request performed on %(count)d document'
    )
    success_message_plural = _(
        'Metadata remove request performed on %(count)d documents'
    )

    def dispatch(self, request, *args, **kwargs):
        result = super(
            DocumentMetadataRemoveView, self
        ).dispatch(request, *args, **kwargs)

        queryset = self.get_queryset()

        for document in queryset:
            document.add_as_recent_document_for_user(request.user)

        if len(set([document.document_type.pk for document in queryset])) > 1:
            messages.error(
                request, _('Selected documents must be of the same type.')
            )
            return HttpResponseRedirect(self.previous_url)

        return result

    def form_valid(self, form):
        result = super(DocumentMetadataRemoveView, self).form_valid(form=form)

        queryset = self.get_queryset()

        if self.action_count == 1:
            return HttpResponseRedirect(
                reverse('metadata:metadata_edit', args=(queryset.first().pk,)),
            )
        elif self.action_count > 1:
            return HttpResponseRedirect(
                '%s?%s' % (
                    reverse('metadata:metadata_multiple_edit'),
                    urlencode(
                        {
                            'id_list': ','.join(
                                map(
                                    force_text,
                                    queryset.values_list('pk', flat=True)
                                )
                            )
                        }
                    )
                )
            )

        return result

    def get_extra_context(self):
        queryset = self.get_queryset()

        result = {
            'form_display_mode_table': True,
            'submit_icon_class': icon_document_metadata_remove,
            'submit_label': _('Remove'),
            'title': ungettext(
                'Remove metadata types from the document',
                'Remove metadata types from the documents',
                queryset.count()
            )
        }

        if queryset.count() == 1:
            result.update(
                {
                    'object': queryset.first(),
                    'title': _(
                        'Remove metadata types from the document: %s'
                    ) % queryset.first()
                }
            )

        return result

    def get_initial(self):
        queryset = self.get_queryset()

        metadata = {}
        for document in queryset:
            document.add_as_recent_document_for_user(self.request.user)

            for document_metadata in document.metadata.all():
                # Metadata value cannot be None here, fallback to an empty
                # string
                value = document_metadata.value or ''
                if document_metadata.metadata_type in metadata:
                    if value not in metadata[document_metadata.metadata_type]:
                        metadata[document_metadata.metadata_type].append(value)
                else:
                    metadata[document_metadata.metadata_type] = [value] if value else ''

        initial = []
        for key, value in metadata.items():
            initial.append(
                {
                    'document_type': queryset.first().document_type,
                    'metadata_type': key,
                    'value': ', '.join(value)
                }
            )
        return initial

    def object_action(self, form, instance):
        for form in form.forms:
            if form.cleaned_data['update']:
                metadata_type = get_object_or_404(
                    MetadataType, pk=form.cleaned_data['id']
                )
                try:
                    document_metadata = DocumentMetadata.objects.get(
                        document=instance, metadata_type=metadata_type
                    )
                    document_metadata.delete(_user=self.request.user)
                    messages.success(
                        self.request,
                        _(
                            'Successfully remove metadata type "%(metadata_type)s" from document: %(document)s.'
                        ) % {
                            'metadata_type': metadata_type,
                            'document': instance
                        }
                    )
                except Exception as exception:
                    messages.error(
                        self.request,
                        _(
                            'Error removing metadata type "%(metadata_type)s" from document: %(document)s; %(exception)s'
                        ) % {
                            'metadata_type': metadata_type,
                            'document': instance,
                            'exception': ', '.join(exception.messages)
                        }
                    )


# Setup views
class MetadataTypeCreateView(SingleObjectCreateView):
    extra_context = {'title': _('Create metadata type')}
    form_class = MetadataTypeForm
    model = MetadataType
    post_action_redirect = reverse_lazy('metadata:setup_metadata_type_list')
    view_permission = permission_metadata_type_create

    def get_save_extra_data(self):
        return {
            '_user': self.request.user,
        }


class MetadataTypeDeleteView(SingleObjectDeleteView):
    model = MetadataType
    object_permission = permission_metadata_type_delete
    post_action_redirect = reverse_lazy('metadata:setup_metadata_type_list')

    def get_extra_context(self):
        return {
            'delete_view': True,
            'object': self.get_object(),
            'title': _('Delete the metadata type: %s?') % self.get_object(),
        }


class MetadataTypeEditView(SingleObjectEditView):
    form_class = MetadataTypeForm
    model = MetadataType
    object_permission = permission_metadata_type_edit
    post_action_redirect = reverse_lazy('metadata:setup_metadata_type_list')

    def get_extra_context(self):
        return {
            'object': self.get_object(),
            'title': _('Edit metadata type: %s') % self.get_object(),
        }

    def get_save_extra_data(self):
        return {
            '_user': self.request.user,
        }


class MetadataTypeListView(SingleObjectListView):
    object_permission = permission_metadata_type_view

    def get_extra_context(self):
        return {
            'extra_columns': (
                {
                    'name': _('Internal name'),
                    'attribute': 'name',
                },
            ),
            'hide_link': True,
            'no_results_icon': icon_metadata,
            'no_results_main_link': link_setup_metadata_type_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Metadata types are users defined properties that can be '
                'assigned values. Once created they must be associated to '
                'document types, either as optional or required, for each. '
                'Setting a metadata type as required for a document type '
                'will block the upload of documents of that type until a '
                'metadata value is provided.'
            ),
            'no_results_title': _('There are no metadata types'),
            'title': _('Metadata types'),
        }

    def get_object_list(self):
        return MetadataType.objects.all()


class SetupDocumentTypeMetadataTypes(FormView):
    form_class = DocumentTypeMetadataTypeRelationshipFormSet
    main_model = 'document_type'
    model = DocumentType
    submodel = MetadataType

    def form_valid(self, form):
        try:
            for instance in form:
                instance.save()
        except Exception as exception:
            messages.error(
                self.request,
                _('Error updating relationship; %s') % exception
            )
        else:
            messages.success(
                self.request, _('Relationships updated successfully')
            )

        return super(
            SetupDocumentTypeMetadataTypes, self
        ).form_valid(form=form)

    def get_extra_context(self):
        return {
            'form_display_mode_table': True,
            'no_results_icon': icon_metadata,
            'no_results_main_link': link_setup_metadata_type_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Create metadata types to be able to associate them '
                'to this document type.'
            ),
            'no_results_title': _('There are no metadata types available'),
            'object': self.get_object(),
            'title': _(
                'Metadata types for document type: %s'
            ) % self.get_object()
        }

    def get_form_extra_kwargs(self):
        return {
            '_user': self.request.user,
        }

    def get_initial(self):
        obj = self.get_object()
        initial = []

        for element in self.get_queryset():
            initial.append({
                'document_type': obj,
                'main_model': self.main_model,
                'metadata_type': element,
            })
        return initial

    def get_object(self):
        obj = get_object_or_404(self.model, pk=self.kwargs['pk'])

        AccessControlList.objects.check_access(
            permissions=(permission_metadata_type_edit,),
            user=self.request.user, obj=obj
        )
        return obj

    def get_post_action_redirect(self):
        return reverse('documents:document_type_list')

    def get_queryset(self):
        queryset = self.submodel.objects.all()
        return AccessControlList.objects.filter_by_access(
            permission=permission_document_type_edit,
            user=self.request.user, queryset=queryset
        )


class SetupMetadataTypesDocumentTypes(SetupDocumentTypeMetadataTypes):
    main_model = 'metadata_type'
    model = MetadataType
    submodel = DocumentType

    def get_extra_context(self):
        return {
            'form_display_mode_table': True,
            'object': self.get_object(),
            'title': _(
                'Document types for metadata type: %s'
            ) % self.get_object()
        }

    def get_initial(self):
        obj = self.get_object()
        initial = []

        for element in self.get_queryset():
            initial.append({
                'document_type': element,
                'main_model': self.main_model,
                'metadata_type': obj,
            })
        return initial

    def get_post_action_redirect(self):
        return reverse('metadata:setup_metadata_type_list')
