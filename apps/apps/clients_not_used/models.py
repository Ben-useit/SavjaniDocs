from django.db import models
from django.utils.translation import ugettext_lazy as _

#from .events import event_client_created, event_client_edited

class ClientA(models.Model):
    """
    This model represents a client.
    """
    name = models.CharField(
        db_index=True, max_length=256, verbose_name=_('Name')
    )

    class Meta:
        ordering = ('name',)
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')

    def __str__(self):
        return self.name

class Contact(models.Model):
    name = models.CharField(
        db_index=True, max_length=256, verbose_name=_('Name')
    )
    address = models.CharField(
        max_length=256, verbose_name=_('Address'),blank = True
    )
    city = models.CharField(
        max_length=256, verbose_name=_('City'), blank = True
    )
    phone = models.CharField(
        max_length=256, verbose_name=_('Phone'), blank = True
    )
    email = models.CharField(
        max_length=256, verbose_name=_('Email'), blank = True
    )
    client = models.ForeignKey(to=ClientA)

    def __str__(self):
        return self.name
