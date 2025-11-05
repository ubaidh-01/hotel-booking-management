from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('proof-verification/', views.payment_proof_dashboard, name='payment_proof_dashboard'),
    path('<int:payment_id>/proof/', views.payment_proof_detail, name='payment_proof_detail'),
    path('<int:payment_id>/upload-proof/', views.tenant_payment_proof_upload, name='tenant_payment_proof_upload'),
]