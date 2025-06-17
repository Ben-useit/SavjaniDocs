from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy as _

from events import EventTypeNamespace

namespace = EventTypeNamespace(name='regsister', label=_('Register'))

event_file_no_activated = namespace.add_event_type(
    label=_('File No. activated'), name='file_no_activate'
)
event_file_no_requested = namespace.add_event_type(
    label=_('File No. requested'), name='file_no_request'
)
event_file_no_created = namespace.add_event_type(
    label=_('File No. created'), name='file_no__create'
)
event_file_no_document_added= namespace.add_event_type(
    label=_('File No. Document added'), name='file_no_document_added'
)
event_file_no_transferred= namespace.add_event_type(
    label=_('File No. transferred'), name='file_no_transferred'
)
event_file_no_closed= namespace.add_event_type(
    label=_('File No. closed'), name='file_no_closed'
)
event_file_no_not_active= namespace.add_event_type(
    label=_('Changed status to not active'), name='file_no_not_active'
)
event_file_no_transferred_to_client= namespace.add_event_type(
    label=_('File No. transferred to client'), name='file_transferred_to_client'
)
