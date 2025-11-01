from django.db import models
from django.utils import timezone

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

    # Temporary Stay Information
    temporary_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='temporary_contracts')
    temporary_stay_start = models.DateField(null=True, blank=True)
    temporary_stay_end = models.DateField(null=True, blank=True)

    temporary_stay_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                              help_text="Rent during temporary stay")
    permanent_stay_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                              help_text="Rent for permanent room")
    rent_difference = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                          help_text="Positive = refund, Negative = additional payment")

    # Status Tracking
    is_temporary_stay_active = models.BooleanField(default=False)

    renewal_status = models.CharField(
        max_length=20,
        choices=[
            ('not_sent', 'Renewal Not Sent'),
            ('sent', 'Renewal Sent'),
            ('renewed', 'Renewed'),
            ('declined', 'Declined'),
        ],
        default='not_sent'
    )
    renewal_sent_date = models.DateTimeField(null=True, blank=True)
    move_out_notice_sent = models.BooleanField(default=False)
    move_out_notice_sent_date = models.DateTimeField(null=True, blank=True)

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

    def calculate_rent_difference(self):
        """Calculate rent difference between temporary and permanent stays"""
        if self.temporary_stay_rent and self.permanent_stay_rent:
            self.rent_difference = self.permanent_stay_rent - self.temporary_stay_rent
        return self.rent_difference

    def switch_to_permanent_room(self):
        """Switch from temporary to permanent room"""
        if self.temporary_room and self.booking.room:
            # Update booking room
            old_room = self.booking.room
            self.booking.room = self.temporary_room
            self.booking.save()

            # Update room statuses
            old_room.status = 'available'
            old_room.save()

            self.temporary_room.status = 'occupied'
            self.temporary_room.save()

            self.is_temporary_stay_active = False
            self.save()

            return True
        return False

    @property
    def temporary_stay_duration(self):
        """Calculate temporary stay duration in days"""
        if self.temporary_stay_start and self.temporary_stay_end:
            return (self.temporary_stay_end - self.temporary_stay_start).days
        return 0

    @property
    def needs_room_switch(self):
        """Check if temporary stay has ended and needs switching"""
        if self.is_temporary_stay_active and self.temporary_stay_end:
            from django.utils import timezone
            return timezone.now().date() >= self.temporary_stay_end
        return False

    @property
    def days_until_expiry(self):
        """Days until contract expires"""
        return (self.end_date - timezone.now().date()).days

    @property
    def needs_renewal_reminder(self):
        """Check if renewal reminder should be sent (3 weeks before)"""
        return (self.days_until_expiry <= 21 and
                self.days_until_expiry > 14 and
                self.renewal_status == 'not_sent')

    @property
    def needs_move_out_reminder(self):
        """Check if move out reminder should be sent (3 weeks before)"""
        return (self.days_until_expiry <= 21 and
                self.days_until_expiry > 0 and
                not self.move_out_notice_sent)
