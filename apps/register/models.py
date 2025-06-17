from __future__ import absolute_import, unicode_literals
from colorful.fields import RGBColorField

from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from acls.models import AccessControlList

from documents.permissions import permission_document_view
from documents.models import Document

from register.permissions import (
    permission_register_view, permission_register_edit, permission_register_create,
)

from .settings import register_status_choices, quotation_status_choices, register_group_choices
import datetime




@python_2_unicode_compatible
class Department(models.Model):
    name = models.CharField(
        db_index=True, help_text=_(
            'Department'
        ), max_length=256, unique=True, verbose_name=_('Department')
    )

    def __str__(self):
        return self.name


    def get_no_matters(self, user = None, status = None):
        if status == 'AnAD':
            status_qs = Status.objects.filter(name='Active') | Status.objects.filter(name='Dormant') | Status.objects.filter(name='Not active')
        elif status:
            status_qs = Status.objects.filter(name=status)

        if user:
            if not status:
                qs = self.register_set.all()
            else:
                qs = self.register_set.filter(status__in=status_qs)
            qs = AccessControlList.objects.filter_by_access(permission=permission_register_view, user=user,
            queryset=qs)
            return qs.count()
        else:
            return 0

@python_2_unicode_compatible
class Group(models.Model):
    name = models.CharField(
        max_length=48,
        help_text=_(
            'Name used by other apps to reference this group. '
            'Do not use python reserved words, or spaces.'
        ),
        unique=True, verbose_name=_('Name')
    )

    def __str__(self):
        return str(self.name)

@python_2_unicode_compatible
class Status(models.Model):
    name = models.CharField(
        db_index=True, help_text=_(
            'Status of a matter'
        ), max_length=256, verbose_name=_('Name')
    )
    color = RGBColorField(
        help_text=_('The RGB font color value for the status.'),
        verbose_name=_('Color'), default=u'#000000'
    )
    background_color = RGBColorField(
        help_text=_('The RGB background color value tor the status.'),
        verbose_name=_('Background Color'), default=u'#FFFFFF'
    )
    def __str__(self):
        return self.name


from actstream.models import Action, any_stream
from django.utils.safestring import mark_safe
from clients.models import Contact, Client
@python_2_unicode_compatible
class Register(models.Model):
    STATUS_CHOICES = register_status_choices.value
    GROUP_CHOICES = register_group_choices.value
    opened = models.DateTimeField(verbose_name=_('Opened'), default=timezone.now, null=False)
    closed = models.DateTimeField(verbose_name=_('Closed'), blank=True, null=True)
    carton_no = models.CharField(
        help_text=_(
            'Carton number file placed in'
        ), max_length=512, verbose_name=_('Carton Number'), default="",
    )
    room = models.CharField(
        help_text=_(
            'Room archive'
        ), max_length=512, verbose_name=_('Room'), default="",
    )
    retention_period = models.CharField(
        help_text=_(
            'Retention Period'
        ), max_length=512, verbose_name=_('Retention Period'), default="",
    )
    last_activity = models.DateTimeField(verbose_name=_('Last Activity'), blank=True, null=True)
    year_of_destruction = models.DateTimeField(verbose_name=_('Year of Destruction'), blank=True, null=True)


    file_no = models.CharField(
        db_index=True, help_text=_(
            'The file number'
        ), max_length=128, unique=True, verbose_name=_('File Number')
    )
    _file_no_bak = models.CharField(
        help_text=_(
            'The file number'
        ), max_length=128, verbose_name=_('File Number'), default = ''
    )
    parties = models.CharField(
        db_index=True, help_text=_(
            'Involved parties.'
        ), max_length=512, verbose_name=_('Parties'), default=""
    )
    group = models.ForeignKey(
        to=Group,verbose_name=_('Group'), blank=True, default=None, null=True
    )
    lawyers = models.ManyToManyField(User)
    last_lawyers = models.ManyToManyField(User, related_name='last_lawyers')
    documents = models.ManyToManyField(related_name='register', to=Document)
    status = models.ForeignKey(
        to=Status,verbose_name=_('StatusF'), blank=True, default=None, null=True
    )
    transfer_to = models.CharField(
        help_text=_(
            'Request to transfer to'
        ), max_length=512, verbose_name=_('Transfer to'), default="",
    )
    last_status = models.CharField(
        db_index=True, choices=STATUS_CHOICES, help_text=_(
            'The last status of the file no.'
        ), max_length=48, verbose_name=_('Last Status'), default = 'Not active'
    )
    contacts = models.ManyToManyField(to=Contact, blank=True)
    clients= models.ManyToManyField(to=Client, blank=True)
    department = models.ForeignKey(
        on_delete=models.CASCADE, to=Department,
        verbose_name=_('Department'), blank=True, default=None, null=True
    )
    opposing_parties = models.TextField(
        verbose_name=_('Opposing Parties'), default = '', blank=True
    )
    other_parties = models.TextField(
        verbose_name=_('Other Parties'), default = '', blank=True
    )
    cause_no = models.TextField(
        db_index=True, verbose_name=_('Cause Number'), default = '', blank=True
    )
    court = models.TextField(
        db_index=True, verbose_name=_('Court'), default = '', blank=True
    )
    physical_file_available = models.BooleanField(
        default=True,
    )
    class Meta:
        ordering = ('-opened','-pk')
        verbose_name = _('Register')
        verbose_name_plural = _('Register')

    def __str__(self):
        return self.file_no+' - '+self.parties

    def get_absolute_url(self):
        return reverse('register:register_detail', args=(str(self.pk),))

    def has_checklist(self):
        if self.registerchecklist_set.all():
            return True
        else:
            return False
    def has_status_report(self):
        if self.registerchecklist_set.all().first():
            return self.registerchecklist_set.all().first().checklist.name == 'Checklist on Commercial Department Files'
        else:
            return False
    def is_tracked(self):
        return self.trackedfile_set.all().count() > 0

    def is_transferred(self):
        actions = any_stream(self)
        for a in actions:
            if a.verb == "register.file_no_transferred":
                return "Yes"
        return "No"

    def get_last_lawyer(self):
        return self.last_lawyers.first()

    def is_active(self):
        return self.status == 'Active'
    def get_open(self):
        td = datetime.timedelta(hours = 2)
        return self.opened + td

    def get_lawyer_full_name(self):
        try:
            return self.lawyers.first().get_full_name()
        except:
            return ''


    def get_client_name(self):
        return ';'.join(self.clients.all().values_list('name',flat=True).distinct())

    def get_document_count(self, user):
        """
        Return the numeric count of documents that belong to this file number.
        It is filtered by access.
        """
        queryset = AccessControlList.objects.filter_by_access(permission=permission_document_view, user=user,
            queryset=self.documents.all())
        return queryset.count()

    def get_transferred_from(self, user):
        #actions = any_stream(self).filter(verb="register.file_no_transferred").order_by('timestamp')
        if self.last_lawyers.first() != user:
            return "Transferred from "+self.last_lawyers.first().get_full_name()
        else:
            return ''
    def has_clients(self):
        return self.clients.all()

    def has_group(self):
        return self.group.name != '---'

@python_2_unicode_compatible
class ActiveFileTrackingChart(models.Model):
    #date_closure = models.DateField(verbose_name=_('Date of closure'), default=timezone.now, null=False)
    files = models.ManyToManyField(to=Register)
    retain_or_transfer = models.CharField(verbose_name='Retain file or transfer required', max_length=256,default='')
    date_closure_letter = models.DateField(verbose_name=_('Date of closure letter to client'), blank = True, null=True)
    instructions = models.DateField(verbose_name= 'Instructions received regarding file transfer', blank = True, null=True)
    file_to = models.ForeignKey(to=Client,verbose_name=_('File to new lawyer or client'), blank=True, default=None, null=True)
    date_completion = models.DateField(verbose_name= 'Date of completion of transfer process', blank = True, null=True)
    notice = models.DateField(verbose_name='Notice of change of legal practitioners', blank = True, null=True)
    receipt = models.DateField(verbose_name='Receipt of file acknowledgement', blank=True,null=True)
    def __str__(self):
        return "Files transferred to: "

    class Meta:
        ordering = ('-date_closure_letter',)
        verbose_name = _('Transferred Register File')
        verbose_name_plural = _('Transferred Register Files')

    def get_date(self, attrib, no=True):
        if attrib:
            return attrib.strftime('%d.%m.%Y') #strftime('%e. %B %Y')
        else:
            if no:
                return 'No'
            else:
                return ''

    def get_client_file_transferrred_to(self, name = False ):
        if self.file_to:
            if name:
                return self.file_no.name
            else:
                return self.file_to
        else:
            return ''

    def get_number_of_files(self):
        return self.files.all().count()

@python_2_unicode_compatible
class Quotation(models.Model):
    STATUS_CHOICES = quotation_status_choices.value
    opened = models.DateTimeField(verbose_name=_('Opened'), default=timezone.now, null=False)
    file_no = models.CharField(
        db_index=True, help_text=_(
            'The file no.'
        ), max_length=128, unique=True, verbose_name=_('Label')
    )
    parties = models.CharField(
        db_index=True, help_text=_(
            'Involved parties.'
        ), max_length=512, verbose_name=_('Parties'), default=""
    )
    documents = models.ManyToManyField(Document)
    status_old = models.CharField(
        db_index=True, choices=STATUS_CHOICES, help_text=_(
            'The status of the file no.'
        ), max_length=48, verbose_name=_('Status'), default = 'not active'
    )
    status = models.ForeignKey(
        to=Status,verbose_name=_('StatusF'), blank=True, default=None, null=True
    )

    class Meta:
        ordering = ('-opened','-pk')
        verbose_name = _('Quotation')
        verbose_name_plural = _('Quotations')

    def __str__(self):
        return self.file_no+' - '+self.parties

    def get_absolute_url(self):
        return reverse('register:register_detail', args=(str(self.pk),))

    def is_active(self):
        return self.status == 'Active'

    def get_open(self):
        td = datetime.timedelta(hours = 2)
        return self.opened + td

    def get_document_count(self, user):
        """
        Return the numeric count of documents that belong to this file number.
        It is filtered by access.
        """
        queryset = AccessControlList.objects.filter_by_access(permission=permission_document_view, user=user,
            queryset=self.documents.all())
        return queryset.count()


