from django.db import models
from bookings.models import Booking
from tenants.models import Tenant
from properties.models import Room
import uuid
from decimal import Decimal


class Payment(models.Model):
    PAYMENT_TYPES = [
        ('deposit', 'Deposit'),
        ('rent', 'Rent'),
        ('security_deposit', 'Security Deposit'),
        ('stamp_duty', 'Stamp Duty'),
        ('utility', 'Utility Bill'),
        ('late_fee', 'Late Fee'),
        ('refund', 'Refund'),
    ]

    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # Payment Identification
    receipt_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)

    # Payment Details
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    # Dates
    payment_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)

    # Reference & Proof
    bank_reference = models.CharField(max_length=200, blank=True)
    proof_of_payment = models.FileField(upload_to='payment_proofs/', null=True, blank=True)

    # For rent payments
    rent_month = models.DateField(null=True, blank=True)  # Which month's rent
    is_rent_paid = models.BooleanField(default=False)

    # Late fee tracking
    late_fee_days = models.IntegerField(default=0)
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.amount} - {self.get_payment_type_display()}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCPT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class UtilityBill(models.Model):
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE)
    bill_type = models.CharField(max_length=20, choices=[
        ('electricity', 'Electricity'),
        ('water', 'Water'),
        ('gas', 'Gas'),
        ('internet', 'Internet'),
    ])
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bill_date = models.DateField()
    due_date = models.DateField()
    bill_photo = models.FileField(upload_to='utility_bills/', null=True, blank=True)

    # For pro-rata calculation
    total_tenants = models.IntegerField(default=1)
    is_settled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_bill_type_display()} - {self.property.name} - {self.bill_date}"