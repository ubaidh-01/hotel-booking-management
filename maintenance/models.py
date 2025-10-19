from django.db import models
from tenants.models import Tenant
from properties.models import Room


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

    class Meta:
        ordering = ['-reported_date']

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last_ticket = MaintenanceTicket.objects.order_by('-id').first()
            last_number = int(last_ticket.ticket_number.split('-')[1]) if last_ticket else 0
            self.ticket_number = f"MT-{last_number + 1:05d}"
        super().save(*args, **kwargs)