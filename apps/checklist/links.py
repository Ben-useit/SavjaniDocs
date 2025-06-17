from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from navigation import Link, get_cascade_condition

from .icons import icon_checklist, icon_status_report

def has_report(context):
    try:
        return context['object'].has_status_report()
    except KeyError:
        # Might not have permissions
        return False

link_status_report = Link(
    icon_class=icon_status_report,
    condition = has_report,
    args='object.id',
    html_extra_classes='None',
    text=_('Status Report'), view='checklist:status_pdf'
)

link_checklist = Link(
    icon_class=icon_checklist,
    description='aaa',
    args='object.id',
    html_extra_classes='None',
    text=_('Checklist'), view='checklist:checklist'
)
link_select = Link(
    #icon_class=icon_register_create,
    args='object.id',

    text=_('Select'), view='checklist:select'
)


