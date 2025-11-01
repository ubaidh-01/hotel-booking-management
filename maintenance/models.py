import logging

from django.db import models
from django.utils import timezone

from notifications.services import EmailService
from tenants.models import Tenant
from properties.models import Room

logger = logging.getLogger(__name__)

class MaintenanceTicket(models.Model):
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    # Ticket Information
    ticket_number = models.CharField(max_length=20, unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    # Issue Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    # Photo/Video uploads
    photos = models.JSONField(default=list, blank=True)
    videos = models.JSONField(default=list, blank=True)

    # Tracking
    reported_date = models.DateTimeField(auto_now_add=True)
    assigned_to = models.CharField(max_length=100, blank=True)
    estimated_fix_date = models.DateField(null=True, blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)

    # Staff updates
    staff_notes = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)

    estimated_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateTimeField(null=True, blank=True)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Staff assignment and tracking
    assigned_staff = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_maintenance_tickets'
    )
    assigned_date = models.DateTimeField(null=True, blank=True)

    # Tenant communication
    tenant_notified = models.BooleanField(default=False)
    last_tenant_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-reported_date']

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.title}"

    @property
    def is_overdue(self):
        """Check if ticket is overdue based on estimated completion date"""
        if self.estimated_completion_date and self.status != 'resolved':
            return timezone.now().date() > self.estimated_completion_date
        return False

    @property
    def days_open(self):
        """Number of days since ticket was reported"""
        return (timezone.now() - self.reported_date).days

    @property
    def needs_tenant_update(self):
        """Check if tenant needs an update (more than 2 days since last update)"""
        if self.last_tenant_update:
            return (timezone.now() - self.last_tenant_update).days > 2
        return self.days_open > 2

    def update_tenant(self, message, staff_member=None):
        """Update tenant on ticket progress"""
        try:
            success = EmailService.send_maintenance_update(self, message)
            if success:
                self.last_tenant_update = timezone.now()
                self.tenant_notified = True
                self.save()

                # Log the communication
                MaintenanceUpdate.objects.create(
                    ticket=self,
                    staff_member=staff_member,
                    message=message,
                    communicated_to_tenant=True
                )
            return success
        except Exception as e:
            logger.error(f"Failed to update tenant for ticket {self.id}: {e}")
            return False

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last_ticket = MaintenanceTicket.objects.order_by('-id').first()
            last_number = int(last_ticket.ticket_number.split('-')[1]) if last_ticket else 0
            self.ticket_number = f"MT-{last_number + 1:05d}"
        super().save(*args, **kwargs)


class MaintenanceUpdate(models.Model):
    ticket = models.ForeignKey(MaintenanceTicket, on_delete=models.CASCADE, related_name='updates')
    staff_member = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    communicated_to_tenant = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update for {self.ticket.ticket_number} - {self.created_at}"