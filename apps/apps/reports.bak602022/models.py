from __future__ import absolute_import, unicode_literals

from django.db import models
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from colorful.fields import RGBColorField

from acls.models import AccessControlList
from documents.models import Document
from documents.permissions import permission_document_view



