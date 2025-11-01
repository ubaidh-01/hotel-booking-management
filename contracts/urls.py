from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('switch-to-permanent/<int:contract_id>/', views.switch_to_permanent_room, name='switch_to_permanent'),
    path('<int:contract_id>/sign/', views.contract_signing_page, name='contract_signing'),
    path('<int:contract_id>/sign/save/', views.save_tenant_signature, name='save_tenant_signature'),
    path('<int:contract_id>/staff-sign/', views.staff_sign_contract, name='staff_sign_contract'),
]