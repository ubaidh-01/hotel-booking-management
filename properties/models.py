from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone


class Property(models.Model):
    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('building', 'Building'),
    ]

    name = models.CharField(max_length=200)
    address = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    total_rooms = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_property_type_display()}"


class Room(models.Model):
    ROOM_STATUS = [
        ('available', 'Available'),  # Ready for booking
        ('reserved', 'Reserved'),  # Booking confirmed, deposit paid
        ('occupied', 'Occupied'),  # Tenant actively living there
        ('maintenance', 'Under Maintenance'),  # Being repaired/cleaned
        ('temporary', 'Temporary Stay'),  # Short-term temporary occupancy
        ('cleaning', 'Being Cleaned'),  # Between tenants, being cleaned
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rooms')
    room_code = models.CharField(max_length=10, unique=True)  # c5a, c5b, etc.
    room_number = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2500.00)  # HK$2,500
    status = models.CharField(max_length=20, choices=ROOM_STATUS, default='available')
    photos = models.JSONField(default=list, blank=True)  # Store photo URLs
    videos = models.JSONField(default=list, blank=True)  # Store video URLs

    # Room features
    size_sqft = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    has_private_bathroom = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['room_code']

    def __str__(self):
        return f"{self.room_code} - {self.property.name}"

    def get_absolute_url(self):
        """URL for individual room pages - Requirement #6"""
        from django.urls import reverse
        return reverse('room_detail', kwargs={'room_code': self.room_code})

    def get_crm_room_url(self):
        """CRM room URL - stays within CRM system"""
        return f"/crm/rooms/{self.room_code}/"

    def get_current_booking(self):
        """Get the currently active booking for this room"""
        today = timezone.now().date()
        try:
            return self.booking_set.filter(
                status='active',
                move_in_date__lte=today,
                move_out_date__gte=today
            ).first()
        except:
            return None

    def update_status_from_bookings(self):
        """Update room status based on current bookings"""
        today = timezone.now().date()

        # Check for active bookings
        active_booking = self.booking_set.filter(
            status='active',
            move_in_date__lte=today,
            move_out_date__gte=today
        ).exists()

        # Check for confirmed (upcoming) bookings
        confirmed_booking = self.booking_set.filter(
            status='confirmed',
            move_in_date__gte=today
        ).exists()

        if active_booking:
            self.status = 'occupied'
        elif confirmed_booking:
            self.status = 'reserved'
        elif self.status in ['occupied', 'reserved']:
            # Only change to available if it was previously occupied/reserved
            self.status = 'available'
        # Don't change maintenance/cleaning/temporary statuses

        self.save()