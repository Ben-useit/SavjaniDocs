from __future__ import absolute_import, unicode_literals

from datetime import timedelta

from kombu import Exchange, Queue

from django.db.models.signals import post_delete
from django.utils.translation import ugettext_lazy as _

from acls import ModelPermission
from acls.links import link_acl_list, link_acl_edit_list_with_icon
from acls.permissions import permission_acl_edit, permission_acl_view
from common import (
    MayanAppConfig, MissingItem, menu_facet, menu_main, menu_object,
    menu_secondary, menu_setup, menu_sidebar, menu_multi_item, menu_tools
)
from common.classes import ModelField
from common.dashboards import dashboard_main
from common.signals import post_initial_setup
from common.widgets import TwoStateWidget
from converter.links import link_transformation_list
from converter.permissions import (
    permission_transformation_create,
    permission_transformation_delete, permission_transformation_edit,
    permission_transformation_view,
)
from events import ModelEventType
from events.links import (
    link_events_for_object, link_object_event_types_user_subcriptions_list,
)
from events.permissions import permission_events_view
from mayan.celery import app
from navigation import SourceColumn
from rest_api.fields import DynamicSerializerField

from .dashboard_widgets import (
    DashboardWidgetDocumentPagesTotal, DashboardWidgetDocumentsInTrash,
    DashboardWidgetDocumentsNewThisMonth,
    DashboardWidgetDocumentsPagesNewThisMonth, DashboardWidgetDocumentsTotal,
    DashboardWidgetDocumentsTypesTotal,
)
from .events import (
    event_document_create, event_document_download,
    event_document_properties_edit, event_document_type_change,
    event_document_type_created, event_document_type_edited,
    event_document_new_version, event_document_version_revert,
    event_document_view,event_document_shared
)
from .handlers import (
    create_default_document_type, handler_remove_empty_duplicates_lists,
    handler_scan_duplicates_for,
)
from .links import (
    link_clear_image_cache, link_document_clear_transformations,
    link_document_clone_transformations, link_document_delete,
    link_document_document_type_edit, link_document_download,
    link_document_duplicates_list, link_document_edit,
    link_document_favorites_add, link_document_favorites_remove,
    link_document_list, link_document_list_deleted,
    link_document_list_favorites, link_document_list_recent_access,
    link_document_list_recent_added,
    link_document_multiple_clear_transformations,
    link_document_multiple_delete, link_document_multiple_document_type_edit,
    link_document_multiple_download, link_document_multiple_favorites_add,
    link_document_multiple_favorites_remove, link_document_multiple_restore,
    link_document_multiple_trash, link_document_multiple_update_page_count,
    link_document_page_navigation_first, link_document_page_navigation_last,
    link_document_page_navigation_next, link_document_page_navigation_previous,
    link_document_page_return, link_document_page_rotate_left,
    link_document_page_rotate_right, link_document_page_view,
    link_document_page_view_reset, link_document_page_zoom_in,
    link_document_page_zoom_out, link_document_pages, link_document_preview,
    link_document_print, link_document_properties, link_document_quick_download,
    link_document_restore, link_document_trash, link_document_type_create,
    link_document_type_delete, link_document_type_edit,
    link_document_type_filename_create, link_document_type_filename_delete,
    link_document_type_filename_edit, link_document_type_filename_list,
    link_document_type_list, link_document_type_setup,
    link_document_update_page_count, link_document_version_download,
    link_document_version_list, link_document_version_return_document,
    link_document_version_return_list, link_document_version_revert,
    link_document_version_view, link_duplicated_document_list,
    link_duplicated_document_scan, link_trash_can_empty
)
from .literals import (
    CHECK_DELETE_PERIOD_INTERVAL, CHECK_TRASH_PERIOD_INTERVAL,
    DELETE_STALE_STUBS_INTERVAL
)
from .menus import menu_documents
from .permissions import (
    permission_document_create, permission_document_delete,
    permission_document_download, permission_document_edit,
    permission_document_new_version, permission_document_print,
    permission_document_properties_edit, permission_document_restore,
    permission_document_trash, permission_document_type_delete,
    permission_document_type_edit, permission_document_type_view,
    permission_document_version_revert, permission_document_version_view,
    permission_document_view
)
from .queues import *  # NOQA
# Just import to initialize the search models
from .search import document_search, document_page_search  # NOQA
from .signals import post_version_upload
from .statistics import *  # NOQA
from .widgets import (
    DocumentPageThumbnailWidget, widget_document_page_number,
    widget_document_version_page_number
)

from sapitwa.links import  link_document_statistics
class DocumentsApp(MayanAppConfig):
    has_rest_api = True
    has_tests = True
    name = 'documents'
    verbose_name = _('Documents')

    def ready(self):
        super(DocumentsApp, self).ready()
        from actstream import registry

        DeletedDocument = self.get_model('DeletedDocument')
        Document = self.get_model('Document')
        DocumentPage = self.get_model('DocumentPage')
        DocumentPageResult = self.get_model('DocumentPageResult')
        DocumentType = self.get_model('DocumentType')
        DocumentTypeFilename = self.get_model('DocumentTypeFilename')
        DocumentVersion = self.get_model('DocumentVersion')
        DuplicatedDocument = self.get_model('DuplicatedDocument')

        DynamicSerializerField.add_serializer(
            klass=Document,
            serializer_class='documents.serializers.DocumentSerializer'
        )

        MissingItem(
            label=_('Create a document type'),
            description=_(
                'Every uploaded document must be assigned a document type, '
                'it is the basic way Mayan EDMS categorizes documents.'
            ), condition=lambda: not DocumentType.objects.exists(),
            view='documents:document_type_list'
        )

        ModelField(Document, name='description')
        ModelField(Document, name='date_added')
        ModelField(Document, name='deleted_date_time')
        ModelField(Document, name='document_type__label')
        ModelField(Document, name='in_trash')
        ModelField(Document, name='is_stub')
        ModelField(Document, name='label')
        ModelField(Document, name='language')
        ModelField(Document, name='uuid')
        ModelField(
            Document, name='versions__checksum'
        )
        ModelField(
            Document, label=_('Versions comment'), name='versions__comment'
        )
        ModelField(
            Document, label=_('Versions encoding'), name='versions__encoding'
        )
        ModelField(
            Document, label=_('Versions mime type'), name='versions__mimetype'
        )
        ModelField(
            Document, label=_('Versions timestamp'), name='versions__timestamp'
        )

        ModelEventType.register(
            model=DocumentType, event_types=(
                event_document_create,
                event_document_type_created,
                event_document_type_edited,
            )
        )
        ModelEventType.register(
            model=Document, event_types=(
                event_document_download, event_document_properties_edit,
                event_document_type_change, event_document_new_version,
                event_document_version_revert, event_document_view,event_document_shared
            )
        )

        ModelPermission.register(
            model=Document, permissions=(
                permission_acl_edit, permission_acl_view,
                permission_document_delete, permission_document_download,
                permission_document_edit, permission_document_new_version,
                permission_document_print, permission_document_properties_edit,
                permission_document_restore, permission_document_trash,
                permission_document_version_revert,
                permission_document_version_view, permission_document_view,
                permission_events_view, permission_transformation_create,
                permission_transformation_delete,
                permission_transformation_edit, permission_transformation_view,
            )
        )

        ModelPermission.register(
            model=DocumentType, permissions=(
                permission_document_create, permission_document_type_delete,
                permission_document_type_edit, permission_document_type_view
            )
        )

        ModelPermission.register_proxy(
            source=Document, model=DocumentType,
        )

        ModelPermission.register_inheritance(
            model=Document, related='document_type',
        )
        ModelPermission.register_inheritance(
            model=DocumentPage, related='document_version__document',
        )
        ModelPermission.register_inheritance(
            model=DocumentPageResult, related='document_version__document',
        )
        ModelPermission.register_inheritance(
            model=DocumentTypeFilename, related='document_type',
        )
        ModelPermission.register_inheritance(
            model=DocumentVersion, related='document',
        )

        # Document and document page thumbnail widget
        document_page_thumbnail_widget = DocumentPageThumbnailWidget()

        # Document
        SourceColumn(
            source=Document, label=_('Thumbnail'),
            func=lambda context: document_page_thumbnail_widget.render(
                instance=context['object']
            )
        )
        SourceColumn(
            source=Document, attribute='document_type'
        )
        SourceColumn(
            source=Document, label=_('Pages'),
            func=lambda context: widget_document_page_number(
                document=context['object']
            )
        )

        # DocumentPage
        SourceColumn(
            source=DocumentPage, label=_('Thumbnail'),
            func=lambda context: document_page_thumbnail_widget.render(
                instance=context['object']
            )
        )

        SourceColumn(
            source=DocumentPageResult, label=_('Thumbnail'),
            func=lambda context: document_page_thumbnail_widget.render(
                instance=context['object']
            )
        )

        SourceColumn(
            source=DocumentPageResult, label=_('Type'),
            attribute='document_version.document.document_type'
        )

        # DocumentType
        SourceColumn(
            source=DocumentType, label=_('Documents'),
            func=lambda context: context['object'].get_document_count(
                user=context['request'].user
            )
        )

        SourceColumn(
            source=DocumentTypeFilename, label=_('Enabled'),
            func=lambda context: TwoStateWidget(
                state=context['object'].enabled
            ).render()
        )

        # DeletedDocument
        SourceColumn(
            source=DeletedDocument, label=_('Thumbnail'),
            func=lambda context: document_page_thumbnail_widget.render(
                instance=context['object']
            )
        )

        SourceColumn(
            source=DeletedDocument, attribute='document_type'
        )
        SourceColumn(
            source=DeletedDocument, attribute='deleted_date_time'
        )

        # DocumentVersion
        SourceColumn(
            source=DocumentVersion, label=_('Thumbnail'),
            func=lambda context: document_page_thumbnail_widget.render(
                instance=context['object']
            )
        )
        SourceColumn(
            source=DocumentVersion, attribute='timestamp'
        )
        SourceColumn(
            source=DocumentVersion, label=_('Pages'),
            func=lambda context: widget_document_version_page_number(
                document_version=context['object']
            )
        )
        SourceColumn(
            source=DocumentVersion, attribute='mimetype'
        )
        SourceColumn(
            source=DocumentVersion, attribute='encoding'
        )
        SourceColumn(
            source=DocumentVersion, attribute='comment'
        )

        # DuplicatedDocument
        SourceColumn(
            source=DuplicatedDocument, label=_('Thumbnail'),
            func=lambda context: document_page_thumbnail_widget.render(
                instance=context['object'].document
            )
        )
        SourceColumn(
            source=DuplicatedDocument, label=_('Duplicates'),
            func=lambda context: context['object'].documents.count()
        )

        app.conf.CELERYBEAT_SCHEDULE.update(
            {
                'task_check_delete_periods': {
                    'task': 'documents.tasks.task_check_delete_periods',
                    'schedule': timedelta(
                        seconds=CHECK_DELETE_PERIOD_INTERVAL
                    ),
                },
                'task_check_trash_periods': {
                    'task': 'documents.tasks.task_check_trash_periods',
                    'schedule': timedelta(seconds=CHECK_TRASH_PERIOD_INTERVAL),
                },
                'task_delete_stubs': {
                    'task': 'documents.tasks.task_delete_stubs',
                    'schedule': timedelta(seconds=DELETE_STALE_STUBS_INTERVAL),
                },
            }
        )

        app.conf.CELERY_QUEUES.extend(
            (
                Queue(
                    'converter', Exchange('converter'),
                    routing_key='converter', delivery_mode=1
                ),
                Queue(
                    'documents_periodic', Exchange('documents_periodic'),
                    routing_key='documents_periodic', delivery_mode=1
                ),
                Queue('uploads', Exchange('uploads'), routing_key='uploads'),
                Queue(
                    'documents', Exchange('documents'), routing_key='documents'
                ),
            )
        )

        app.conf.CELERY_ROUTES.update(
            {
                'mailer.tasks.task_send': {
                    'queue': 'mailing'
                },
            }
        )

        app.conf.CELERY_ROUTES.update(
            {
                'documents.tasks.task_check_delete_periods': {
                    'queue': 'documents_periodic'
                },
                'documents.tasks.task_check_trash_periods': {
                    'queue': 'documents_periodic'
                },
                'documents.tasks.task_clean_empty_duplicate_lists': {
                    'queue': 'documents'
                },
                'documents.tasks.task_clear_image_cache': {
                    'queue': 'tools'
                },
                'documents.tasks.task_delete_document': {
                    'queue': 'documents'
                },
                'documents.tasks.task_delete_stubs': {
                    'queue': 'documents_periodic'
                },
                'documents.tasks.task_generate_document_page_image': {
                    'queue': 'converter'
                },
                'documents.tasks.task_scan_duplicates_all': {
                    'queue': 'tools'
                },
                'documents.tasks.task_scan_duplicates_for': {
                    'queue': 'uploads'
                },
                'documents.tasks.task_update_page_count': {
                    'queue': 'uploads'
                },
                'documents.tasks.task_upload_new_version': {
                    'queue': 'uploads'
                },
                'documents.task_send': {
                    'queue': 'mailing'
                },
            }
        )

        dashboard_main.add_widget(
            widget=DashboardWidgetDocumentsTotal, order=0
        )
        dashboard_main.add_widget(
            widget=DashboardWidgetDocumentPagesTotal, order=1
        )
        dashboard_main.add_widget(
            widget=DashboardWidgetDocumentsInTrash, order=2
        )
        dashboard_main.add_widget(
            widget=DashboardWidgetDocumentsTypesTotal, order=3
        )
        dashboard_main.add_widget(
            widget=DashboardWidgetDocumentsNewThisMonth, order=4
        )
        dashboard_main.add_widget(
            widget=DashboardWidgetDocumentsPagesNewThisMonth, order=5
        )

        menu_documents.bind_links(
            links=(
                link_document_list_recent_access,
                link_document_list_recent_added, link_document_list_favorites,
                link_document_list, link_document_list_deleted,
                link_duplicated_document_list,
            )
        )

        menu_main.bind_links(links=(menu_documents,), position=0)

        menu_setup.bind_links(links=(link_document_type_setup,))
        menu_tools.bind_links(
            links=(link_clear_image_cache, link_duplicated_document_scan)
        )

        # Document type links
        menu_object.bind_links(
            links=(
                link_document_type_edit, link_document_type_filename_list,
                link_acl_list, link_object_event_types_user_subcriptions_list,
                link_document_type_delete,
                link_events_for_object,
            ), sources=(DocumentType,)
        )
        menu_object.bind_links(
            links=(
                link_document_type_filename_edit,
                link_document_type_filename_delete
            ), sources=(DocumentTypeFilename,)
        )
        menu_secondary.bind_links(
            links=(link_document_type_list, link_document_type_create),
            sources=(
                DocumentType, 'documents:document_type_create',
                'documents:document_type_list'
            )
        )
        menu_sidebar.bind_links(
            links=(link_document_type_filename_create,),
            sources=(
                DocumentTypeFilename, 'documents:document_type_filename_list',
                'documents:document_type_filename_create'
            )
        )
        menu_sidebar.bind_links(
            links=(link_trash_can_empty,),
            sources=(
                'documents:document_list_deleted', 'documents:trash_can_empty'
            )
        )

        # Document object links
        menu_object.bind_links(
            links=(
                link_document_favorites_add, link_document_favorites_remove,
                link_document_edit, link_document_document_type_edit,
                link_document_print, link_document_trash,
                link_document_quick_download, link_document_download,
                link_document_clear_transformations,
                link_document_clone_transformations,
                link_document_update_page_count,
            ), sources=(Document,)
        )
        menu_object.bind_links(
            links=(link_document_restore, link_document_delete),
            sources=(DeletedDocument,)
        )

        # Document facet links
        menu_facet.bind_links(
            links=(link_document_duplicates_list, link_acl_list,link_acl_edit_list_with_icon),
            sources=(Document,)
        )
        menu_facet.bind_links(
            links=(link_document_preview,), sources=(Document,), position=0
        )
        menu_facet.bind_links(
            links=(link_document_properties,), sources=(Document,), position=2
        )
        menu_facet.bind_links(
            links=(
                link_events_for_object,
                link_object_event_types_user_subcriptions_list,
                link_document_version_list,
            ), sources=(Document,), position=2
        )
        menu_facet.bind_links(links=(link_document_pages,), sources=(Document,))

        # Document actions
        menu_object.bind_links(
            links=(
                link_document_version_revert, link_document_version_download
            ),
            sources=(DocumentVersion,)
        )
        menu_multi_item.bind_links(
            links=(
                link_document_multiple_favorites_add,
                link_document_multiple_favorites_remove,
                link_document_multiple_clear_transformations,
                link_document_multiple_trash, link_document_multiple_download,
                link_document_multiple_update_page_count,
                link_document_multiple_document_type_edit,
            ), sources=(Document,)
        )
        menu_multi_item.bind_links(
            links=(
                link_document_multiple_restore, link_document_multiple_delete
            ), sources=(DeletedDocument,)
        )

        # Document pages
        menu_facet.add_unsorted_source(source=DocumentPage)
        menu_facet.bind_links(
            links=(
                link_document_page_rotate_left,
                link_document_page_rotate_right, link_document_page_zoom_in,
                link_document_page_zoom_out, link_document_page_view_reset
            ), sources=('documents:document_page_view',)
        )
        menu_facet.bind_links(
            links=(link_document_page_return, link_document_page_view),
            sources=(DocumentPage,)
        )
        menu_facet.bind_links(
            links=(
                link_document_page_navigation_first,
                link_document_page_navigation_previous,
                link_document_page_navigation_next,
                link_document_page_navigation_last, link_transformation_list
            ), sources=(DocumentPage,)
        )
        menu_object.bind_links(
            links=(link_transformation_list,), sources=(DocumentPage,)
        )

        # Document versions
        menu_facet.bind_links(
            links=(
                link_document_version_return_document,
                link_document_version_return_list
            ), sources=(DocumentVersion,)
        )
        menu_facet.bind_links(
            links=(link_document_version_view,), sources=(DocumentVersion,)
        )

        post_delete.connect(
            dispatch_uid='handler_remove_empty_duplicates_lists',
            receiver=handler_remove_empty_duplicates_lists,
            sender=Document,
        )
        post_initial_setup.connect(
            create_default_document_type,
            dispatch_uid='create_default_document_type'
        )
        post_version_upload.connect(
            handler_scan_duplicates_for,
            dispatch_uid='handler_scan_duplicates_for',
        )

        registry.register(DeletedDocument)
        registry.register(Document)
        registry.register(DocumentType)
        registry.register(DocumentVersion)
