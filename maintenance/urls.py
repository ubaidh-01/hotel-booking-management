from django.urls import path
from . import views

app_name = 'maintance'

urlpatterns = [
    path('tenant/', views.tenant_maintenance_dashboard, name='tenant_maintenance_dashboard'),
    path('tenant/ticket/<int:ticket_id>/', views.tenant_ticket_detail, name='tenant_ticket_detail'),
    path('tenant/new/', views.create_maintenance_request, name='create_maintenance_request'),
]
