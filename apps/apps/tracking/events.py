from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy as _

from events import EventTypeNamespace

namespace = EventTypeNamespace(name='tracking', label=_('Tracking'))

event_tracking_modified = namespace.add_event_type(
    label=_('File tracking modified'), name='file_tracking_modified'
)
