from django.conf.urls import url
from .views import ( DocumentStatisticView, ShowStatisticView,
    SignatureImageDeleteView, 
    RegisterFileAutocomplete, QuotationFileAutocomplete 
)

urlpatterns = [
    url(r'^statistics/$', DocumentStatisticView.as_view(), name='document_statistic'),
    url(r'^show_statistics/(?P<year_from>\d+)/(?P<month_from>\d+)/(?P<day_from>\d+)/(?P<year_to>\d+)/(?P<month_to>\d+)/(?P<day_to>\d+)/$', ShowStatisticView.as_view(), name='show_statistics'),
    url(
        r'^multiple/sig/$', SignatureImageDeleteView.as_view(),
        name='signature_image_delete_view'
    ),
    url(
        r'^register-file-autocomplete/$',
        RegisterFileAutocomplete.as_view(),
        name='register_file_autocomplete',
    ),
    url(
        r'^quotation-file-autocomplete/$',
        QuotationFileAutocomplete.as_view(),
        name='quotation_file_autocomplete',
    ),
]
