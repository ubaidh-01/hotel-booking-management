from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('empty-rooms/', views.empty_rooms_report, name='empty_rooms'),
    path('rent-owed/', views.rent_owed_report, name='rent_owed'),
    path('move-out/', views.move_out_report, name='move_out'),
    path('monthly-sales/', views.monthly_sales_report, name='monthly_sales'),
    path('utilities/', views.utilities_report, name='utilities'),
]