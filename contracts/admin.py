from django.contrib import admin
from django.utils.html import format_html
from .models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        'contract_number',
        'booking',
        'start_date',
        'end_date',
        'status',
        'temporary_stay_status',
        'signed_date'
    ]
    list_filter = ['status', 'start_date', 'end_date', 'is_temporary_stay_active']
    search_fields = [
        'contract_number',
        'booking__tenant__full_name',
        'booking__room__room_code',
        'temporary_room__room_code'
    ]
    readonly_fields = [
        'contract_number',
        'created_at',
        'updated_at',
        'rent_difference_display',
        'temporary_stay_duration_display'
    ]
    list_editable = ['status']

    fieldsets = (
        ('Contract Information', {
            'fields': ('contract_number', 'booking', 'start_date', 'end_date')
        }),
        ('Financial Terms', {
            'fields': ('monthly_rent', 'security_deposit', 'stamp_duty')
        }),
        ('Temporary Stay Information', {
            'fields': (
                'is_temporary_stay_active',  # STAFF MANUALLY CONTROLS THIS
                'temporary_room',
                'temporary_stay_start',
                'temporary_stay_end',
                'temporary_stay_rent',
                'permanent_stay_rent',
                'rent_difference_display',  # This can auto-calculate
                'temporary_stay_duration_display'  # This can auto-calculate
            )
        }),
        ('Signature Status', {
            'fields': ('status', 'signed_date', 'digital_signature')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def temporary_stay_status(self, obj):
        """Show status based on MANUAL is_temporary_stay_active field"""
        if obj.is_temporary_stay_active:
            # Check if temporary stay period has ended (for info only)
            from django.utils import timezone
            today = timezone.now().date()
            if obj.temporary_stay_end and obj.temporary_stay_end < today:
                return format_html('<span style="color: red;">⚠️ Ended (Check needed)</span>')
            else:
                return format_html('<span style="color: orange;">🛌 Active</span>')
        return format_html('<span style="color: green;">➡️ Permanent</span>')

    temporary_stay_status.short_description = 'Temp Stay'

    def rent_difference_display(self, obj):
        """Auto-calculate rent difference (this is useful)"""
        if obj.rent_difference > 0:
            return format_html('<span style="color: green;">+HK${} (Refund to tenant)</span>', obj.rent_difference)
        elif obj.rent_difference < 0:
            return format_html('<span style="color: red;">HK${} (Additional payment)</span>', abs(obj.rent_difference))
        return "No difference"

    rent_difference_display.short_description = 'Rent Difference'

    def temporary_stay_duration_display(self, obj):
        """Auto-calculate duration (this is useful)"""
        if obj.temporary_stay_duration > 0:
            return f"{obj.temporary_stay_duration} days"
        return "Not set"

    temporary_stay_duration_display.short_description = 'Temp Stay Duration'

    def save_model(self, request, obj, form, change):
        """ONLY calculate rent difference - don't touch is_temporary_stay_active"""
        # Calculate rent difference if rent amounts changed
        if any(field in form.changed_data for field in ['temporary_stay_rent', 'permanent_stay_rent']):
            obj.calculate_rent_difference()

        # Save WITHOUT auto-setting temporary stay status
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'booking__tenant',
            'booking__room',
            'temporary_room'
        )

    # Keep the bulk actions for manual control
    actions = ['activate_temporary_stay', 'deactivate_temporary_stay']

    def activate_temporary_stay(self, request, queryset):
        """MANUALLY activate temporary stays"""
        updated = queryset.update(is_temporary_stay_active=True)
        self.message_user(request, f"{updated} temporary stays activated.")

    activate_temporary_stay.short_description = "Activate temporary stay"

    def deactivate_temporary_stay(self, request, queryset):
        """MANUALLY deactivate temporary stays"""
        updated = queryset.update(is_temporary_stay_active=False)
        self.message_user(request, f"{updated} temporary stays deactivated.")

    deactivate_temporary_stay.short_description = "Deactivate temporary stay"