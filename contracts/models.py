from django.db import models
from bookings.models import Booking
from tenants.models import Tenant
from properties.models import Room
import uuid


class Contract(models.Model):
    CONTRACT_STATUS = [
        ('draft', 'Draft'),
        ('sent', 'Sent for Signature'),
        ('signed', 'Signed'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ]

    # Basic Information
    contract_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)

    # Contract Details
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stamp_duty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status & Signatures
    status = models.CharField(max_length=20, choices=CONTRACT_STATUS, default='draft')
    signed_date = models.DateTimeField(null=True, blank=True)
    digital_signature = models.TextField(blank=True)  # Store signature data

    # Temporary Stay Information (for your requirement #12)
    temporary_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='temporary_contracts')
    temporary_stay_start = models.DateField(null=True, blank=True)
    temporary_stay_end = models.DateField(null=True, blank=True)

    # Auto-generated fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Contract {self.contract_number} - {self.booking.tenant.full_name}"

    @property
    def is_active(self):
        return self.status == 'signed'

    def save(self, *args, **kwargs):
        if not self.contract_number:
            self.contract_number = f"CONTRACT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)