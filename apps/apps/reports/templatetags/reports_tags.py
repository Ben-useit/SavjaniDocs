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
def event_user_name(pk, **kwargs):
    user = User.objects.get(pk = pk)
    if user.get_full_name():
        return user.get_full_name()
    else:
        return _('System')


@register.simple_tag
def event_timestamp(obj, **kwargs):
    now = timezone.now()
    if obj < now - timedelta(seconds=604799):
        return obj.strftime("%d.%m.%Y")
    else:
        return timesince(obj, timezone.now()).encode('utf8').replace(b'\xc2\xa0', b' ').decode('utf8')

@register.simple_tag
def format_verb(verb, **kwargs):
    if verb == 'register.file_no_document_added':
        return mark_safe(
            '<span style="color:#970000"><i class="fas fa-angle-double-up"></i></span> %(verb)s' % {
                'verb': 'Document added'
            }
        )
    if verb == 'register.file_no_create':
        return mark_safe(
            '<span style="color:green"><i class="fas fa-star"></i></span> %(verb)s' % {
                'verb': 'Matter created'
            }
        )

    if verb == 'register.file_no_activate':
        return mark_safe(
            '<span style="color:green"><i class="fas fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Active'
            }
        )
    if verb == 'register.file_no_not_active':
        return mark_safe(
            '<span style="color:#f39c12"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Not Active'
            }
        )
    if verb == 'register.file_no_dormant':
        return mark_safe(
            '<span style="color:#888888"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Dormant'
            }
        )
    if verb == 'register.file_no_request':
        return mark_safe(
            '<span style="color:grey"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Requested'
            }
        )
    if verb == 'register.file_no_transferred':
        return mark_safe(
            '<span style="color:#02075D"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Transferred'
            }
        )
    if verb == 'register.file_no_closed':
        return mark_safe(
            '<span style="color:red"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Closed'
            }
        )
    if verb == 'register.file_transferred_to_client':
        return mark_safe(
            '<span style="color:blue"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Transferred to client'
            }
        )

@register.simple_tag
def matter_get_document_count(matter, user):
    return matter.get_document_count(user)

@register.simple_tag
def matter_get_transferred_from(action, user):
    if action.description.find(user.get_full_name()) > 20:
        return action.description.split('</b>')[0][20:]
    return ''

@register.simple_tag
def matter_get_transferred_to(action, user):
    if action.description.find(user.get_full_name()) == 20:
        return action.description.split('</b>')[1][7:]
    return ''

@register.simple_tag
def get_value_by_key(dic,key):
    if key in dic:
        return dic[key]
    return ''

@register.simple_tag
def matter_get_transferred(action, user):
    if action.description.find(user.get_full_name()) > 20:
        return mark_safe('<span style="color:#02700d"><i class="fas fa-arrow-down"></i></span> '+action.description.split('</b>')[0][20:])
    return mark_safe('<span style="color:#0000ff"><i class="fas fa-arrow-up"></i></span> '+action.description.split('</b>')[1][7:])

@register.simple_tag
def matter_format_status(matter):
    if matter.status == 'Active':
        return mark_safe("<span class='btn btn-xs' style='background-color:green;color:#FFF;'>Active</span>")
    elif matter.status == 'Dormant':
        return mark_safe("<span class='btn btn-xs' style='background-color:#888888'>Dormant</span>")
    elif matter.status == 'Not active':
        return mark_safe("<span class='btn btn-xs' style='background-color:#f39c12'>Not active</span>")
    elif matter.status == 'Closed':
        return mark_safe("<span class='btn btn-xs' style='background-color:red;color:white'>Closed</span>")
    elif matter.status == 'Request to close':
        return mark_safe("<span class='btn btn-xs' style='background-color:grey;color:white'>Request to close</span>")
    elif matter.status == 'Transferred to client':
        return mark_safe("<span class='btn btn-xs' style='background-color:blue;color:white'>Transferred to client</span>")
    elif matter.status == 'Request to transfer':
        return mark_safe("<span class='btn btn-xs' style='background-color:#02075D;color:white'>Request to transfer</span>")
    else:
        return mark_safe("<span sclass='btn btn-xs'>??</span>")

@register.simple_tag
def format_transfer_action(obj,max_len, **kwargs):
        return mark_safe(
            '<span style="color:#02075D"><i class="fas fa-exchange-alt"></i></span> %(verb)s' % {
                'verb': obj.description
            }
        )
@register.simple_tag
def format_description(obj, **kwargs):
    if obj:
        description = obj.split('|')
        if len(description) > 1:
            return mark_safe(description[0]+ ' <span style="color:#02075D" class="glyphicon glyphicon-chevron-right"></span> '+description[1])
        else:
            return mark_safe(description[0])
    else:
        return ''

@register.simple_tag
def format_action(obj,max_len, **kwargs):
    verb = obj.verb
    if not obj.description:
        return ''
    if verb == 'register.file_no_document_added':
        link = ""
        if obj.target:
            truncator = Truncator(obj.target.label)
            link = '<a href="'+obj.target.get_absolute_url()+'"><i class="far fa-file-alt"></i><span style="padding-left:10px">'+truncator.chars(max_len)+'</span></a>'

        return mark_safe(
            '<td><span style="color:#970000"><i class="far fa-plus-square"></i></span> %(verb)s' % {
                'verb': obj.description + "</td><td>" + link +"</td>"
            }
        )
    if verb == 'register.file_no_create':
        return mark_safe(
            '<td colspan=2 ><span style="color:green"><i class="fas fa-star"></i></span> %(verb)s' % {
                'verb': obj.description+"</td>"
            }
        )

    if verb == 'register.file_no_activate':
        return mark_safe(
            '<td colspan=2 ><span style="color:green"><i class="fas fa-edit"></i></span> %(verb)s' % {
                'verb': obj.description+"</td>"
            }
        )
    if verb == 'register.file_no_not_active':
        return mark_safe(
            '<td colspan=2 ><span style="color:#f39c12"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': obj.description+"</td>"
            }
        )
    if verb == 'register.file_no_dormant':
        return mark_safe(
            '<td colspan=2 ><span style="color:#888888"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': obj.description+"</td>"
            }
        )
    # ~ if verb == 'register.file_no_request':
        # ~ return mark_safe(
            # ~ '<td colspan=2 ><span style="color:grey"><i class="far fa-edit"></i></span> %(verb)s' % {
                # ~ 'verb': 'Status Changed: Requested'
            # ~ }
        # ~ )
    if verb == 'register.file_no_transferred':
        return mark_safe(
            '<td colspan=2 ><span style="color:#02075D"><i class="fas fa-exchange-alt"></i></span> %(verb)s' % {
                'verb': obj.description+"</td>"
            }
        )
    if verb == 'register.file_no_closed':
        return mark_safe(
            '<td colspan=2 ><span style="color:red"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': obj.description+"</td>"
            }
        )
    if verb == 'register.file_transferred_to_client':
        return mark_safe(
            '<td colspan=2 ><span style="color:blue"><i class="far fa-edit"></i></span> %(verb)s' % {
                'verb': 'Status Changed: Transferred to client </td>'
            }
        )
