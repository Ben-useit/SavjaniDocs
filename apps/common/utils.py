from __future__ import unicode_literals

import logging
import os
import shutil
import tempfile
import types

import datetime
import pytz
#from tzlocal import get_localzone 
from dateutil.parser import parse  
from django.utils import timezone 
from django.utils.dateformat import DateFormat 

from django.conf import settings
from django.urls import resolve as django_resolve
from django.urls.base import get_script_prefix
from django.utils.datastructures import MultiValueDict
from django.utils.http import (
    urlencode as django_urlencode, urlquote as django_urlquote
)
from django.utils.six.moves import reduce as reduce_function, xmlrpc_client
from django.utils.translation import ugettext_lazy as _

from common.compat import dict_type, dictionary_type
import mayan

from .exceptions import NotLatestVersion, UnknownLatestVersion
from .literals import DJANGO_SQLITE_BACKEND, MAYAN_PYPI_NAME, PYPI_URL
from .settings import setting_temporary_directory

logger = logging.getLogger(__name__)


def check_for_sqlite():
    return settings.DATABASES['default']['ENGINE'] == DJANGO_SQLITE_BACKEND and settings.DEBUG is False


def check_version():
    pypi = xmlrpc_client.ServerProxy(PYPI_URL)
    versions = pypi.package_releases(MAYAN_PYPI_NAME)
    if not versions:
        raise UnknownLatestVersion
    else:
        if versions[0] != mayan.__version__:
            raise NotLatestVersion(upstream_version=versions[0])


# http://stackoverflow.com/questions/123198/how-do-i-copy-a-file-in-python
def copyfile(source, destination, buffer_size=1024 * 1024):
    """
    Copy a file from source to dest. source and dest
    can either be strings or any object with a read or
    write method, like StringIO for example.
    """
    source_descriptor = get_descriptor(source)
    destination_descriptor = get_descriptor(destination, read=False)

    while True:
        copy_buffer = source_descriptor.read(buffer_size)
        if copy_buffer:
            destination_descriptor.write(copy_buffer)
        else:
            break

    source_descriptor.close()
    destination_descriptor.close()


def encapsulate(function):
    # Workaround Django ticket 15791
    # Changeset 16045
    # http://stackoverflow.com/questions/6861601/
    # cannot-resolve-callable-context-variable/6955045#6955045
    return lambda: function


def get_user_label_text(context):
    if not context['request'].user.is_authenticated:
        return _('Anonymous')
    else:
        return context['request'].user.get_full_name() or context['request'].user


def fs_cleanup(filename, file_descriptor=None, suppress_exceptions=True):
    """
    Tries to remove the given filename. Ignores non-existent files
    """
    if file_descriptor:
        os.close(file_descriptor)

    try:
        os.remove(filename)
    except OSError:
        try:
            shutil.rmtree(filename)
        except OSError:
            if suppress_exceptions:
                pass
            else:
                raise


def get_descriptor(file_input, read=True):
    try:
        # Is it a file like object?
        file_input.seek(0)
    except AttributeError:
        # If not, try open it.
        if read:
            return open(file_input, mode='rb')
        else:
            return open(file_input, mode='wb')
    else:
        return file_input


def TemporaryFile(*args, **kwargs):
    kwargs.update({'dir': setting_temporary_directory.value})
    return tempfile.TemporaryFile(*args, **kwargs)


def mkdtemp(*args, **kwargs):
    kwargs.update({'dir': setting_temporary_directory.value})
    return tempfile.mkdtemp(*args, **kwargs)


def mkstemp(*args, **kwargs):
    kwargs.update({'dir': setting_temporary_directory.value})
    return tempfile.mkstemp(*args, **kwargs)


def resolve(path, urlconf=None):
    path = '/{}'.format(path.replace(get_script_prefix(), '', 1))
    return django_resolve(path=path, urlconf=urlconf)


def return_attrib(obj, attrib, arguments=None):
    if isinstance(attrib, types.FunctionType):
        return attrib(obj)
    elif isinstance(
        obj, dict_type
    ) or isinstance(obj, dictionary_type):
        return obj[attrib]
    else:
        result = reduce_function(getattr, attrib.split('.'), obj)
        if isinstance(result, types.MethodType):
            if arguments:
                return result(**arguments)
            else:
                return result()
        else:
            return result


def return_related(instance, related_field):
    """
    This functions works in a similar method to return_attrib but is
    meant for related models. Support multiple levels of relationship
    using double underscore.
    """
    return reduce_function(getattr, related_field.split('__'), instance)


def urlquote(link=None, get=None):
    """
    This method does both: urlquote() and urlencode()

    urlqoute(): Quote special characters in 'link'

    urlencode(): Map dictionary to query string key=value&...

    HTML escaping is not done.

    Example:

    urlquote('/wiki/Python_(programming_language)')
        --> '/wiki/Python_%28programming_language%29'
    urlquote('/mypath/', {'key': 'value'})
        --> '/mypath/?key=value'
    urlquote('/mypath/', {'key': ['value1', 'value2']})
        --> '/mypath/?key=value1&key=value2'
    urlquote({'key': ['value1', 'value2']})
        --> 'key=value1&key=value2'
    """
    if get is None:
        get = []

    assert link or get
    if isinstance(link, dict):
        # urlqoute({'key': 'value', 'key2': 'value2'}) -->
        # key=value&key2=value2
        assert not get, get
        get = link
        link = ''
    assert isinstance(get, dict), 'wrong type "%s", dict required' % type(get)
    # assert not (link.startswith('http://') or link.startswith('https://')),
    #    'This method should only quote the url path.
    #    It should not start with http(s)://  (%s)' % (
    #    link)
    if get:
        # http://code.djangoproject.com/ticket/9089
        if isinstance(get, MultiValueDict):
            get = get.lists()
        if link:
            link = '%s?' % django_urlquote(link)
        return '%s%s' % (link, django_urlencode(get, doseq=True))
    else:
        return django_urlquote(link)


def validate_path(path):
    if not os.path.exists(path):
        # If doesn't exist try to create it
        try:
            os.mkdir(path)
        except Exception as exception:
            logger.debug('unhandled exception: %s', exception)
            return False

    # Check if it is writable
    try:
        fd, test_filepath = tempfile.mkstemp(dir=path)
        os.close(fd)
        os.unlink(test_filepath)
    except Exception as exception:
        logger.debug('unhandled exception: %s', exception)
        return False

    return True

    

def get_now_as_str():
    return timezone.now().__str__()

def get_date_str(dt):
    try:
        d = parse(dt)
    except:
        d = datetime.datetime.now()
    return d.__str__()

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


# Expect a datetime string like
# 2019-09-01 18:29:00 -1000 or
# Returns: 1. Sept 2019 18:29 or 1. Sept 2019
def get_str_from_aware(datetime_str, date_only=False):   
    try:
        df = DateFormat(timezone.localtime(parse(datetime_str)))
    except:
        return "NIL"
    if date_only:
        return str(df.format('j. N Y'))
    else:
        return str(df.format('j. N Y, H:i'))

# Expect a string like
# 'Sep 1,2019,6:29 am'
# Returns: 2019-09-01 06:29:00 -1000  
def get_aware_str_from_unaware(value):
    try:
        value = value.replace(',',' ')
        parsed = parse(value)
        value = timezone.make_aware(parsed)
    except:
        return timezone.now().strftime("%Y-%m-%d %H:%M:%S %z")
    return str(value.strftime("%Y-%m-%d %H:%M:%S%z"))



        
# def convert_into_datetime(dt_str,user):
    # user_tz = user.locale_profile.timezone
    # if user_tz == '':
        # user_tz = pytz.timezone("UTC")
    # else:
        # user_tz = pytz.timezone(user.locale_profile.timezone)
    # d = parse(dt_str)
    # return d.astimezone(user_tz)

#used by zip upload
def get_timzone_date_str_from_tuple(tup,user):
    return get_timezone_date_str(datetime.datetime(*tup[:6]).__str__(),user)
