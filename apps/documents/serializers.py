from __future__ import unicode_literals

import logging
import datetime
from zipfile import ZipFile
import sys
import time
import os
from django.utils.encoding import force_text
from django.core.files import File
from rest_framework import serializers
from rest_framework.reverse import reverse

from common.models import SharedUploadedFile
from common.utils import get_timzone_date_str_from_tuple

from metadata.models import MetadataType, DocumentMetadata
from acls.tasks import task_add_full_permision

from .models import (
    Document, DocumentVersion, DocumentPage, DocumentType,
    DocumentTypeFilename, RecentDocument
)
from .settings import setting_language
from .tasks import task_upload_new_version
logger = logging.getLogger(__name__)

class DocumentPageSerializer(serializers.HyperlinkedModelSerializer):
    document_version_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        fields = ('document_version_url', 'image_url', 'page_number', 'url')
        model = DocumentPage

    def get_document_version_url(self, instance):
        return reverse(
            'rest_api:documentversion-detail', args=(
                instance.document.pk, instance.document_version.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_image_url(self, instance):
        return reverse(
            'rest_api:documentpage-image', args=(
                instance.document.pk, instance.document_version.pk,
                instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_url(self, instance):
        return reverse(
            'rest_api:documentpage-detail', args=(
                instance.document.pk, instance.document_version.pk,
                instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )


class DocumentTypeFilenameSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTypeFilename
        fields = ('filename',)


class DocumentTypeSerializer(serializers.HyperlinkedModelSerializer):
    documents_url = serializers.HyperlinkedIdentityField(
        view_name='rest_api:documenttype-document-list',
    )
    documents_count = serializers.SerializerMethodField()
    filenames = DocumentTypeFilenameSerializer(many=True, read_only=True)

    class Meta:
        extra_kwargs = {
            'url': {'view_name': 'rest_api:documenttype-detail'},
        }
        fields = (
            'delete_time_period', 'delete_time_unit', 'documents_url',
            'documents_count', 'id', 'label', 'filenames', 'trash_time_period',
            'trash_time_unit', 'url'
        )
        model = DocumentType

    def get_documents_count(self, obj):
        return obj.documents.count()


class WritableDocumentTypeSerializer(serializers.ModelSerializer):
    documents_url = serializers.HyperlinkedIdentityField(
        view_name='rest_api:documenttype-document-list',
    )
    documents_count = serializers.SerializerMethodField()

    class Meta:
        extra_kwargs = {
            'url': {'view_name': 'rest_api:documenttype-detail'},
        }
        fields = (
            'delete_time_period', 'delete_time_unit', 'documents_url',
            'documents_count', 'id', 'label', 'trash_time_period',
            'trash_time_unit', 'url'
        )
        model = DocumentType

    def get_documents_count(self, obj):
        return obj.documents.count()


class DocumentVersionSerializer(serializers.HyperlinkedModelSerializer):
    document_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    pages_url = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        extra_kwargs = {
            'document': {'view_name': 'rest_api:document-detail'},
            'file': {'use_url': False},
        }
        fields = (
            'checksum', 'comment', 'document_url', 'download_url', 'encoding',
            'file', 'mimetype', 'pages_url', 'size', 'timestamp', 'url'
        )
        model = DocumentVersion
        read_only_fields = ('document', 'file', 'size')

    def get_size(self, instance):
        return instance.size

    def get_document_url(self, instance):
        return reverse(
            'rest_api:document-detail', args=(
                instance.document.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_download_url(self, instance):
        return reverse(
            'rest_api:documentversion-download', args=(
                instance.document.pk, instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_pages_url(self, instance):
        return reverse(
            'rest_api:documentversion-page-list', args=(
                instance.document.pk, instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_url(self, instance):
        return reverse(
            'rest_api:documentversion-detail', args=(
                instance.document.pk, instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )


class WritableDocumentVersionSerializer(serializers.ModelSerializer):
    document_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    pages_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        extra_kwargs = {
            'file': {'use_url': False},
        }
        fields = (
            'checksum', 'comment', 'document_url', 'download_url', 'encoding',
            'file', 'mimetype', 'pages_url', 'timestamp', 'url'
        )
        model = DocumentVersion
        read_only_fields = ('document', 'file')

    def get_document_url(self, instance):
        return reverse(
            'rest_api:document-detail', args=(
                instance.document.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_download_url(self, instance):
        return reverse(
            'rest_api:documentversion-download', args=(
                instance.document.pk, instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_pages_url(self, instance):
        return reverse(
            'rest_api:documentversion-page-list', args=(
                instance.document.pk, instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )

    def get_url(self, instance):
        return reverse(
            'rest_api:documentversion-detail', args=(
                instance.document.pk, instance.pk,
            ), request=self.context['request'], format=self.context['format']
        )



class NewDocumentVersionSerializer(serializers.Serializer):
    comment = serializers.CharField(allow_blank=True)
    file = serializers.FileField(use_url=False)
    last_modified = serializers.CharField(max_length=205)

    def save(self, document, _user):
        shared_uploaded_file = SharedUploadedFile.objects.create(
            file=self.validated_data['file']
        )
        #convert last_modified
        last_modified = float(self.validated_data.get('last_modified'))
        last_modified = last_modified/1000.0    
        last_modified = datetime.datetime.fromtimestamp(last_modified)

        document = task_upload_new_version.delay(
            comment=self.validated_data.get('comment', ''),
            document_id=document.pk,
            shared_uploaded_file_id=shared_uploaded_file.pk, user_id=_user.pk,
            last_modified = str(last_modified)
        )
        return document
    class Meta:
        fields = (
            'file', 'comment','last_modified' 
        )


class DeletedDocumentSerializer(serializers.HyperlinkedModelSerializer):
    document_type_label = serializers.SerializerMethodField()
    restore = serializers.HyperlinkedIdentityField(
        view_name='rest_api:trasheddocument-restore'
    )

    class Meta:
        extra_kwargs = {
            'document_type': {'view_name': 'rest_api:documenttype-detail'},
            'url': {'view_name': 'rest_api:trasheddocument-detail'}
        }
        fields = (
            'date_added', 'deleted_date_time', 'description', 'document_type',
            'document_type_label', 'id', 'label', 'language', 'restore',
            'url', 'uuid',
        )
        model = Document
        read_only_fields = (
            'deleted_date_time', 'description', 'document_type', 'label',
            'language'
        )

    def get_document_type_label(self, instance):
        return instance.document_type.label


class DocumentSerializer(serializers.HyperlinkedModelSerializer):
    document_type = DocumentTypeSerializer()
    latest_version = DocumentVersionSerializer(many=False, read_only=True)
    versions_url = serializers.HyperlinkedIdentityField(
        view_name='rest_api:document-version-list',
    )

    class Meta:
        extra_kwargs = {
            'document_type': {'view_name': 'rest_api:documenttype-detail'},
            'url': {'view_name': 'rest_api:document-detail'}
        }
        fields = (
            'date_added', 'description', 'document_type', 'id', 'label',
            'language', 'latest_version', 'url', 'uuid', 'versions_url',
        )
        model = Document
        read_only_fields = ('document_type',)


class WritableDocumentSerializer(serializers.ModelSerializer):
    document_type = DocumentTypeSerializer(read_only=True)
    latest_version = DocumentVersionSerializer(many=False, read_only=True)
    versions = serializers.HyperlinkedIdentityField(
        view_name='rest_api:document-version-list',
    )
    url = serializers.HyperlinkedIdentityField(
        view_name='rest_api:document-detail',
    )

    class Meta:
        fields = (
            'date_added', 'description', 'document_type', 'id', 'label',
            'language', 'latest_version', 'url', 'uuid', 'versions',
        )
        model = Document
        read_only_fields = ('document_type',)

import sys
import io
class NewDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    last_modified = serializers.CharField(max_length=205)
    document_type = serializers.CharField(max_length=205)
    
    def save(self, _user):
        label = force_text(self.validated_data['file'])
        dt = DocumentType.objects.get(label="Temp__Upload")
        shared_uploaded_file = SharedUploadedFile.objects.create(
            file=self.validated_data['file']
        )
        
        if label.endswith('.zip'):
            directory = '/tmp/'+ str(time.time())
            date_times = {}
            email = None
            with ZipFile(shared_uploaded_file.open(), 'r') as zipObj:
                for f in zipObj.infolist():
                    #file_name = f.filename.decode('Cp437')
                    file_name = ''
                    for x in f.filename:
                        try:
                            file_name += x.decode('Cp437')
                        except:
                            pass
                    if file_name.endswith('.email'):
                        email = file_name
                    date_time = f.date_time
                    date_times[file_name] = str(get_timzone_date_str_from_tuple(date_time,_user))
            os.mkdir(directory)
            unzip(shared_uploaded_file.open(),directory)
            if email:
                #f = open(directory+'/'+email)
                email_path = directory+'/'+email
                with io.open(email_path, encoding="utf8", errors='ignore') as f:
                    metas = []
                    for x in f:
                        m = x.split(':',1)
                        metas.append((m[0],m[1]))     
                                      
            doc_ids = ''
            uuid = ''
            for filename in os.listdir(directory):  
                if filename.endswith('.email'):
                    continue 
                if filename.endswith('.png'):
                    continue 
                if filename.endswith('.gif'):
                    continue 
                if filename.endswith('.xml'):
                    continue 
                if filename.endswith('.jpg'):
                    if os.path.getsize(directory+'/'+filename) < 50000:
                        continue 
                                             
                if doc_ids != '':
                    doc_ids += ','
                f = open(directory+'/'+filename)
                shared_uploaded_file = SharedUploadedFile.objects.create(
                    file=File(f)
                )              
                document = Document.objects.create(
                    description='',
                    document_type=dt,
                    label=filename,
                    language="eng",
                ) 
                document.save(_user=_user) 
                task_add_full_permision(document,_user) 
                last_modified = None
                if email:
                    dt = DocumentType.objects.get(label='Email')
                    document.document_type = dt
                    document.save()
                    for m in metas:
                        if m[0] == 'from':
                            metadata_type = MetadataType.objects.get(name='email_from')
                            mo = DocumentMetadata.objects.create(document=document,metadata_type=metadata_type,value=m[1])
                            mo.save()
                        elif m[0] == 'to':
                            metadata_type = MetadataType.objects.get(name='email_to')
                            mo = DocumentMetadata.objects.create(document=document,metadata_type=metadata_type,value=m[1])
                            mo.save()
                        elif m[0] == 'subject':
                            metadata_type = MetadataType.objects.get(name='email_subject')
                            mo = DocumentMetadata.objects.create(document=document,metadata_type=metadata_type,value=m[1])
                            mo.save()
                        elif m[0] == 'sent':
                            last_modified = m[1].rstrip()
                            metadata_type = MetadataType.objects.get(name='email_date')
                            mo = DocumentMetadata.objects.create(document=document,metadata_type=metadata_type,value=m[1])
                            mo.save()
                if not last_modified:
                    last_modified = date_times[filename]  
                task_upload_new_version.delay(
                    document_id=document.pk,
                    shared_uploaded_file_id=shared_uploaded_file.pk, user_id=_user.pk,
                    last_modified = last_modified,is_stub = False
                ) 
                document.is_stub = False
                document.save()
                doc_ids += str(document.pk)
            document.description = doc_ids
            if email:
                document.description = 'email/' + doc_ids
            self.instance = document
            return document
            
        # no zip            
        last_modified = float(self.validated_data.get('last_modified'))
        last_modified = last_modified/1000.0    
        last_modified = datetime.datetime.fromtimestamp(last_modified).__str__()+'+00:00'
        
        #dt = DocumentType.objects.get(label="Temp__Upload")
        document = Document.objects.create(
            description=self.validated_data.get('description', ''),
            document_type=dt, #self.validated_data['document_type'],
            label=self.validated_data.get(
                'label', force_text(self.validated_data['file'])
            ),
            language=self.validated_data.get(
                'language', setting_language.value
            ),
        )
        document.save(_user=_user)
        task_add_full_permision(document,_user) 
        task_upload_new_version.delay(
            document_id=document.pk,
            shared_uploaded_file_id=shared_uploaded_file.pk, user_id=_user.pk,
            last_modified = str(last_modified),is_stub = False
        )
        document.is_stub = False
        document.save()
        self.instance = document
        return document

    class Meta:
        fields = (
            'uuid','description', 'document_type', 'id', 'file', 'label', 'language','last_modified'
        )
        model = Document


class RecentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('document', 'datetime_accessed')
        model = RecentDocument


def unzip(zip_file, target):
    zf = ZipFile(zip_file, 'r')
    for m in zf.infolist():
        data = zf.read(m) # extract zipped data into memory
        # convert unicode file path to utf8
        #disk_file_name = m.filename.decode('Cp437')
        file_name = ''
        for x in m.filename:
            try:
                file_name += x.decode('Cp437')
            except:
                pass        
        with open(target+'/'+file_name, 'wb') as fd:
            fd.write(data)
    zf.close()
