from django.contrib import admin
from .models import Payment, UtilityBill


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'booking', 'payment_type', 'amount', 'payment_method', 'status', 'payment_date']
    list_filter = ['payment_type', 'payment_method', 'status', 'payment_date']
    search_fields = ['receipt_number', 'booking__tenant__full_name', 'bank_reference']
    readonly_fields = ['receipt_number', 'created_at']
    list_editable = ['status']

    fieldsets = (
        ('Payment Information', {
            'fields': ('receipt_number', 'booking', 'payment_type', 'amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'status', 'payment_date', 'due_date', 'received_date')
        }),
        ('Reference & Proof', {
            'fields': ('bank_reference', 'proof_of_payment')
        }),
        ('Rent Specific', {
            'fields': ('rent_month', 'is_rent_paid'),
            'classes': ('collapse',)
        }),
        ('Late Fees', {
            'fields': ('late_fee_days', 'late_fee_amount'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('booking__tenant', 'booking__room')


@admin.register(UtilityBill)
class UtilityBillAdmin(admin.ModelAdmin):
    list_display = ['property', 'bill_type', 'bill_amount', 'bill_date', 'due_date', 'is_settled']
    list_filter = ['bill_type', 'bill_date', 'is_settled']
    search_fields = ['property__name']
    list_editable = ['is_settled']

    fieldsets = (
        ('Bill Information', {
            'fields': ('property', 'bill_type', 'bill_amount', 'bill_date', 'due_date')
        }),
        ('Settlement', {
            'fields': ('total_tenants', 'is_settled')
        }),
        ('Document', {
            'fields': ('bill_photo',),
            'classes': ('collapse',)
        })
    )