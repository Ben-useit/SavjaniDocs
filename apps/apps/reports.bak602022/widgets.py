from __future__ import absolute_import, unicode_literals

from django import forms
from django.forms import DateTimeInput
from django.apps import apps
from django.template.loader import render_to_string
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

class DatePickerInput(DateTimeInput):
    template_name = 'reports/datepicker.html'
