from __future__ import unicode_literals

import os

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from smart_settings import Namespace

namespace = Namespace(name='register', label=_('Register'))

register_status_choices = namespace.add_setting(
    global_name='REGISTER_STATUS_CHOICES', default= (
    ('Active','Active'),
    ('Dormant','Dormant'),
    ('Not active', 'Not active'),
    ('Closed','Closed'),
    ('Transferred to client','Transferred to client'),
    ('Request to close','Request to close'),
    ('Request to transfer','Request to transfer'),
    ),
)

register_group_choices = namespace.add_setting(
    global_name='REGISTER_GROUP_CHOICES', default= (
    ('---','---'),
    ('Mota Engil', 'Mota Engil'),
    ('Pro Bono','Pro Bono'),
    ('Trademark','Trademark'),
    ),
)

quotation_status_choices = namespace.add_setting(
    global_name='QUOTATION_STATUS_CHOICES', default= (
    ('Active','Active'),
    ('Not active', 'Not active'),
    ('Closed','Closed'),
    ('Request to close','Request to close'),
    ('Request to transfer','Request to transfer'),
    ),
)

access_choices = namespace.add_setting(
    global_name='ACCESS_CHOICES', default= (

)

statistic_access_choices = namespace.add_setting(
    global_name='STATISTIC_ACCESS_CHOICES', default= (

)


abbr = namespace.add_setting(
    global_name='ABBR', default= {

)
