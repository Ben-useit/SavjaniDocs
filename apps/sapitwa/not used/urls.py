from django.conf.urls import url

from .views import PermissionDeleteView, permissions_edit_view, permissions_list_view, permissions_create_view
app_name = 'sapitwa'
urlpatterns = [
    url(
        regex=r'^permissions/(?P<object_id>\d+)/list/$',name='permissions_list', 
        view=permissions_list_view
    ),
    url(
        regex=r'^permissions/(?P<acl_id>\d+)/edit/$', name='permissions_edit',
        view=permissions_edit_view
    ),
    url(
        regex=r'^permissions/(?P<object_id>\d+)/create/$', name='permissions_create',
        view=permissions_create_view
    ),
    url(
        regex=r'^permissions/(?P<acl_id>\d+)/delete/$', name='permissions_delete',
        view=PermissionDeleteView.as_view()
    ),
]
