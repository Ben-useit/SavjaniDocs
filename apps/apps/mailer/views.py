from __future__ import absolute_import, unicode_literals

from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.urls import reverse, reverse_lazy
from django.utils.translation import ungettext, ugettext_lazy as _

from acls.models import AccessControlList
from common.generics import (
    FormView, MultipleObjectFormActionView, SingleObjectDeleteView,
    SingleObjectDynamicFormCreateView, SingleObjectDynamicFormEditView,
    SingleObjectListView
)
from documents.models import Document

from .classes import MailerBackend
from .forms import (
    DocumentMailForm, UserMailerBackendSelectionForm, UserMailerDynamicForm,
    UserMailerTestForm
)
from .icons import icon_mail_document_submit, icon_user_mailer_setup
from .links import link_user_mailer_create
from .models import LogEntry, UserMailer
from .permissions import (
    permission_mailing_link, permission_mailing_send_document,
    permission_user_mailer_create, permission_user_mailer_delete,
    permission_user_mailer_edit, permission_user_mailer_use,
    permission_user_mailer_view, permission_view_error_log
)
from .tasks import task_send_document


class SystemMailerLogEntryListView(SingleObjectListView):
    extra_context = {
        'hide_object': True,
        'title': _('Document mailing error log'),
    }
    model = LogEntry
    view_permission = permission_view_error_log


class MailDocumentView(MultipleObjectFormActionView):
    as_attachment = True
    form_class = DocumentMailForm
    model = Document
    object_permission = permission_mailing_send_document

    success_message = _('%(count)d document queued for email delivery')
    success_message_plural = _(
        '%(count)d documents queued for email delivery'
    )
    title = 'Email document'
    title_plural = 'Email documents'
    title_document = 'Email document: %s'

    def get_extra_context(self):
        queryset = self.get_queryset()

        result = {
            'submit_icon_class': icon_mail_document_submit,
            'submit_label': _('Send'),
            'title': ungettext(
                self.title,
                self.title_plural,
                queryset.count()
            )
        }

        if queryset.count() == 1:
            result.update(
                {
                    'object': queryset.first(),
                    'title': _(self.title_document) % queryset.first()
                }
            )

        return result

    def get_form_extra_kwargs(self):
        return {
            'as_attachment': self.as_attachment,
            'user': self.request.user
        }

    def object_action(self, form, instance):
        AccessControlList.objects.check_access(
            permissions=permission_user_mailer_use, user=self.request.user,
            obj=form.cleaned_data['user_mailer']
        )

        task_send_document.apply_async(
            kwargs={
                'as_attachment': self.as_attachment,
                'body': form.cleaned_data['body'],
                'document_id': instance.pk,
                'recipient': form.cleaned_data['email'],
                'sender': self.request.user.email,
                'subject': form.cleaned_data['subject'],
                'user_mailer_id': form.cleaned_data['user_mailer'].pk,
            }
        )


class MailDocumentLinkView(MailDocumentView):
    as_attachment = False
    object_permission = permission_mailing_link
    success_message = _('Link to document sent.')
    success_message_plural = _(
        'Links to documents sent.'
    )
    title = 'Email document link'
    title_plural = 'Email document links'
    title_document = 'Email link for document: %s'


class UserMailerBackendSelectionView(FormView):
    extra_context = {
        'title': _('New mailing profile backend selection'),
    }
    form_class = UserMailerBackendSelectionForm
    view_permission = permission_user_mailer_create

    def form_valid(self, form):
        backend = form.cleaned_data['backend']
        return HttpResponseRedirect(
            reverse('mailer:user_mailer_create', args=(backend,),)
        )


class UserMailingCreateView(SingleObjectDynamicFormCreateView):
    form_class = UserMailerDynamicForm
    post_action_redirect = reverse_lazy('mailer:user_mailer_list')
    view_permission = permission_user_mailer_create

    def get_backend(self):
        try:
            return MailerBackend.get(name=self.kwargs['class_path'])
        except KeyError:
            raise Http404(
                '{} class not found'.format(self.kwargs['class_path'])
            )

    def get_extra_context(self):
        return {
            'title': _(
                'Create a "%s" mailing profile'
            ) % self.get_backend().label,
        }

    def get_form_schema(self):
        backend = self.get_backend()
        result = {
            'fields': backend.fields,
            'widgets': getattr(backend, 'widgets', {})
        }
        if hasattr(backend, 'field_order'):
            result['field_order'] = backend.field_order

        return result

    def get_instance_extra_data(self):
        return {'backend_path': self.kwargs['class_path']}


class UserMailingDeleteView(SingleObjectDeleteView):
    model = UserMailer
    object_permission = permission_user_mailer_delete
    post_action_redirect = reverse_lazy('mailer:user_mailer_list')

    def get_extra_context(self):
        return {
            'title': _('Delete mailing profile: %s') % self.get_object(),
        }


class UserMailingEditView(SingleObjectDynamicFormEditView):
    form_class = UserMailerDynamicForm
    model = UserMailer
    object_permission = permission_user_mailer_edit

    def get_extra_context(self):
        return {
            'title': _('Edit mailing profile: %s') % self.get_object(),
        }

    def get_form_schema(self):
        backend = self.get_object().get_backend()
        result = {
            'fields': backend.fields,
            'widgets': getattr(backend, 'widgets', {})
        }
        if hasattr(backend, 'field_order'):
            result['field_order'] = backend.field_order

        return result


class UserMailerLogEntryListView(SingleObjectListView):
    model = LogEntry
    view_permission = permission_user_mailer_view

    def get_extra_context(self):
        return {
            'hide_object': True,
            'object': self.get_user_mailer(),
            'title': _('%s error log') % self.get_user_mailer(),
        }

    def get_object_list(self):
        return self.get_user_mailer().error_log.all()

    def get_user_mailer(self):
        return get_object_or_404(UserMailer, pk=self.kwargs['pk'])


class UserMailerListView(SingleObjectListView):
    model = UserMailer
    object_permission = permission_user_mailer_view

    def get_extra_context(self):
        return {
            'hide_object': True,
            'no_results_icon': icon_user_mailer_setup,
            'no_results_main_link': link_user_mailer_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Mailing profiles are email configurations. '
                'Mailing profiles are used to send documents '
                'via email.'
            ),
            'no_results_title': _('No mailing profiles available'),
            'title': _('Mailing profile'),
        }

    def get_form_schema(self):
        return {'fields': self.get_backend().fields}


class UserMailerTestView(FormView):
    form_class = UserMailerTestForm
    object_permission = permission_user_mailer_edit

    def form_valid(self, form):
        self.get_object().test(to=form.cleaned_data['email'])
        return super(UserMailerTestView, self).form_valid(form=form)

    def get_extra_context(self):
        return {
            'hide_object': True,
            'object': self.get_object(),
            'submit_label': _('Test'),
            'title': _('Test mailing profile: %s') % self.get_object(),
        }

    def get_object(self):
        user_mailer = get_object_or_404(UserMailer, pk=self.kwargs['pk'])
        AccessControlList.objects.check_access(
            permissions=permission_user_mailer_use, user=self.request.user,
            obj=user_mailer
        )

        return user_mailer
