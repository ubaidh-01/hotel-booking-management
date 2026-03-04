import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from bookings.models import Booking


@pytest.mark.django_db
class TestBookingRoomStatusIntegration:
    def test_booking_room_status_lifecycle(self, property_obj, room_obj, tenant_obj):
        """Test the complete lifecycle of booking and room status"""
        today = timezone.now().date()

        # Create a booking
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today + timedelta(days=7),
            move_out_date=today + timedelta(days=97),
            duration_months=3,
            monthly_rent=Decimal("5000.00"),
            status='pending'
        )

        # Initial status check
        assert booking.status == 'pending'
        assert booking.room.status == 'available'

        # Confirm booking
        booking.status = 'confirmed'
        booking.payment_status = 'deposit_paid'
        booking.deposit_paid = Decimal("2500.00")
        booking.total_amount_paid = Decimal("2500.00")
        booking.save()

        # Check status after confirmation
        booking.refresh_from_db()
        room_obj.refresh_from_db()
        assert booking.status == 'confirmed'
        assert room_obj.status == 'reserved'

        # Simulate move-in date passing
        booking.move_in_date = today - timedelta(days=1)
        booking.save()

        # Check status after move-in
        booking.refresh_from_db()
        room_obj.refresh_from_db()
        assert booking.status == 'active'
        assert room_obj.status == 'occupied'
        assert booking.actual_move_in_date == today

        # Simulate move-out date passing
        booking.move_out_date = today - timedelta(days=1)
        booking.save()

        # Check status after move-out
        booking.refresh_from_db()
        room_obj.refresh_from_db()
        assert booking.status == 'completed'
        assert room_obj.status == 'available'
        assert booking.actual_move_out_date == today

    def test_multiple_bookings_same_room(self, property_obj, room_obj, tenant_obj):
        """Test handling of multiple bookings for the same room"""
        today = timezone.now().date()

        # Create first booking
        booking1 = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today - timedelta(days=30),
            move_out_date=today - timedelta(days=1),
            duration_months=1,
            monthly_rent=Decimal("5000.00"),
            status='completed'
        )

        # Create second booking
        booking2 = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today,
            move_out_date=today + timedelta(days=30),
            duration_months=1,
            monthly_rent=Decimal("5000.00"),
            status='active'
        )

        # Create third booking (future)
        booking3 = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today + timedelta(days=31),
            move_out_date=today + timedelta(days=60),
            duration_months=1,
            monthly_rent=Decimal("5000.00"),
            status='confirmed'
        )

        # Check room status is correctly set to active (current booking)
        room_obj.refresh_from_db()
        assert room_obj.status == 'occupied'

        # Check get_current_booking returns the active booking
        assert room_obj.get_current_booking() == booking2

        # Complete the active booking
        booking2.status = 'completed'
        booking2.save()

        # Check room status is updated to reserved (for future booking)
        room_obj.refresh_from_db()
        assert room_obj.status == 'reserved'

        # Cancel the future booking
        booking3.status = 'cancelled'
        booking3.save()

        # Check room status is updated to available
        room_obj.refresh_from_db()
        assert room_obj.status == 'available'

    def test_booking_cancellation(self, property_obj, room_obj, tenant_obj):
        """Test booking cancellation and its effect on room status"""
        today = timezone.now().date()

        # Create a confirmed booking
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today + timedelta(days=7),
            move_out_date=today + timedelta(days=97),
            duration_months=3,
            monthly_rent=Decimal("5000.00"),
            status='confirmed'
        )

        # Check room status is reserved
        room_obj.refresh_from_db()
        assert room_obj.status == 'reserved'

        # Cancel the booking
        booking.status = 'cancelled'
        booking.save()

        # Check room status is updated to available
        room_obj.refresh_from_db()
        assert room_obj.status == 'available'

    def test_booking_termination(self, property_obj, room_obj, tenant_obj):
        """Test booking termination and its effect on room status"""
        today = timezone.now().date()

        # Create an active booking
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today - timedelta(days=30),
            move_out_date=today + timedelta(days=60),
            duration_months=3,
            monthly_rent=Decimal("5000.00"),
            status='active'
        )

        # Check room status is occupied
        room_obj.refresh_from_db()
        assert room_obj.status == 'occupied'

        # Terminate the booking
        booking.status = 'terminated'
        booking.save()

        # Check room status is updated to available
        room_obj.refresh_from_db()
        assert room_obj.status == 'available'
