from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    # CRM Room URLs (staff only)
    path('crm/rooms/', views.crm_room_list, name='crm_room_list'),
    path('crm/rooms/<str:room_code>/', views.crm_room_detail, name='crm_room_detail'),
]