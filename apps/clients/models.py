from __future__ import absolute_import, unicode_literals
from django.db import models
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _

#from register.models import Register
from .events import event_client_created, event_client_edited


class Client(models.Model):
    """
    This model represents a client.
    """
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
    is_ex_lawyer = models.BooleanField(verbose_name=_('Is an external lawyer'), default=False)

    class Meta:
        ordering = ('name',)
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')

    def __str__(self):
        return self.name

    def get_no_matters(self, status = None, lawyers = None):
        if not status:
            if lawyers:
                return self.register_set.filter(lawyers__pk__in=lawyers).count()
            else:
                return self.register_set.all().count()
            #return Client.objects.exclude(contact__register__status__startswith="Request" ).exclude(contact__register__status="Transferred to client" ).annotate(number_of_matters=Count('contact__register')).get(pk=self.pk).number_of_matters
        elif status == "Misc":
            status = ['Active','Not active','Dormant','Closed']
            if lawyers:
                return self.register_set.filter(lawyers__pk__in=lawyers).exclude(status__name__in=status).count()
            else:
                return self.register_set.exclude(status__name__in=status).count()
        else:
            if lawyers:
                return self.register_set.filter(status__name=status).filter(lawyers__pk__in=lawyers).count()
            else:
                return self.register_set.filter(status__name=status).count()

class Contact(models.Model):
    name = models.CharField(
        db_index=True, max_length=256, verbose_name=_('Name')
    )
    position = models.CharField(
        help_text=_(
            'Posittion of contact person of client'
        ), max_length=256, verbose_name=_('Position'),blank=True
    )
    address = models.CharField(
        max_length=256, verbose_name=_('Address'),blank = True
    )
    city = models.CharField(
        max_length=256, verbose_name=_('City'), blank = True
    )
    country = models.CharField(
        help_text=_(
            'Address'
        ), max_length=256, verbose_name=_('Country'),blank=True
    )
    phone = models.CharField(
        max_length=256, verbose_name=_('Phone'), blank = True
    )
    email = models.CharField(
        max_length=256, verbose_name=_('Email'), blank = True
    )
    client = models.ForeignKey(
        to=Client, verbose_name=_('Client'), blank=True, default=None, null=True
    )
    clients = models.ManyToManyField(related_name='clients', to=Client, blank=True)

    def __str__(self):
        return self.get_client_names() + ' - ' +self.name

    def get_client_names(self):
        return ';'.join(self.clients.all().values_list('name',flat=True).distinct())



