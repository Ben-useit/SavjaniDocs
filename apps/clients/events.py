from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext_lazy as _

from events import EventTypeNamespace

namespace = EventTypeNamespace(label=_('Clients'), name='clients')

event_client_created = namespace.add_event_type(
    label=_('Client created'), name='client_created'
)
event_client_edited = namespace.add_event_type(
    label=_('Client edited'), name='client_edited'
)

