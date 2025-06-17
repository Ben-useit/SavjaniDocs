from __future__ import absolute_import, unicode_literals

from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from acls.models import AccessControlList
from documents.permissions import permission_document_view
from register.models import Register


class Checklist(models.Model):

    name = models.CharField(max_length=256)
    template = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class TemplateEntry(models.Model):
    LABEL= 'LB'
    TEXT = 'TX'
    DATE = 'DO'
    DATETIME = 'DT'
    CHECKBOX = 'CB'
    YESNO = 'YN'
    TEXTAREA='TA'
    ACTIVEDORMANT = 'AD'

    TYPE_CHOICES = [
        (LABEL, 'Label'),
        (TEXT, 'Text'),
        (DATE, 'Date'),
        (DATETIME, 'Datetime'),
        (CHECKBOX, 'Checkbox'),
        (YESNO,'Yes No'),
        (TEXTAREA,'Textarea'),
        (ACTIVEDORMANT,'ActiveDormant')
    ]
    checklist = models.ForeignKey(Checklist,on_delete=models.CASCADE, blank=True, default=None)
    number = models.FloatField(verbose_name=_('Number'), default=0.0)
    symbol = models.CharField(max_length=32, verbose_name=_('Symbol'),default='')
    label = models.CharField(max_length=512, verbose_name=_('Label'))
    entry_type = models.CharField(choices=TYPE_CHOICES, max_length=2,default=TEXT)
    indent = models.PositiveIntegerField(default=0)
    help_text =models.CharField(max_length=512, verbose_name=_('Help Text'), default='', blank=True)
    def __str__(self):
        return self.label

class ChecklistTemplateEntry(models.Model):
    checklist = models.ForeignKey(
        on_delete=models.CASCADE, related_name='checklist', to=Checklist,
        verbose_name=_('Checklist')
    )
    template_entry = models.ForeignKey(
        on_delete=models.CASCADE, to=TemplateEntry,
        verbose_name=_('Template Entry')
    )


class RegisterTemplateEntry(models.Model):
    """
    Link a register file to a specific instance of a template type with it's
    current value
    """
    register = models.ForeignKey(
        on_delete=models.CASCADE, related_name='matter', to=Register,
        verbose_name=_('Register')
    )
    template_entry = models.ForeignKey(
        on_delete=models.CASCADE, to=TemplateEntry, verbose_name=_('Template Entry')
    )
    value = models.TextField(
        blank=True, db_index=True, help_text=_(
            'The actual value stored in the template entry field for '
            'the matter.'
        ), null=True, verbose_name=_('Value')
    )

class RegisterChecklist(models.Model):
    register = models.ForeignKey(Register,on_delete=models.CASCADE)
    checklist = models.ForeignKey(Checklist,on_delete=models.CASCADE)
    #empty = models.BooleanField(default=True)

    def __str__(self):
        return "Checklist for"+ self.register.file_no
