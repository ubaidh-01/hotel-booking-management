from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'tenant', 'room', 'move_in_date', 'move_out_date', 'status', 'payment_status', 'room_status']
    list_filter = ['status', 'payment_status', 'move_in_date', 'move_out_date']
    search_fields = ['tenant__full_name', 'room__room_code', 'id']
    readonly_fields = ['booking_date', 'confirmed_date', 'room_status_display']
    list_editable = ['status', 'payment_status']

    fieldsets = (
        ('Booking Information', {
            'fields': ('tenant', 'room', 'move_in_date', 'move_out_date', 'duration_months')
        }),
        ('Status Tracking', {
            'fields': ('status', 'payment_status', 'room_status_display')
        }),
        ('Financial Details', {
            'fields': ('monthly_rent', 'deposit_paid', 'total_amount_paid')
        }),
        ('Actual Dates', {
            'fields': ('actual_move_in_date', 'actual_move_out_date'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('special_requests',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('booking_date', 'confirmed_date'),
            'classes': ('collapse',)
        })
    )

    def room_status_display(self, obj):
        return obj.room.get_status_display()

    room_status_display.short_description = 'Current Room Status'

    def room_status(self, obj):
        return obj.room.get_status_display()

    room_status.short_description = 'Room Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant', 'room')