from __future__ import unicode_literals
from datetime import timedelta
from django.utils.translation import ugettext_lazy as _
from django.template import Library
from django.contrib.auth.models import User
from django.utils.timesince import timesince
from django.utils import timezone
from django.utils.text import Truncator
from django.utils.safestring import mark_safe

from django.utils.safestring import mark_safe

register = Library()


# ~ @register.simple_tag
# ~ def get_client_name(obj, **kwargs):
    # ~ return obj.get_client_name()

@register.simple_tag
def get_doc_count(obj,user, **kwargs):
     return obj.get_document_count(user)
     
@register.simple_tag     
def get_status(obj,**kwargs):
	return mark_safe("<span class='btn btn-xs' style='background-color:"+obj.status.background_color+";color:"+obj.status.color+";'>"+obj.status.name+"</span>")
	
@register.simple_tag
def get_checklist(obj,**kwargs):
	if obj.has_checklist():
		return mark_safe("<span style='color:green;'><i class='fas fa-check'></i></span>")
	else:
		return mark_safe("<span style='background-color:green;color:grey;'></span>")

