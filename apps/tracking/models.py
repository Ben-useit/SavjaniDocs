from __future__ import absolute_import, unicode_literals
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from clients.models import Client
from register.models import Register

@python_2_unicode_compatible
class TrackedFile(models.Model):
    NONE = ''
    RETAIN = 'RT'
    TRANSFER = 'TR'
    ACTION_CHOICES = [
        ( NONE, ''),
        ( RETAIN, 'Retain'),
        ( TRANSFER, 'Transfer')
    ]
    file = models.ForeignKey(verbose_name='Tracked File', to=Register, on_delete=models.CASCADE, )
    retain_or_transfer = models.CharField(
        verbose_name='Retain file or transfer required', max_length=2,
        choices = ACTION_CHOICES, default=NONE, blank=True
    )
    closure_letter = models.DateField(verbose_name=_('Date of closure letter to client'), blank = True, null=True)
    instructions = models.DateField(verbose_name= 'Date instructions received regarding file transfer', blank = True, null=True)
    client = models.ForeignKey(to=Client,verbose_name=_('File to new lawyer or client'), blank=True, default=None, null=True)
    completion = models.DateField(verbose_name= 'Date of completion of transfer process', blank = True, null=True)
    notice = models.DateField(verbose_name='Date of notice of change of legal practitioners', blank = True, null=True)
    receipt = models.DateField(verbose_name='Date of receipt of file acknowledgement', blank=True,null=True)
    def __str__(self):
        return "Tracked file "+self.file.file_no

    class Meta:
        ordering = ('-file__opened',)
        verbose_name = _('Tracked Register File')
        verbose_name_plural = _('Tracked Register Files')

    def get_date(self, attrib, no=True):
        if attrib:
            return attrib.strftime('%d.%m.%Y')
        else:
            if no:
                return 'No'
            else:
                return ''

    def get_client(self, name = False ):
        if self.client:
            if name:
                return self.client.name
            else:
                return self.client
        else:
            return ''


