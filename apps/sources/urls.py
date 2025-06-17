from __future__ import unicode_literals

from django.conf.urls import url

from sapitwa.wizards import DocumentWizard, DocumentWebCreateWizard
from sapitwa.views import UploadWebInteractiveView

from .api_views import (
    APIStagingSourceFileView, APIStagingSourceFileImageView,
    APIStagingSourceListView, APIStagingSourceView
)
from .views import (
    SetupSourceCheckView, SetupSourceCreateView, SetupSourceDeleteView,
    SetupSourceEditView, SetupSourceListView, SourceLogListView,
    StagingFileDeleteView, UploadInteractiveVersionView, 
    UploadInteractiveView, document_upload
)
from .wizards import ( DocumentCreateWizard, DocumentFinalizeWizard,
    DocumentsFinalizeWizard, EmailFinalizeWizard
)

urlpatterns = [
    url(
        r'^staging_file/(?P<pk>\d+)/(?P<encoded_filename>.+)/delete/$',
        StagingFileDeleteView.as_view(), name='staging_file_delete'
    ),

    url(
        r'^upload/document/new/interactive/(?P<source_id>\d+)/$',
        UploadWebInteractiveView.as_view(), name='document_upload_interactive'
    ),
    url(
        r'^upload/document/new/interactive/$',
        UploadWebInteractiveView.as_view(), name='document_upload_interactive'
    ),
    url(
        r'^upload/document/new/interactive/$', DocumentWebCreateWizard.as_view(),
        name='document_create_multiple'
    ),
    # ~ url(
        # ~ r'^upload/document/new/$', UploadWebInteractiveView.as_view(),
        # ~ name='document_upload'
    # ~ ),

    url(
        r'^upload/document/(?P<document_pk>\d+)/version/interactive/(?P<source_id>\d+)/$',
        UploadInteractiveVersionView.as_view(), name='upload_version'
    ),
    url(
        r'^upload/document/(?P<document_pk>\d+)/version/interactive/$',
        UploadInteractiveVersionView.as_view(), name='upload_version'
    ),

    # Setup views

    url(
        r'^setup/list/$', SetupSourceListView.as_view(),
        name='setup_source_list'
    ),
    url(
        r'^setup/(?P<pk>\d+)/edit/$', SetupSourceEditView.as_view(),
        name='setup_source_edit'
    ),
    url(
        r'^setup/(?P<pk>\d+)/logs/$', SourceLogListView.as_view(),
        name='setup_source_logs'
    ),
    url(
        r'^setup/(?P<pk>\d+)/delete/$', SetupSourceDeleteView.as_view(),
        name='setup_source_delete'
    ),
    url(
        r'^setup/(?P<source_type>\w+)/create/$',
        SetupSourceCreateView.as_view(), name='setup_source_create'
    ),
    url(
        r'^setup/(?P<pk>\d+)/check/$', SetupSourceCheckView.as_view(),
        name='setup_source_check'
    ),

    # Document create views

    url(
        r'^create/from/local/multiple/$', DocumentWebCreateWizard.as_view(), # DocumentCreateWizard.as_view(),
        name='document_create_multiple'
    ),
    # ~ url(
        # ~ r'^add/(?P<doc_id>[\w\-]+)/(?P<uuid>[\w\-]+)/$', DocumentFinalizeWizard.as_view(),
        # ~ name='document_finalize'
    # ~ ),
    # ~ url(
        # ~ r'^add/(?P<doc_id>[\w\-\,]+)/(?P<uuid>[\w\-]+)/$', DocumentsFinalizeWizard.as_view(),
        # ~ name='documents_finalize'
    # ~ ),
    url(
        r'^add/(?P<doc_id>[\w\-]+)/(?P<uuid>[\w\-]+)/$', DocumentWizard.as_view(),
        name='document_wizard'
    ),
    url(
        r'^add/email/(?P<doc_id>[\w\-\,]+)/(?P<uuid>[\w\-]+)/$', EmailFinalizeWizard.as_view(),
        name='email_finalize'
    ),
]

api_urls = [
    url(
        r'^staging_folders/file/(?P<staging_folder_pk>[0-9]+)/(?P<encoded_filename>.+)/image/$',
        APIStagingSourceFileImageView.as_view(),
        name='stagingfolderfile-image-view'
    ),
    url(
        r'^staging_folders/file/(?P<staging_folder_pk>[0-9]+)/(?P<encoded_filename>.+)/$',
        APIStagingSourceFileView.as_view(), name='stagingfolderfile-detail'
    ),
    url(
        r'^staging_folders/$', APIStagingSourceListView.as_view(),
        name='stagingfolder-list'
    ),
    url(
        r'^staging_folders/(?P<pk>[0-9]+)/$', APIStagingSourceView.as_view(),
        name='stagingfolder-detail'
    )
]
