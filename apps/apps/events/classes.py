from __future__ import unicode_literals

import logging

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from actstream import action

from .permissions import permission_events_view
from mailer.tasks import task_send
from mailer.permissions import permission_user_mailer_use
from common.settings import setting_project_url


logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class EventTypeNamespace(object):
    _registry = {}

    @classmethod
    def all(cls):
        return sorted(cls._registry.values())

    @classmethod
    def get(cls, name):
        return cls._registry[name]

    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.event_types = []
        self.__class__._registry[name] = self

    def __lt__(self, other):
        return self.label < other.label

    def __str__(self):
        return force_text(self.label)

    def add_event_type(self, name, label):
        event_type = EventType(namespace=self, name=name, label=label)
        self.event_types.append(event_type)
        return event_type

    def get_event_types(self):
        return EventType.sort(event_type_list=self.event_types)


@python_2_unicode_compatible
class EventType(object):
    _registry = {}

    @staticmethod
    def sort(event_type_list):
        return sorted(
            event_type_list, key=lambda x: (x.namespace.label, x.label)
        )

    @classmethod
    def all(cls):
        # Return sorted permisions by namespace.name
        return EventType.sort(event_type_list=cls._registry.values())

    @classmethod
    def get(cls, name):
        try:
            return cls._registry[name]
        except KeyError:
            return _('Unknown or obsolete event type: %s') % name

    @classmethod
    def refresh(cls):
        for event_type in cls.all():
            event_type.get_stored_event_type()

    def __init__(self, namespace, name, label):
        self.namespace = namespace
        self.name = name
        self.label = label
        self.stored_event_type = None
        self.__class__._registry[self.id] = self

    def __str__(self):
        return force_text('{}: {}'.format(self.namespace.label, self.label))

    def commit(self, actor=None, action_object=None, target=None, description=None):
        AccessControlList = apps.get_model(
            app_label='acls', model_name='AccessControlList'
        )
        Action = apps.get_model(
            app_label='actstream', model_name='Action'
        )
        ContentType = apps.get_model(
            app_label='contenttypes', model_name='ContentType'
        )
        Notification = apps.get_model(
            app_label='events', model_name='Notification'
        )

        results = action.send(
            actor or target, actor=actor, verb=self.id,
            action_object=action_object, target=target,description=description
        )
        user_emails = {}
        for handler, result in results:
            if isinstance(result, Action):
                for user in get_user_model().objects.all():
                    is_actor = False
                    if user.username == str(actor):
                        is_actor = True
                    notification = None
                    if user.event_subscriptions.filter(stored_event_type__name=result.verb).exists():
                        if result.target:
                            try:
                                AccessControlList.objects.check_access(
                                    permissions=permission_events_view,
                                    user=user, obj=result.target
                                )
                            except PermissionDenied:
                                pass
                            else:
                                notification, created = Notification.objects.get_or_create(
                                    action=result, user=user
                                )
                                if user.email:
                                    if not user.email in user_emails:
                                        self.send_mail(actor=actor,email=user.email,result=result, is_actor=is_actor)
                                        user_emails[user.email] = True
                        else:
                            notification, created = Notification.objects.get_or_create(
                                action=result, user=user
                            )

                    if result.target:
                        content_type = ContentType.objects.get_for_model(model=result.target)

                        relationship = user.object_subscriptions.filter(
                            content_type=content_type,
                            object_id=result.target.pk,
                            stored_event_type__name=result.verb
                        )

                        if relationship.exists():
                            try:
                                AccessControlList.objects.check_access(
                                    permissions=permission_events_view,
                                    user=user, obj=result.target
                                )
                            except PermissionDenied:
                                pass
                            else:
                                notification, created = Notification.objects.get_or_create(
                                    action=result, user=user
                                )

                    if not notification and result.action_object:
                        content_type = ContentType.objects.get_for_model(model=result.action_object)

                        relationship = user.object_subscriptions.filter(
                            content_type=content_type,
                            object_id=result.action_object.pk,
                            stored_event_type__name=result.verb
                        )

                        if relationship.exists():
                            try:
                                AccessControlList.objects.check_access(
                                    permissions=permission_events_view,
                                    user=user, obj=result.action_object
                                )
                            except PermissionDenied:
                                pass
                            else:
                                notification, created = Notification.objects.get_or_create(
                                    action=result, user=user
                                )

    def get_stored_event_type(self):
        if not self.stored_event_type:
            StoredEventType = apps.get_model('events', 'StoredEventType')

            self.stored_event_type, created = StoredEventType.objects.get_or_create(
                name=self.id
            )

        return self.stored_event_type

    @property
    def id(self):
        return '%s.%s' % (self.namespace.name, self.name)

    def send_mail(self,actor,email,result,is_actor = False):
        logger.error('actor: %s, email: %s', actor,email)

        UserMailer = apps.get_model(
            app_label='mailer', model_name='UserMailer'
        )

        User = apps.get_model(settings.AUTH_USER_MODEL)
        if is_actor:
            username = "You"
            reply_to = None
            body_text = " have initiated the following event:"
        else:
            body_text = " wants to notify you about the following event:"
            try:
                user = User.objects.get(username = actor)
                if not user.is_superuser:
                    username = user.first_name+" "+user.last_name
                else:
                    username = "The system administrator"
                reply_to = user.email
            except:
                username = "The system administrator"
                reply_to = None

        user_mailer = UserMailer.objects.get(default=True)
        #Get a not to technical event name
        return # Here because we do not send mails
        event = str(EventType.get(result.verb))
        try:
            event = event.split(':')[1]
        except:
            pass


        subject = "EDMSDocs: "+str(event)+" "+str(result.target)
        body ="""
        <body lang="en-US" link="#AE132D" vlink="#AE132D" dir="ltr">
        <div style="padding:10px;">
        <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
        <font color="#000000"><font face="Calibri">"""
        body += str(username)
        body += body_text
        body += """</font></font></font></p>
        <p style="font-variant: normal; letter-spacing: normal; font-style: normal; font-weight: normal">
        <font color="#000000"><font face="Calibri"><b>"""
        body += str(event)
        body += """ </b><p><a href=" """

        body+= str(setting_project_url.value)+str(result.target.get_absolute_url())
        body += """ " style="color:#AE132D;">"""
        body += str(result.target)
        body += """
        </a></p></font></font></font></p><hr/>

        <p><span style="font-variant: normal"><font color="#000000"><font face="Calibri"><span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">*
        Please do not reply to this email. Your response will not be
        received.<br/>
        </span></span></span></font></font></font></span>"""
        if reply_to:
            body +="""
            <span style="font-variant: normal">
            <font color="#000000"><font face="Calibri">
            <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">
            </span></span></span></font></font></font></span><span style="font-variant: normal">
            <font color="#000000"><font face="Calibri">
            <span style="letter-spacing: normal"><span style="font-style: normal"><span style="font-weight: normal">Contact:
            <a href="mailto:"""
            body += reply_to
            body += """ " style="color:#AE132D;">"""
            body += reply_to
            body += """</a></span></span></span></font></font></font></span></p>"""
        body +="""</div>
        <p><img src="https://www.useit-mw.com/docs96x96.png" name="docs" width=60 height=60 align="middle" border="0"/>

        <font face="Calibri"><b>EDMSDocs</b></font></p></body>
        """
        logger.error('----------> Send mail to: %s', email)
        return #do not send mail notification of events at the moment
        task_send.apply_async(
            kwargs={
                'as_attachment': False,
                'body': body,
                'document_id': None,
                'recipient': email, #'mail@useit-mw.com', # email,
                'sender': "",
                'subject': subject,
                'user_mailer_id': user_mailer.id,
                'signature' : False
            }
        )


class ModelEventType(object):
    """
    Class to allow matching a model to a specific set of events.
    """
    _inheritances = {}
    _proxies = {}
    _registry = {}

    @classmethod
    def get_for_class(cls, klass):
        return cls._registry.get(klass, ())

    @classmethod
    def get_for_instance(cls, instance):
        StoredEventType = apps.get_model(
            app_label='events', model_name='StoredEventType'
        )

        events = []

        class_events = cls._registry.get(type(instance))

        if class_events:
            events.extend(class_events)

        proxy = cls._proxies.get(type(instance))

        if proxy:
            events.extend(cls._registry.get(proxy))

        pks = [
            event.id for event in set(events)
        ]

        return EventType.sort(
            event_type_list=StoredEventType.objects.filter(name__in=pks)
        )

    @classmethod
    def get_inheritance(cls, model):
        return cls._inheritances[model]

    @classmethod
    def register(cls, model, event_types):
        cls._registry.setdefault(model, [])
        for event_type in event_types:
            cls._registry[model].append(event_type)

    @classmethod
    def register_inheritance(cls, model, related):
        cls._inheritances[model] = related

    @classmethod
    def register_proxy(cls, source, model):
        cls._proxies[model] = source
