from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_dashboard, name='dashboard'),
    path('test/', views.send_test_notification, name='test_notification'),
]