import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from bookings.models import Booking


@pytest.mark.django_db
class TestRoomModel:
    def test_room_creation(self, room_obj, property_obj):
        """Test that a room is created correctly"""
        assert room_obj.property == property_obj
        assert room_obj.room_code == "T101"
        assert room_obj.room_number == "101"
        assert room_obj.monthly_rent == Decimal("5000.00")
        assert room_obj.deposit_amount == Decimal("2500.00")
        assert room_obj.status == 'available'

    def test_get_current_booking_method(self, room_obj, tenant_obj):
        """Test the get_current_booking method"""
        today = timezone.now().date()

        # Test with no booking
        assert room_obj.get_current_booking() is None

        # Test with active booking
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today - timedelta(days=1),
            move_out_date=today + timedelta(days=30),
            duration_months=1,
            monthly_rent=Decimal("5000.00"),
            status='active'
        )

        assert room_obj.get_current_booking() == booking

        # Test with non-active booking
        booking.status = 'pending'
        booking.save()

        assert room_obj.get_current_booking() is None

        # Test with booking outside date range
        booking.status = 'active'
        booking.move_in_date = today + timedelta(days=1)
        booking.move_out_date = today + timedelta(days=30)
        booking.save()

        assert room_obj.get_current_booking() is None

    def test_update_status_from_bookings_method(self, room_obj, tenant_obj):
        """Test the update_status_from_bookings method"""
        today = timezone.now().date()

        # Test with no bookings
        room_obj.update_status_from_bookings()
        room_obj.refresh_from_db()
        assert room_obj.status == 'available'

        # Test with active booking
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today - timedelta(days=1),
            move_out_date=today + timedelta(days=30),
            duration_months=1,
            monthly_rent=Decimal("5000.00"),
            status='active'
        )

        room_obj.update_status_from_bookings()
        room_obj.refresh_from_db()
        assert room_obj.status == 'occupied'

        # Test with confirmed (upcoming) booking
        booking.status = 'confirmed'
        booking.move_in_date = today + timedelta(days=1)
        booking.move_out_date = today + timedelta(days=30)
        booking.save()

        room_obj.update_status_from_bookings()
        room_obj.refresh_from_db()
        assert room_obj.status == 'reserved'

        # Test with completed booking
        booking.status = 'completed'
        booking.save()

        room_obj.update_status_from_bookings()
        room_obj.refresh_from_db()
        assert room_obj.status == 'available'

        # Test with maintenance status (should not change)
        room_obj.status = 'maintenance'
        room_obj.save()

        booking.status = 'active'
        booking.move_in_date = today - timedelta(days=1)
        booking.move_out_date = today + timedelta(days=30)
        booking.save()

        room_obj.update_status_from_bookings()
        room_obj.refresh_from_db()
        assert room_obj.status == 'maintenance'  # Should remain unchanged

        # Test with cleaning status (should not change)
        room_obj.status = 'cleaning'
        room_obj.save()

        room_obj.update_status_from_bookings()
        room_obj.refresh_from_db()
        assert room_obj.status == 'cleaning'  # Should remain unchanged

        # Test with temporary status (should not change)
        room_obj.status = 'temporary'
        room_obj.save()

        room_obj.update_status_from_bookings()
        room_obj.refresh_from_db()
        assert room_obj.status == 'temporary'  # Should remain unchanged
