from datetime import timedelta
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
    address_chinese = models.TextField(null=True, blank=True)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    total_rooms = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_property_type_display()}"

    def get_kitchen_images(self):
        """Get all kitchen images for this property"""
        return self.property_images.filter(image_type='kitchen')

    def get_living_room_images(self):
        """Get all living room images for this property"""
        return self.property_images.filter(image_type='living_room')

    def get_toilet_images(self):
        """Get all toilet images for this property"""
        return self.property_images.filter(image_type='toilet')

    def get_street_level_images(self):
        """Get all street level images for this property"""
        return self.property_images.filter(image_type='street_level')

    def get_other_images(self):
        """Get all other property images"""
        return self.property_images.filter(image_type='other')

    def get_main_kitchen_image(self):
        """Get the first kitchen image (useful for thumbnails)"""
        return self.property_images.filter(image_type='kitchen').first()

    def get_main_living_room_image(self):
        """Get the first living room image"""
        return self.property_images.filter(image_type='living_room').first()

    def get_main_toilet_image(self):
        """Get the first toilet image"""
        return self.property_images.filter(image_type='toilet').first()

    def get_main_street_level_image(self):
        """Get the first street level image"""
        return self.property_images.filter(image_type='street_level').first()


def property_image_upload_path(instance, filename):
    """Generate upload path for property images"""
    return f"properties/{instance.property.name}/images/{instance.image_type}/{filename}"


class PropertyImage(models.Model):
    IMAGE_TYPES = [
        ('kitchen', 'Kitchen'),
        ('living_room', 'Living Room'),
        ('toilet', 'Toilet'),
        ('street_level', 'Street Level'),
        ('other', 'Other'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="property_images")
    image = models.ImageField(upload_to=property_image_upload_path)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES)
    caption = models.CharField(max_length=200, blank=True, null=True)
    is_primary = models.BooleanField(default=False, help_text="Mark as primary image for this type")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['image_type', '-is_primary', 'uploaded_at']

    def __str__(self):
        return f"{self.get_image_type_display()} - {self.property.name}"

    def save(self, *args, **kwargs):
        # If this image is marked as primary, ensure no other images of same type are primary
        if self.is_primary:
            PropertyImage.objects.filter(
                property=self.property,
                image_type=self.image_type
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


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
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2500.00)
    status = models.CharField(max_length=20, choices=ROOM_STATUS, default='available')
    post_ad_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Price advertised to public (for rent increase detection)"
    )

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

    def needs_rent_increase_notice(self):
        from contracts.models import Contract

        """Check if rent is below HK$1500 and contract ending soon"""
        if self.post_ad_price and self.post_ad_price < 1500:
            # Check if any active contract is ending in next 30 days
            today = timezone.now().date()
            ending_soon = Contract.objects.filter(
                booking__room=self,
                end_date__lte=today + timedelta(days=30),
                end_date__gte=today,
                status='signed'
            ).exists()
            return ending_soon
        return False

    def get_ending_contracts(self):
        from contracts.models import Contract
        """Get contracts ending soon for this room"""
        today = timezone.now().date()
        return Contract.objects.filter(
            booking__room=self,
            end_date__lte=today + timedelta(days=30),
            end_date__gte=today,
            status = 'signed'
    ).select_related('booking__tenant')



def room_photo_upload_path(instance, filename):
    return f"rooms/{instance.room.room_code}/photos/{filename}"

def room_video_upload_path(instance, filename):
    return f"rooms/{instance.room.room_code}/videos/{filename}"
    return f"rooms/{instance.room.room_code}/videos/{filename}"

class RoomPhoto(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="room_photos")
    image = models.ImageField(upload_to=room_photo_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.room.room_code}"


class RoomVideo(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="room_videos")
    video = models.FileField(upload_to=room_video_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video for {self.room.room_code}"



class Owner(models.Model):
    name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    bank_account = models.CharField(max_length=100, blank=True)
    management_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

    @property
    def active_properties_count(self):
        return self.property_ownerships.filter(is_active=True).count()

    @property
    def total_rent_owed(self):
        """Total rent owed to this owner across all properties"""
        active_ownerships = self.property_ownerships.filter(is_active=True)
        return sum(ownership.rent_owed for ownership in active_ownerships)


class PropertyOwnership(models.Model):
    property_obj = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_ownerships')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='property_ownerships')
    ownership_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    management_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly management fee")
    contract_start = models.DateField()
    contract_end = models.DateField()
    monthly_rent_to_owner = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly rent paid to owner")
    is_active = models.BooleanField(default=True)

    # Rent payment tracking to owner
    last_rent_paid_date = models.DateField(null=True, blank=True)
    next_rent_due_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.owner.name} - {self.property_obj.name}"  # Updated to property_obj

    @property
    def rent_owed(self):
        """Calculate current rent owed to owner"""
        if not self.is_active:
            return 0

        # Simple calculation: monthly rent * months since last payment
        if self.last_rent_paid_date:
            months_owed = (timezone.now().date() - self.last_rent_paid_date).days // 30
        else:
            months_owed = (timezone.now().date() - self.contract_start).days // 30

        return self.monthly_rent_to_owner * max(1, months_owed)

    @property
    def contract_expiring_soon(self):
        """Check if contract expires in next 30 days"""
        days_until_end = (self.contract_end - timezone.now().date()).days
        return 0 <= days_until_end <= 30

    def save(self, *args, **kwargs):
        # Set next rent due date if not set
        if not self.next_rent_due_date and self.last_rent_paid_date:
            self.next_rent_due_date = self.last_rent_paid_date + timedelta(days=30)
        elif not self.next_rent_due_date:
            self.next_rent_due_date = self.contract_start + timedelta(days=30)

        super().save(*args, **kwargs)