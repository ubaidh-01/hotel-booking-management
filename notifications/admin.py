from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'notification_type',
        'tenant_display',
        'subject',
        'status',
        'sent_at',
        'created_at'
    ]

    list_filter = [
        'notification_type',
        'status',
        'sent_at',
        'created_at'
    ]

    search_fields = [
        'tenant__full_name',
        'subject',
        'recipient_email',
        'message'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'sent_at'
    ]

    fieldsets = (
        ('Notification Details', {
            'fields': (
                'notification_type',
                'status',
                'subject',
                'message'
            )
        }),
        ('Relationships', {
            'fields': (
                'tenant',
                'related_booking',
                'related_payment'
            ),
            'classes': ('collapse',)
        }),
        ('Recipient Information', {
            'fields': ('recipient_email',),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': (
                'scheduled_for',
                'sent_at'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )

    def tenant_display(self, obj):
        return obj.tenant.full_name if obj.tenant else "System"

    tenant_display.short_description = 'Tenant'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'tenant',
            'related_booking',
            'related_payment'
        )