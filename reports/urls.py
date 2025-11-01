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
    path('temporary-stay/', views.temporary_stay_report, name='temporary_stay'),
    path('owners/', views.owners_report, name='owners_report'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('rent-increase/', views.rent_increase_report, name='rent_increase_report'),

]