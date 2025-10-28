from django.urls import path
from . import views

app_name = 'cities'

urlpatterns = [
    path('', views.CityListView.as_view(), name='city_list'),
    path('download/', views.download_cities, name='download_cities'),
    path('edit/<int:city_id>/', views.edit_city, name='edit_city'),
    path('api/', views.city_api, name='city_api'),
]
