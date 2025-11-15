from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
    path('contracts/', include('contracts.urls')),
    path('', include('properties.urls')),  # Includes CRM room URLs
    path('', login_required(RedirectView.as_view(url='/reports/', permanent=False))),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
