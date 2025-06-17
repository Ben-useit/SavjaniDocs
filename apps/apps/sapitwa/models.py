from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from common.models import SharedUploadedFile
from permissions.models import Role
from documents.models import Document, DocumentType

from register.models import Register, Quotation

class TempDocument(models.Model):

    document = models.ForeignKey(Document, blank=True, null=True, on_delete=models.CASCADE,)
    uploaded_file = models.ForeignKey(SharedUploadedFile, blank=True,null=True, on_delete=models.CASCADE,)
    user = models.ForeignKey(User, blank=False, default=None, on_delete=models.CASCADE,)
    document_type = models.ForeignKey(DocumentType,blank=False, default=None,null=True, on_delete=models.CASCADE,)

    metadata = models.TextField(
        blank=True, verbose_name=_('Metadata')
    )
    tags = models.TextField(
        blank=True, verbose_name=_('Tags')
    )
    permissions = models.TextField(
        blank=True, verbose_name=_('Permissions')
    )
    cabinets = models.TextField(
        blank=True, verbose_name=_('Cabinets')
    )
    last_modified = models.TextField(
        blank=True, verbose_name=_('Last Modified')
    )
    role = models.ForeignKey(Role, blank=False,null=True, default=None, on_delete=models.CASCADE,)
    label = models.TextField(
            blank=True, verbose_name=_('Label')
    )
    label = models.TextField(
            blank=True, verbose_name=_('Label')
    )
    register_no = models.TextField(
            blank=True, verbose_name=_('Register No')
    )
    quotation_no = models.TextField(
            blank=True, verbose_name=_('Quotation No')
    )
    register_file = models.ForeignKey(Register,blank=True,null=True, default=None, on_delete=models.CASCADE,
    )
    quotation_file = models.ForeignKey(Quotation,blank=True,null=True, default=None, on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _('TempDocument')
        verbose_name_plural = _('TempDocuments')

    def __str__(self):
        return self.document.label

class RegisterOptions(models.Model):
    role = models.ForeignKey(Role, blank=False, default=None, on_delete=models.CASCADE,)
    option_list = models.TextField(
            blank=True, verbose_name=_('OptionList')
    )
    class Meta:
        verbose_name = _('RegisterOptions')
        verbose_name_plural = _('RegisterOptions')

    def __str__(self):
        return self.option_list[:20]

class QuotationOptions(models.Model):
    role = models.ForeignKey(Role, blank=False, default=None, on_delete=models.CASCADE,)
    option_list = models.TextField(
            blank=True, verbose_name=_('OptionList')
    )
    class Meta:
        verbose_name = _('Quotation Options')
        verbose_name_plural = _('Quotation Options')

    def __str__(self):
        return self.option_list[:20]

class UserStats(models.Model):
    user = models.ForeignKey(User, blank=False, on_delete=models.CASCADE,)
    date = models.DateField(
        db_index=True, verbose_name=_('Date')
    )
    number = models.IntegerField(default=0)

    def __str__(self):
        return str(self.number)


class ListOptions(models.Model):
    name = models.CharField(max_length=128, verbose_name=_('Label'))
    user = models.ForeignKey(User, blank=False, default=None, on_delete=models.CASCADE,)
    option_list = models.TextField(
            blank=True, verbose_name=_('Option List')
    )
    class Meta:
        verbose_name = _('ListOptions')
        verbose_name_plural = _('ListOptions')

    def __str__(self):
        return self.option_list[:20]
