from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


def staff_required(user):
    return user.is_staff


urlpatterns = [
    path('admin/', admin.site.urls),

    # CRM Routes (Staff Only)
    path('crm/reports/', include('reports.urls')),
    path('crm/notifications/', include('notifications.urls')),
    path('crm/contracts/', include('contracts.urls')),
    path('crm/properties/', include('properties.urls')),
    path('crm/maintenance/', include('maintenance.urls')),
    path('crm/payments/', include('payments.urls')),

    # Website Routes (Public)
    path('', include('website.urls')),

    # Default redirect for staff users to CRM dashboard
    path('crm/',
         login_required(user_passes_test(staff_required)(RedirectView.as_view(pattern_name='reports:dashboard')))),

    # Default redirect for regular users to website
    path('home/', RedirectView.as_view(pattern_name='website:home', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)