from django.db import models
from tenants.models import Tenant
from bookings.models import Booking
from payments.models import Payment
from django.utils import timezone


class NotificationLog(models.Model):
    NOTIFICATION_TYPES = [
        ('rent_reminder', 'Rent Reminder'),
        ('contract_reminder', 'Contract Reminder'),
        ('birthday_wish', 'Birthday Wish'),
        ('late_fee_invoice', 'Late Fee Invoice'),
        ('move_out_reminder', 'Move Out Reminder'),
        ('test_notification', 'Test Notification'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]

    # Required fields
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subject = models.CharField(max_length=200)

    # Optional relationships
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    related_booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    related_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)

    # Content and tracking
    message = models.TextField(blank=True)
    recipient_email = models.EmailField(blank=True)

    # Timing
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'

    def __str__(self):
        tenant_name = self.tenant.full_name if self.tenant else "System"
        return f"{self.get_notification_type_display()} - {tenant_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        # Set recipient email if tenant exists
        if self.tenant and self.tenant.user and not self.recipient_email:
            self.recipient_email = self.tenant.user.email

        # Set sent_at timestamp when status changes to 'sent'
        if self.status == 'sent' and not self.sent_at:
            self.sent_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_successful(self):
        return self.status == 'sent'

    @property
    def days_ago(self):
        if self.sent_at:
            return (timezone.now() - self.sent_at).days
        return None