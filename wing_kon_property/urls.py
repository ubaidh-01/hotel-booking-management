from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
    path('contracts/', include('contracts.urls')),
    path('', include('properties.urls')),  # Includes CRM room URLs
    path('', login_required(RedirectView.as_view(url='/reports/', permanent=False))),
]