from django.contrib import admin
from .models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'booking', 'start_date', 'end_date', 'status', 'signed_date']
    list_filter = ['status', 'start_date', 'end_date']
    search_fields = ['contract_number', 'booking__tenant__full_name', 'booking__room__room_code']
    readonly_fields = ['contract_number', 'created_at', 'updated_at']
    list_editable = ['status']

    fieldsets = (
        ('Contract Information', {
            'fields': ('contract_number', 'booking', 'start_date', 'end_date')
        }),
        ('Financial Terms', {
            'fields': ('monthly_rent', 'security_deposit', 'stamp_duty')
        }),
        ('Signature Status', {
            'fields': ('status', 'signed_date', 'digital_signature')
        }),
        ('Temporary Stay', {
            'fields': ('temporary_room', 'temporary_stay_start', 'temporary_stay_end'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('booking__tenant', 'booking__room')