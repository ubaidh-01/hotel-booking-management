from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('switch-to-permanent/<int:contract_id>/', views.switch_to_permanent_room, name='switch_to_permanent'),
]