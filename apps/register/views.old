from __future__ import absolute_import, unicode_literals

import logging
import time
import datetime
import operator
import uuid

from django.db.models import Q
from dynamic_search.icons import icon_search_submit
from dynamic_search.settings import setting_limit
import shlex

from django.http import Http404
from django.views.generic import (
    DetailView,
)
from django.db.models import Count
from django.core.cache import cache
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _, ungettext
from django.views.generic.edit import CreateView
from django.views.generic import TemplateView
from django.template import RequestContext
from acls.models import AccessControlList
from common.forms import ChoiceForm
from common.icons import icon_assign_remove_add, icon_assign_remove_remove
from common.generics import ConfirmView, SimpleView
from common.views import (
    SingleObjectCreateView, SingleObjectListView, SingleObjectEditView,
    SingleObjectDeleteView
)


from dynamic_search.mixins import SearchModelMixin
from .settings import ( register_status_choices, access_choices )

from django.http import QueryDict
from urlparse import urlparse, urlunparse
from dateutil.parser import parse

from common.utils import get_aware_str_from_unaware
from user_management.views import GroupMembersView
from common.mixins import ( ObjectNameMixin,ViewPermissionCheckMixin,ExtraContextMixin,RedirectionMixin,FormExtraKwargsMixin,
    ObjectPermissionCheckMixin )
from permissions.models import Permission, StoredPermission, Role
from documents.models import Document
from documents.permissions import permission_document_view
from .models import Register, Quotation, Client, Department, Contact
from register.permissions import (
    permission_register_view, permission_register_edit, permission_register_create,
    permission_client_create, permission_client_view
)
from .forms import ( RegisterEntryCreateForm, RegisterSearchForm,
    QuotationEntryCreateForm, QuotationEntryEditForm, QuotationSearchForm, FilterForm,
    RegisterRequestTransferForm, RegisterStatisticForm, RegisterEditGroupForm,
    ClientFilterForm, ContactCreateForm)
from .tasks import ( send_register_request_mail,send_register_request_confirmation_mail,
    send_quotation_request_mail,send_quotation_request_confirmation_mail,
    send_register_request_transfer_mail, send_register_request_close_mail )
from .links import link_register_create, link_register_quotation_create
from .icons import icon_document_list, icon_register
from .events import ( event_file_no_created,event_file_no_requested,event_file_no_activated,
    event_file_no_transferred, event_file_no_closed, event_file_no_not_active,
    event_file_no_transferred_to_client, event_file_no_dormant )

from sapitwa.tasks import add_entry_to_option_list, remove_entry_from_option_list
from sapitwa.utils import get_now
from django.urls import reverse
import dateutil.parser
import json
from .tasks import create_report, create_statistic_report, create_client_report
from .views import RegisterListView

from django.http import FileResponse

logger = logging.getLogger(__name__)
from register.settings import abbr
from sapitwa.tasks import task_add_rw_permissions





# Client



















