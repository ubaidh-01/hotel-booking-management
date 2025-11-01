from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('<int:booking_id>/move-out/', views.tenant_move_out_portal, name='tenant_move_out'),
    path('<int:booking_id>/move-out/inspection/', views.staff_move_out_inspection, name='move_out_inspection'),
    path('<int:booking_id>/process-refund/', views.process_refund, name='process_refund'),
]
