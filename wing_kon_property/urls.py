from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
    path('', include('properties.urls')),  # Includes CRM room URLs
    path('', lambda request: redirect('/reports/')),  # Default to CRM dashboard
]