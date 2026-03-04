import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User

from tenants.models import Tenant
from properties.models import Property, Room
from bookings.models import Booking


@pytest.mark.django_db
class TestRoomModel:

    def setup_method(self):
        self.user = User.objects.create_user(username="alice", email="alice@example.com", password="pass")
        self.tenant = Tenant.objects.create(
            user=self.user,
            full_name="Alice",
            nationality="Country",
            date_of_birth="1992-02-02",
            gender="female",
            phone_number="111222333"
        )
        self.property = Property.objects.create(name="Prop", address="Addr", property_type="apartment", total_rooms=2)
        self.room = Room.objects.create(
            property=self.property,
            room_code="C1",
            room_number="1",
            monthly_rent=4000
        )

    def create_booking(self, **kwargs):
        today = timezone.now().date()
        defaults = dict(
            tenant=self.tenant,
            room=self.room,
            move_in_date=today,
            move_out_date=today + timedelta(days=10),
            duration_months=1,
            monthly_rent=4000,
            status='active'
        )
        defaults.update(kwargs)
        return Booking.objects.create(**defaults)

    def test_get_absolute_url(self):
        assert self.room.get_absolute_url() == f"/{self.room.room_code}/"

    def test_get_current_booking_returns_active_booking(self):
        booking = self.create_booking()
        current = self.room.get_current_booking()
        assert current == booking

    def test_update_status_from_bookings_sets_occupied_for_active(self):
        self.create_booking(status='active')
        self.room.update_status_from_bookings()
        self.room.refresh_from_db()
        assert self.room.status == 'occupied'

    def test_update_status_from_bookings_sets_reserved_for_confirmed_future(self):
        today = timezone.now().date()
        self.create_booking(status='confirmed', move_in_date=today + timedelta(days=2), move_out_date=today + timedelta(days=32))
        self.room.update_status_from_bookings()
        self.room.refresh_from_db()
        assert self.room.status == 'reserved'

    def test_update_status_from_bookings_changes_occupied_reserved_to_available_when_none(self):
        # set previous status to occupied then call update -> should set to available (if no active/confirmed)
        self.room.status = 'occupied'
        self.room.save()
        self.room.update_status_from_bookings()
        self.room.refresh_from_db()
        assert self.room.status == 'available'
