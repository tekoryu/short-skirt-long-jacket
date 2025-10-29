from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.main_page, name='main'),
    path('settings/', views.settings, name='settings'),
]

