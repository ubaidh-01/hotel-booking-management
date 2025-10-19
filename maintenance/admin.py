from django.contrib import admin
from .models import MaintenanceTicket


@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'tenant', 'room', 'title', 'priority', 'status', 'reported_date']
    list_filter = ['priority', 'status', 'reported_date']
    search_fields = ['ticket_number', 'tenant__full_name', 'room__room_code', 'title']
    readonly_fields = ['ticket_number', 'reported_date']
    list_editable = ['priority', 'status']

    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_number', 'tenant', 'room', 'title', 'description')
        }),
        ('Priority & Status', {
            'fields': ('priority', 'status')
        }),
        ('Media Uploads', {
            'fields': ('photos', 'videos'),
            'classes': ('collapse',)
        }),
        ('Assignment & Tracking', {
            'fields': ('assigned_to', 'estimated_fix_date', 'resolved_date')
        }),
        ('Staff Updates', {
            'fields': ('staff_notes', 'action_taken'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant', 'room')