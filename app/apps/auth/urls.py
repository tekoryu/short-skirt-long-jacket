from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    
    # Permission Management URLs
    path('permissions/', views.PermissionListView.as_view(), name='permission_list'),
    path('user-permissions/', views.UserPermissionListView.as_view(), name='user_permission_list'),
    path('assign-permission/', views.assign_permission_view, name='assign_permission'),
    path('assign-group/', views.assign_group_view, name='assign_group'),
    path('revoke-permission/<int:permission_id>/', views.revoke_permission_view, name='revoke_permission'),
    
    # API URLs
    path('api/check-permission/', views.check_permission_api, name='check_permission_api'),
]
