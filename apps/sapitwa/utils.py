import logging
import pytz
import datetime
from dateutil.parser import parse

from django.core.files import File
from django.db import models, transaction
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.utils.encoding import force_text

from common.compressed_files import Archive
from common.exceptions import NoMIMETypeMatch
from common.models import SharedUploadedFile
from permissions.models import Role
from documents.models import Document
from django.core.files.uploadedfile import SimpleUploadedFile

logger = logging.getLogger(__name__)

def get_user_role(user):
    role = None
    if not user.is_superuser:
        try:
            role = Role.objects.get(label=user.first_name+" "+user.last_name)
        except Role.DoesNotExist:
            pass
    return role

# Expect a string like
# 'Sep 1,2019,6:29 am'
# Returns: 2019-09-01 06:29:00 -1000
def get_aware_str_from_unaware(value, datetime = False):
    try:
        value = value.replace(',',' ')
        parsed = parse(value)
        value = timezone.make_aware(parsed)
        if datetime:
            return value
    except:
        if datetime:
            return timezone.now()
        return timezone.now().strftime("%Y-%m-%d %H:%M:%S %z")
    return str(value.strftime("%Y-%m-%d %H:%M:%S%z"))

def get_zip_info(user, shared_uploaded_file):
    file_date_time = {}
    email = {}
    subject = ''
    try:
        compressed_file = Archive.open(file_object=shared_uploaded_file.file)
    except NoMIMETypeMatch:
        return({},{},{})
    for f in compressed_file._archive.infolist():

        if f.filename.endswith('.email'):
            data = compressed_file._archive.read(f)
            data_list = data.decode('Cp437').split('\n')
            for x in data_list:
                kv = x.split(':', 1)
                if len(kv) == 2:
                    email[kv[0]] = kv[1]
            subject = email['subject']
        else:
            file_date_time[f.filename] = str(get_timzone_date_str_from_tuple(f.date_time,user))
    return(file_date_time,email,subject)

# Expect a datetime string like
# 2019-09-01 18:29:00 -1000
# Returns: 1. Sept 2019 18:29 or 1. Sept 2019
def get_str_from_aware(datetime_str, date_only=False, if_error_now = False):
    try:
        df = DateFormat(timezone.localtime(parse(datetime_str)))
    except:
        if if_error_now:
            return get_now()
        return ""
    if date_only:
        return str(df.format('j N Y'))
    else:
        return str(df.format('j N Y, H:i'))

def get_now( date_only=False, long_date = False):
    try:
        df = DateFormat(timezone.localtime(parse(timezone.now().__str__())))
    except:
        return "NIL"
    if date_only:
        if long_date:
            return str(df.format('jS F Y'))
        else:
            return str(df.format('j N Y'))
    else:
        if long_date:
            return str(df.format('j F Y, H:i'))
        else:
            return str(df.format('j N Y, H:i'))

#used by zip upload
def get_timzone_date_str_from_tuple(tup,user):
    return get_timezone_date_str(datetime.datetime(*tup[:6]).__str__(),user)

def get_timezone_date_str(dt,user):
    if user:
        user_tz = user.locale_profile.timezone
        if user_tz == '':
            user_tz = pytz.timezone("UTC")
        else:
            user_tz = pytz.timezone(user.locale_profile.timezone)
        parsed = parse(dt)
        parsed_tz = user_tz.localize(parsed)
        utc_tz = pytz.timezone("UTC")
        return parsed_tz.astimezone(utc_tz)
    else:
        return timezone.now().__str__()

def create_document(uploaded_file,document_type,user):
    document = None
    try:
        with transaction.atomic():
            document = Document(document_type=document_type,label=force_text(uploaded_file))
            document.save(_user=user)
            with uploaded_file.open() as file_object:
                document.new_version(file_object=file_object, _user=user)
    except Exception as exception:
        logger.error('Could not create Document or Document Version object: %s', exception)

    return document


def extract(uploaded_file,document_type,user,email):

    documents = []
    with uploaded_file.open() as file_object:
        compressed_file = Archive.open(file_object=file_object)
        members =  [ filename for filename in compressed_file._archive.namelist() if not filename.endswith('/')]
        simple_uploaded_files = (SimpleUploadedFile(name=filename.replace('\xb3','|'), content=compressed_file.member_contents(filename)) for filename in members)
        for compressed_file_child in simple_uploaded_files:
            if email:
                label = force_text(compressed_file_child)
                if label.startswith('image0') and label[-4:].lower().endswith('.jpg') or label[-4:].lower().endswith('.png') or label[-4:].lower().endswith('.gif') or label[-5:].lower().endswith('.jpeg'):
                    if compressed_file_child.size < 40000:
                        continue
            if force_text(compressed_file_child) == 'info.email':
                continue
            try:
                child_shared_uploaded_file = SharedUploadedFile.objects.create(file=File(compressed_file_child))
                with transaction.atomic():
                    document = Document(document_type=document_type,label=force_text(compressed_file_child))
                    document.save(_user=user)
                    documents.append(document)
                    with child_shared_uploaded_file.open() as file_object:
                        document.new_version(file_object=file_object, _user=user)
                child_shared_uploaded_file.delete()
            except Exception as exception:
                logger.error('Could not create Document or Document Version object: %s', exception)

    return documents


def get_users_of_role(role):
    users = {}
    for g in role.groups.all():
        for user in g.user_set.all():
            users[user.pk] = user
    return users.values()
