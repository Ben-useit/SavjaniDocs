from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .managers import UserOptionsManager


class UserOptions(models.Model):
    user = models.OneToOneField(
        on_delete=models.CASCADE, related_name='user_options',
        to=settings.AUTH_USER_MODEL, unique=True, verbose_name=_('User')
    )
    block_password_change = models.BooleanField(
        default=False,
        verbose_name=_('Forbid this user from changing their password.')
    )
    display_closed_register_files = models.BooleanField(
        default=False,
        verbose_name=_('Display closed register files.')
    )

    objects = UserOptionsManager()

    class Meta:
        verbose_name = _('User settings')
        verbose_name_plural = _('Users settings')

    def natural_key(self):
        return self.user.natural_key()
    natural_key.dependencies = [settings.AUTH_USER_MODEL]
