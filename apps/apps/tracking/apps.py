from __future__ import absolute_import, unicode_literals

from django.apps import apps
from django.utils.translation import ugettext_lazy as _
from events import ModelEventType
from common import (
    MayanAppConfig, menu_main,menu_object, menu_multi_item,
)
from common.classes import ModelAttribute
from navigation import SourceColumn


from register.menus import menu_register
from .links import (
    link_tracking_list,link_tracking_edit, link_tracking_start_tracking,
    link_tracking_retain_or_transfer, link_tracking_closure_letter,
    link_tracking_instructions, link_tracking_client,
    link_tracking_notice, link_tracking_receipt,
    link_tracking_completion,
    link_tracking_delete, link_tracking_stop_tracking
)
from .events import event_tracking_modified
from .widgets import AttribWidget

class TrackingApp(MayanAppConfig):
    has_rest_api = False
    has_tests = False
    name = 'tracking'
    verbose_name = _('Tracking')

    def ready(self):
        super(TrackingApp, self).ready()

        from actstream import registry
        TrackedFile = self.get_model('TrackedFile')

        SourceColumn(
            source=TrackedFile,label='File No',
            func=lambda context: context['object'].file.file_no
        )
        SourceColumn(
            source=TrackedFile,label='Parties',
            func=lambda context: context['object'].file.parties
        )
        SourceColumn(
            source=TrackedFile,label='Opened',
            func=lambda context: context['object'].get_date(context['object'].file.opened)
        )
        SourceColumn(
            source=TrackedFile,label='Retain/ Transfer',
            func=lambda context: AttribWidget(
                attrib=context['object'].get_retain_or_transfer_display()).render()
        )
        SourceColumn(
            source=TrackedFile, label=_('Closure Letter'),
            func=lambda context: AttribWidget(
                attrib=context['object'].get_date(context['object'].closure_letter, no=False)).render()
        )
        SourceColumn(
            source=TrackedFile, label=_('Instructions received'),
            func=lambda context: AttribWidget(
                attrib=context['object'].get_date(context['object'].instructions, no=False)).render()
        )
        SourceColumn(
            source=TrackedFile, label=_('File to ex. Lawyer'),
            func=lambda context: AttribWidget(
                attrib=context['object'].get_client(name=True)).render()

        )
        SourceColumn(
            source=TrackedFile, label=_('Notice'),
            func=lambda context: AttribWidget(
                attrib=context['object'].get_date(context['object'].notice, no=False)).render()
        )
        SourceColumn(
            source=TrackedFile, label=_('Receipt'),
            func=lambda context: AttribWidget(
                attrib=context['object'].get_date(context['object'].receipt, no=False)).render()
        )
        SourceColumn(
            source=TrackedFile, label=_('Completion'),
            func=lambda context: AttribWidget(
                attrib=context['object'].get_date(context['object'].completion, no=False)).render()
        )

        menu_register.bind_links(
            links=(
                link_tracking_list,
            )
        )

        menu_multi_item.bind_links(
            links=(
                link_tracking_start_tracking,
            ), sources=('register:register_list',)
        )
        menu_multi_item.bind_links(
            links=(
                link_tracking_retain_or_transfer, link_tracking_closure_letter,
                link_tracking_instructions, link_tracking_client,
                link_tracking_notice, link_tracking_receipt,
                link_tracking_completion, link_tracking_stop_tracking
            ), sources=('tracking:tracking_list',)
        )
        menu_object.bind_links(
            links=(
                link_tracking_edit,link_tracking_delete,
            ),
            sources=(TrackedFile,)
        )
        ModelEventType.register(
            model=TrackedFile, event_types=(
                event_tracking_modified,
            )
        )

        registry.register(TrackedFile)


