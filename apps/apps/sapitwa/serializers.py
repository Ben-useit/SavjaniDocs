import logging
import datetime
from rest_framework import serializers
from django.utils.encoding import force_text

from common.models import SharedUploadedFile
from documents.models import Document, DocumentType
from documents.settings import setting_language

from .models import TempDocument
logger = logging.getLogger(name=__name__)
class NewSapitwaDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    last_modified = serializers.CharField(max_length=205)
    document_type = serializers.CharField(max_length=205)

    def save(self, _user):
        dt = DocumentType.objects.get(label="Temp__Upload")
        document = Document(
            description=self.validated_data.get('description', ''),
            document_type=dt, 
            label=self.validated_data.get(
                'label', force_text(self.validated_data['file'])
            ),
            language=self.validated_data.get(
                'language', setting_language.value
            )
        )
        document.save(_user=_user)
        lm = self.validated_data['last_modified']
        try:
            lm = float(lm )
            lm = lm/1000.0    
            lm = datetime.datetime.fromtimestamp(lm).__str__()+'+00:00'
        except:
            pass
        shared_uploaded_file = SharedUploadedFile.objects.create(
            file=self.validated_data['file']
        )
        tmp_document = TempDocument(document = document, uploaded_file = shared_uploaded_file, user = _user, last_modified = lm)
        tmp_document.save()

        self.instance = document
        return document

    class Meta:
        fields = (
            'uuid','description', 'document_type', 'id', 'file', 'label', 'language', 'last_modified'
        )
        model = Document
