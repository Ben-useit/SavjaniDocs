from __future__ import unicode_literals
from datetime import timedelta
from django.utils.translation import ugettext_lazy as _
from django.template import Library
from django.contrib.auth.models import User
from django.utils.timesince import timesince
from django.utils import timezone
from django.utils.text import Truncator

from django.utils.safestring import mark_safe

register = Library()


@register.simple_tag
def get_matter_status(obj,status,lawyers, **kwargs):
    return obj.get_no_matters(status=status,lawyers=lawyers)

