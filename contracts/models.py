import logging
import random

from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from bookings.models import Booking
from notifications.whatsapp_service import WhatsAppService
from properties.models import Room
import uuid

logger = logging.getLogger(__name__)


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
    digital_signature_tenant = models.TextField(blank=True)  # Store tenant's signature data
    digital_signature_staff = models.TextField(blank=True)  # Store staff signature
    tenant_signed_date = models.DateTimeField(null=True, blank=True)
    staff_signed_date = models.DateTimeField(null=True, blank=True)

    # Email and WhatsApp verification
    tenant_email_verified = models.BooleanField(default=False)
    tenant_whatsapp_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True)
    whatsapp_verification_code = models.CharField(max_length=6, blank=True)

    # Contract generation
    contract_pdf = models.FileField(upload_to='contracts/pdfs/', null=True, blank=True)
    contract_hash = models.CharField(max_length=64, blank=True)  # For integrity verification

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

    @property
    def is_fully_signed(self):
        """Check if contract is fully signed by both parties"""
        return bool(self.digital_signature_tenant and self.digital_signature_staff)

    @property
    def signing_status(self):
        """Get current signing status"""
        if self.is_fully_signed:
            return 'fully_signed'
        elif self.digital_signature_tenant:
            return 'tenant_signed'
        elif self.digital_signature_staff:
            return 'staff_signed'
        else:
            return 'unsigned'

    def generate_contract_pdf(self):
        """Generate PDF version of the contract"""
        try:
            from weasyprint import HTML
            from django.template.loader import render_to_string
            import hashlib

            context = {
                'contract': self,
                'tenant': self.booking.tenant,
                'room': self.booking.room,
                'today': timezone.now().date(),
            }

            html_string = render_to_string('contracts/contract_pdf.html', context)
            pdf_file = HTML(string=html_string).write_pdf()

            # Generate hash for integrity
            contract_hash = hashlib.sha256(pdf_file).hexdigest()

            # Save PDF
            filename = f"contract_{self.contract_number}_{timezone.now().strftime('%Y%m%d')}.pdf"
            self.contract_pdf.save(filename, ContentFile(pdf_file), save=False)
            self.contract_hash = contract_hash
            self.save()

            return True
        except Exception as e:
            logger.error(f"Failed to generate contract PDF: {e}")
            return False

    def send_for_tenant_signature(self):
        from notifications.services import EmailService

        """Send contract to tenant for digital signature"""
        try:
            # Generate verification codes
            self.email_verification_code = str(random.randint(100000, 999999))
            self.whatsapp_verification_code = str(random.randint(100000, 999999))
            self.save()

            # Send email with signing link
            EmailService.send_contract_for_signature(self)

            # Send WhatsApp verification if number provided
            if self.booking.tenant.whatsapp_number:
                WhatsAppService.send_verification_code(self)

            return True
        except Exception as e:
            logger.error(f"Failed to send contract for signature: {e}")
            return False
