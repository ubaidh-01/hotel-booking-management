from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import datetime, timedelta
from .models import NotificationLog
from .tasks import send_test_email


def staff_required(view_func):
    """Decorator that checks if user is staff member"""
    decorated_view_func = login_required(user_passes_test(
        lambda u: u.is_staff,
        login_url='/admin/login/'
    )(view_func))
    return decorated_view_func


@staff_required
def notification_dashboard(request):
    """Dashboard for notification system"""
    today = timezone.now().date()

    # Recent notifications (last 7 days)
    recent_notifications = NotificationLog.objects.filter(
        created_at__gte=today - timedelta(days=7)
    ).select_related('tenant')[:50]

    # Notification statistics
    stats = {
        'total_sent': NotificationLog.objects.filter(status='sent').count(),
        'total_failed': NotificationLog.objects.filter(status='failed').count(),
        'today_sent': NotificationLog.objects.filter(
            sent_at__date=today,
            status='sent'
        ).count(),
        'rent_reminders': NotificationLog.objects.filter(
            notification_type='rent_reminder'
        ).count(),
        'contract_reminders': NotificationLog.objects.filter(
            notification_type='contract_reminder'
        ).count(),
    }

    context = {
        'title': 'Notification System Dashboard',
        'recent_notifications': recent_notifications,
        'stats': stats,
        'today': today,
    }
    return render(request, 'notifications/dashboard.html', context)


@staff_required
def send_test_notification(request):
    """Send a test notification"""
    # Trigger test email task
    send_test_email()

    # Create log entry
    NotificationLog.objects.create(
        notification_type='rent_reminder',
        status='sent',
        message='Test notification sent manually by admin.'
    )

    return render(request, 'notifications/test_sent.html')