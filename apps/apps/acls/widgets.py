from __future__ import unicode_literals

from django.apps import apps
from django import forms
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
#from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404

from common.utils import get_str_from_aware

import logging
logger = logging.getLogger(__name__)

def get_permission_string(document):
    """
    Return a formated representation of a document's permissions
    """

    StoredPermission = apps.get_model(
        app_label='permissions', model_name='StoredPermission'
    )   
 
    ContentType = apps.get_model(
        app_label='contenttypes', model_name='ContentType'
    )

    AccessControlList = apps.get_model(
        app_label='acls', model_name='AccessControlList'
    )
 
    object_content_type = get_object_or_404(
        ContentType, app_label='documents',
        model='document'
    )  
    acl = AccessControlList.objects.filter(
        content_type=object_content_type,
        object_id=document.pk
    )
    sp = StoredPermission.objects.get(name='acl_edit')
    
    html_string = ""
    for item in acl:
        if sp in item.permissions.all():
            html_string += '<span class="rw-permission">'+ str(item.role) +' </span><br />'
        else:
            html_string += '<span class="ro-permission">'+ str(item.role) +' </span><br />'
    
    return mark_safe(html_string)    


