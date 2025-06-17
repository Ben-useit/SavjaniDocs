from __future__ import absolute_import, unicode_literals

from django import forms
from django.apps import apps
from django.template.loader import render_to_string
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.forms.widgets import NumberInput

class AttribWidget(object):
    def __init__(self, attrib, center=False, icon_ok=None, icon_fail=None):
        self.attrib = attrib

    def render(self):
        if self.attrib:
            return mark_safe("<span class='btn btn-xs' style='background-color:Lightgreen; color:Black;'>"+self.attrib+"</span>")
        else:
             return mark_safe("<span class='btn btn-xs' style='background-color:Red; color:Red;'>02.10.2022</span>")


