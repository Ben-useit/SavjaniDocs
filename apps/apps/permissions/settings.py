from __future__ import unicode_literals

import os

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from smart_settings import Namespace

namespace = Namespace(name='permissions', label=_('Permissions'))

role_types = namespace.add_setting(
    global_name='ROLE_TYPES1', default= (
    ('Single','Single'),
    ('Group', 'Group'),
    ('Register','Register'),
    ('Quotation','Quotation'),
    ),
)
