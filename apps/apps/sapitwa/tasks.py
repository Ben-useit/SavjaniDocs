import json
import logging
from os.path import splitext

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from mayan.celery import app

from acls.models import AccessControlList
from common.models import SharedUploadedFile
from documents.models import Document, DocumentType
from document_indexing.models import Index
from metadata.models import MetadataType, DocumentMetadata
from tags.models import Tag
from permissions.models import Role, StoredPermission

from .utils import get_timezone_date_str, extract, create_document, get_users_of_role
from .models import TempDocument, ListOptions, UserStats

logger = logging.getLogger(__name__)

@app.task(bind=True, default_retry_delay=10, ignore_result=True)
def task_post_web_upload_process(self,uploaded_file_pk,temp_document_pk):
    temp_document = TempDocument.objects.get(pk = temp_document_pk)
    user = temp_document.user
    user_role = temp_document.role
    uploaded_file = SharedUploadedFile.objects.get(pk = uploaded_file_pk)
    document_type = temp_document.document_type
    document = create_document(uploaded_file,document_type,user)
    if document:
        process_wizard_data(document = document, temp_document= temp_document, user_role= user_role, user=user)

@app.task(bind=True, default_retry_delay=10, ignore_result=True)
def task_post_upload_process(self,document_pk,email,file_timestamps,temp_document_pk):
    document = Document.objects.raw("Select * from documents_document where id={0}".format(document_pk))[0]
    temp_document = TempDocument.objects.get(pk = temp_document_pk)
    user_role = temp_document.role
    user = temp_document.user
    if document and not file_timestamps:
        if temp_document.document_type:
            document.document_type = temp_document.document_type
            document.save(_user=user)
            with temp_document.uploaded_file.open() as file_object:
                document.new_version(file_object=file_object,_user = user)
            process_wizard_data(document, temp_document= temp_document,user_role=user_role, user=user)
            temp_document.uploaded_file.delete()
    elif document and file_timestamps:
        if email:
            document_type = DocumentType.objects.get(label = 'Email')
        else:
            document_type = temp_document.document_type
        documents = extract(temp_document.uploaded_file,document_type,user,email)
        for doc in documents:
            process_wizard_data(doc,temp_document,user_role,user,file_timestamps)
        temp_document.uploaded_file.delete()
        document.delete(to_trash=False)

import datetime
from register.models import Register, Quotation
from register.events import event_file_no_document_added
def process_wizard_data(document, temp_document, user_role,user, file_timestamps = None):

    query_dict = json.loads(temp_document.metadata)
    if temp_document.last_modified != '':
        lv = document.latest_version
        lv.timestamp = temp_document.last_modified
        lv.save()
    if temp_document.register_no != '':
        try:
            r = Register.objects.get(file_no=temp_document.register_no)
            r.documents.add(document)
            r.save()
            event_file_no_document_added.commit(
                actor=user, target=document, action_object=r
            )
        except Register.DoesNotExist:
            pass
    if temp_document.quotation_no != '':
        try:
            r = Quotation.objects.get(file_no=temp_document.quotation_no)
            r.documents.add(document)
            r.save()
            event_file_no_document_added.commit(
                actor=user, target=document, action_object=r
            )
        except Quotation.DoesNotExist:
            pass
    if temp_document.register_file:
        temp_document.register_file.documents.add(document)
        temp_document.register_file.save()
        event_file_no_document_added.commit(
            actor=user, target=document, action_object=temp_document.register_file
        )
    if temp_document.quotation_file:
        temp_document.quotation_file.documents.add(document)
        temp_document.quotation_file.save()
        event_file_no_document_added.commit(
            actor=user, target=document, action_object=temp_document.quotation_file
        )
    if temp_document.label != '':
        document.label =  temp_document.label
        document.save()

    query_dict = json.loads(temp_document.metadata)
    if 'metadata' in query_dict:
        for m in query_dict['metadata']:
            #if m.get('update'):
            if m.get('value') != '':
                #m.get('id')
                mt = MetadataType.objects.get(pk=m.get('id'))
                value = m.get('value')
                if mt.name == 'document_name':
                    file_name,extension = splitext(document.label)
                    document.label = value + extension
                    document.save(_user=user)
                    continue
                if 'DateAndTimeValidator' in mt.validation:
                    pass
                    #value = get_timezone_date_str(value,user)
                dm = DocumentMetadata(document=document, metadata_type=mt,value=value)
                dm.save()

    #Add timestamp information if document has metadata timestamp
    if file_timestamps:
        #mt = MetadataType.objects.get(name='document_timestamp')
        if file_timestamps.get(document.label):
            lv = document.latest_version
            lv.timestamp = file_timestamps.get(document.label)
            lv.save()
    query_dict = json.loads(temp_document.permissions)
    if 'role_rw' in query_dict:
        if query_dict.get('role_rw'):
            for role_pk in query_dict.get('role_rw'):
                role = Role.objects.get(pk= role_pk)
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=document.pk,content_type=ContentType.objects.get_for_model(document), role=role
                )
                task_add_rw_permissions(acl)
    #give user role full access
    if user_role:
        acl, created = AccessControlList.objects.get_or_create(
           object_id=document.pk,content_type=ContentType.objects.get_for_model(document), role=user_role
        )
        task_add_rw_permissions(acl)

    if 'role_ro' in query_dict:
        if query_dict.get('role_ro'):
            for role_pk in query_dict.get('role_ro'):
                role = Role.objects.get(pk= role_pk)
                acl, created = AccessControlList.objects.get_or_create(
                   object_id=document.pk,content_type=ContentType.objects.get_for_model(document), role=role
                )
                if not created:
                    acl.permissions.clear()
                task_add_ro_permissions(acl)
    query_dict = json.loads(temp_document.tags)
    if 'tags' in query_dict:
        for tag_pk in query_dict['tags']:
            tag = Tag.objects.get(pk=tag_pk)
            tag.documents.add(document)
    updateStats(user=user)

    #index = Index.objects.get(label='File Number')
    #index.index_document(document)

def updateStats(user):
    now = timezone.now().date()
    stat, created = UserStats.objects.get_or_create(user=user,date=now)
    stat.number = stat.number + 1
    stat.save()

def task_add_rw_permissions(access_list):
    ro_permissions ='comment_view'
    ro_permissions +=',transformation_view,content_view'
    ro_permissions +=',document_view,document_version_view'
    ro_permissions +=',document_print,document_download,ocr_document'
    ro_permissions +=',events_view,mail_document,metadata_document_view'
    ro_permissions +=',ocr_content_view,tag_view,tag_attach'

    rw_permissions = ro_permissions +''
    rw_permissions +=',comment_create,transformation_delete,document_delete,document_trash'
    rw_permissions +=',document_restore,metadata_document_remove,acl_edit,acl_view'
    rw_permissions +=',comment_delete,transformation_edit,transformation_create,tag_remove'
    rw_permissions +=',document_properties_edit,document_edit,document_version_revert'
    rw_permissions +=',metadata_document_edit,metadata_document_add,tag_remove,document_new_version'
    for p in rw_permissions.split(','):
        access_list.permissions.add(StoredPermission.objects.get(name=p))

def task_add_ro_permissions(access_list):
    access_list.permissions.clear()
    ro_permissions ='comment_view'
    ro_permissions +=',transformation_view,content_view'
    ro_permissions +=',document_view,document_version_view'
    ro_permissions +=',document_print,document_download,ocr_document'
    ro_permissions +=',events_view,mail_document,metadata_document_view'
    ro_permissions +=',ocr_content_view,tag_view,tag_attach,acl_view'

    rw_permissions = ro_permissions +''
    rw_permissions +=',comment_create'
    rw_permissions +=',comment_delete,transformation_edit,transformation_create'
    rw_permissions +=',document_properties_edit,document_edit'
    rw_permissions +=',metadata_document_edit,metadata_document_add,document_new_version'
    for p in rw_permissions.split(','):
        access_list.permissions.add(StoredPermission.objects.get(name=p))

def remove_entry_from_option_list(name,role,entry):
    op = '<option value="'+str(entry)+'">'
    reg_option = op.decode('utf-8')
    users = get_users_of_role(role)
    for user in users:
        try:
            obj = ListOptions.objects.get(name=name,user=user)
            obj.option_list = obj.option_list.replace(reg_option,'')
            obj.save()
        except ListOptions.DoesNotExist:
            pass

def add_entry_to_option_list(name,role,entry):
    op = '<option value="'+str(entry)+'">'
    option = op.decode('utf-8')
    users = get_users_of_role(role)
    for user in users:
        obj,created = ListOptions.objects.get_or_create(name=name,user=user)
        if option not in obj.option_list:
            obj.option_list = option + obj.option_list
            obj.save()

