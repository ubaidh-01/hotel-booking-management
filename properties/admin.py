from django.contrib import admin
from .models import Property, Room


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'property_type', 'total_rooms', 'created_at']
    list_filter = ['property_type', 'created_at']
    search_fields = ['name', 'address']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['room_code', 'property', 'monthly_rent', 'status', 'current_tenant', 'has_private_bathroom']
    list_filter = ['status', 'property', 'has_private_bathroom', 'has_balcony']
    search_fields = ['room_code', 'property__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'current_tenant_display']
    list_editable = ['status']  # Quick edit status

    fieldsets = (
        ('Basic Information', {
            'fields': ('property', 'room_code', 'room_number', 'description')
        }),
        ('Financial', {
            'fields': ('monthly_rent', 'deposit_amount')
        }),
        ('Status & Features', {
            'fields': ('status', 'size_sqft', 'has_private_bathroom', 'has_balcony')
        }),
        ('Current Occupancy', {
            'fields': ('current_tenant_display',),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('photos', 'videos'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def current_tenant(self, obj):
        booking = obj.get_current_booking()
        return booking.tenant.full_name if booking else "Available"

    current_tenant.short_description = 'Current Tenant'

    def current_tenant_display(self, obj):
        booking = obj.get_current_booking()
        if booking:
            return f"{booking.tenant.full_name} (Until {booking.move_out_date})"
        return "No current tenant"

    current_tenant_display.short_description = 'Current Tenant'