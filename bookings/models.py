from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from properties.models import Room
from tenants.models import Tenant


class Booking(models.Model):
    BOOKING_STATUS = [
        ('pending', 'Pending'),  # Booking created but not confirmed
        ('confirmed', 'Confirmed'),  # Deposit paid, room reserved
        ('active', 'Active'),  # Tenant moved in
        ('completed', 'Completed'),  # Tenant moved out successfully
        ('cancelled', 'Cancelled'),  # Booking cancelled
        ('terminated', 'Terminated'),  # Contract terminated early
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('deposit_paid', 'Deposit Paid'),
        ('fully_paid', 'Fully Paid'),
        ('overdue', 'Overdue'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    # Booking Details
    move_in_date = models.DateField()
    move_out_date = models.DateField()
    duration_months = models.IntegerField(help_text="Duration of stay in months")

    # Status Tracking
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    # Financial Details
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Dates
    booking_date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(null=True, blank=True)
    actual_move_in_date = models.DateField(null=True, blank=True)
    actual_move_out_date = models.DateField(null=True, blank=True)

    # Additional Information
    special_requests = models.TextField(blank=True)

    class Meta:
        ordering = ['-booking_date']

    def __str__(self):
        return f"Booking #{self.id} - {self.tenant.full_name} - {self.room.room_code}"

    @property
    def total_rent_amount(self):
        return self.monthly_rent * self.duration_months

    @property
    def balance_due(self):
        return self.total_rent_amount - self.total_amount_paid

    @property
    def is_currently_active(self):
        """Check if booking should be active based on dates"""
        today = timezone.now().date()
        return (self.status == 'active' and
                self.move_in_date <= today <= self.move_out_date)

    def update_room_status(self):
        """Automatically update room status based on booking status"""
        room = self.room

        if self.status == 'confirmed':
            room.status = 'reserved'
        elif self.status == 'active' and self.is_currently_active:
            room.status = 'occupied'
        elif self.status in ['completed', 'cancelled', 'terminated']:
            room.status = 'available'
        elif self.status == 'pending':
            # Room remains available for pending bookings
            room.status = 'available'
        else:
            # Fallback - check if any active booking exists for this room
            active_booking = Booking.objects.filter(
                room=room,
                status='active',
                move_in_date__lte=timezone.now().date(),
                move_out_date__gte=timezone.now().date()
            ).exists()
            room.status = 'occupied' if active_booking else 'available'

        room.save()


# Signal to automatically update room status when booking changes
@receiver(post_save, sender=Booking)
def update_room_status_on_booking_change(sender, instance, created, **kwargs):
    """Update room status whenever booking is saved"""
    instance.update_room_status()


@receiver(pre_save, sender=Booking)
def handle_booking_status_change(sender, instance, **kwargs):
    """Handle automatic status transitions based on dates"""
    if instance.pk:  # Only for existing instances
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            today = timezone.now().date()

            # Auto-activate booking on move-in date
            if (old_instance.status == 'confirmed' and
                instance.status == 'confirmed' and
                instance.move_in_date <= today and
                instance.move_out_date >= today):
                instance.status = 'active'
                if not instance.actual_move_in_date:
                    instance.actual_move_in_date = today

            # Auto-complete booking after move-out date
            if (old_instance.status == 'active' and
                    instance.status == 'active' and
                    instance.move_out_date < today):
                instance.status = 'completed'
                if not instance.actual_move_out_date:
                    instance.actual_move_out_date = today

        except Booking.DoesNotExist:
            pass
