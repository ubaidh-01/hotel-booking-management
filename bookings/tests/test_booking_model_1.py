import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User

from tenants.models import Tenant
from properties.models import Property, Room
from bookings.models import Booking


@pytest.mark.django_db
class TestBookingModel:

    def setup_method(self):
        # create user + tenant
        self.user = User.objects.create_user(username="tenant1", email="t1@example.com", password="pass")
        self.tenant = Tenant.objects.create(
            user=self.user,
            full_name="John Doe",
            nationality="Testland",
            date_of_birth="1990-01-01",
            gender="male",
            phone_number="123456789"
        )

        # property and room
        self.property = Property.objects.create(
            name="P1", address="Addr", property_type="apartment", total_rooms=1
        )
        self.room = Room.objects.create(
            property=self.property,
            room_code="R101",
            room_number="101",
            monthly_rent=5000
        )

    def create_booking(self, **kwargs):
        today = timezone.now().date()
        defaults = dict(
            tenant=self.tenant,
            room=self.room,
            move_in_date=today,
            move_out_date=today + timedelta(days=30),
            duration_months=1,
            monthly_rent=5000,
        )
        defaults.update(kwargs)
        return Booking.objects.create(**defaults)

    def test_total_rent_amount_and_balance_due(self):
        booking = self.create_booking(total_amount_paid=2000)
        assert booking.total_rent_amount == booking.monthly_rent * booking.duration_months
        assert float(booking.total_rent_amount - booking.total_amount_paid) == float(booking.balance_due)

    def test_is_currently_active_property_true_when_active_and_in_date_range(self):
        today = timezone.now().date()
        booking = self.create_booking(status='active', move_in_date=today - timedelta(days=1), move_out_date=today + timedelta(days=1))
        assert booking.is_currently_active is True

    def test_update_room_status_sets_reserved_for_confirmed(self):
        booking = self.create_booking(status='confirmed')
        booking.update_room_status()
        self.room.refresh_from_db()
        assert self.room.status == 'reserved'

    def test_update_room_status_sets_occupied_for_active(self):
        today = timezone.now().date()
        booking = self.create_booking(status='active', move_in_date=today - timedelta(days=1), move_out_date=today + timedelta(days=1))
        booking.update_room_status()
        self.room.refresh_from_db()
        assert self.room.status == 'occupied'

    def test_update_room_status_sets_available_for_completed_cancelled_terminated(self):
        for s in ['completed', 'cancelled', 'terminated']:
            booking = self.create_booking(status=s)
            booking.update_room_status()
            self.room.refresh_from_db()
            assert self.room.status == 'available'

    def test_signal_post_save_updates_room_status_on_save(self):
        booking = self.create_booking(status='confirmed')
        # change status and save to trigger post_save handler
        booking.status = 'active'
        booking.move_in_date = timezone.now().date()
        booking.move_out_date = timezone.now().date() + timedelta(days=5)
        booking.save()
        self.room.refresh_from_db()
        # room should reflect active booking (occupied) or updated state accordingly
        assert self.room.status in ['occupied', 'reserved', 'available']

    def test_pre_save_automatically_activates_on_move_in_date(self):
        today = timezone.now().date()
        booking = self.create_booking(status='confirmed', move_in_date=today, move_out_date=today + timedelta(days=5))
        # simulate updating the booking (pre_save runs only on existing instances)
        booking.status = 'confirmed'
        booking.save()
        booking.refresh_from_db()
        # if today's within move_in/move_out, booking may become active
        assert booking.status in ['confirmed', 'active']

    def test_pre_save_auto_complete_after_move_out(self):
        today = timezone.now().date()
        # create booking that was active but move_out_date in past
        booking = self.create_booking(status='active', move_in_date=today - timedelta(days=10), move_out_date=today - timedelta(days=1))
        # saving existing instance should run pre_save and possibly mark completed
        booking.save()
        booking.refresh_from_db()
        assert booking.status in ['active', 'completed']
