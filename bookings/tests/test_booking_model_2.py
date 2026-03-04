import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


@pytest.mark.django_db
class TestBookingModel:
    def test_booking_creation(self, booking_obj, tenant_obj, room_obj):
        """Test that a booking is created correctly"""
        assert booking_obj.tenant == tenant_obj
        assert booking_obj.room == room_obj
        assert booking_obj.status == 'pending'
        assert booking_obj.payment_status == 'pending'
        assert booking_obj.monthly_rent == Decimal("5000.00")
        assert booking_obj.deposit_paid == Decimal("2500.00")
        assert booking_obj.total_amount_paid == Decimal("2500.00")
        assert str(booking_obj) == f"Booking #{booking_obj.id} - {tenant_obj.full_name} - {room_obj.room_code}"

    def test_booking_status_transitions(self, booking_obj):
        """Test booking status transitions"""
        # Test pending to confirmed
        booking_obj.status = 'confirmed'
        booking_obj.payment_status = 'deposit_paid'
        booking_obj.save()

        # Refresh from database
        booking_obj.refresh_from_db()
        assert booking_obj.status == 'confirmed'
        assert booking_obj.payment_status == 'deposit_paid'

        # Check room status is updated to reserved
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'reserved'

        # Test confirmed to active
        booking_obj.move_in_date = timezone.now().date() - timedelta(days=1)
        booking_obj.save()

        # Refresh from database
        booking_obj.refresh_from_db()
        assert booking_obj.status == 'active'

        # Check room status is updated to occupied
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'occupied'

        # Test active to completed
        booking_obj.move_out_date = timezone.now().date() - timedelta(days=1)
        booking_obj.save()

        # Refresh from database
        booking_obj.refresh_from_db()
        assert booking_obj.status == 'completed'

        # Check room status is updated to available
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'available'

    def test_total_rent_amount_property(self, booking_obj):
        """Test the total_rent_amount property calculation"""
        expected_total = booking_obj.monthly_rent * booking_obj.duration_months
        assert booking_obj.total_rent_amount == expected_total

    def test_balance_due_property(self, booking_obj):
        """Test the balance_due property calculation"""
        expected_balance = booking_obj.total_rent_amount - booking_obj.total_amount_paid
        assert booking_obj.balance_due == expected_balance

    def test_is_currently_active_property(self, booking_obj):
        """Test the is_currently_active property"""
        today = timezone.now().date()

        # Test with dates that should make it active
        booking_obj.status = 'active'
        booking_obj.move_in_date = today - timedelta(days=1)
        booking_obj.move_out_date = today + timedelta(days=1)
        booking_obj.save()
        assert booking_obj.is_currently_active is True

        # Test with dates that should make it inactive (before move-in)
        booking_obj.move_in_date = today + timedelta(days=1)
        booking_obj.move_out_date = today + timedelta(days=30)
        booking_obj.save()
        assert booking_obj.is_currently_active is False

        # Test with dates that should make it inactive (after move-out)
        booking_obj.move_in_date = today - timedelta(days=30)
        booking_obj.move_out_date = today - timedelta(days=1)
        booking_obj.save()
        assert booking_obj.is_currently_active is False

        # Test with non-active status
        booking_obj.status = 'pending'
        booking_obj.move_in_date = today - timedelta(days=1)
        booking_obj.move_out_date = today + timedelta(days=1)
        booking_obj.save()
        assert booking_obj.is_currently_active is False

    def test_update_room_status_method(self, booking_obj):
        """Test the update_room_status method"""
        # Test pending booking
        booking_obj.status = 'pending'
        booking_obj.save()
        booking_obj.update_room_status()
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'available'

        # Test confirmed booking
        booking_obj.status = 'confirmed'
        booking_obj.save()
        booking_obj.update_room_status()
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'reserved'

        # Test active booking
        booking_obj.status = 'active'
        booking_obj.move_in_date = timezone.now().date() - timedelta(days=1)
        booking_obj.move_out_date = timezone.now().date() + timedelta(days=1)
        booking_obj.save()
        booking_obj.update_room_status()
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'occupied'

        # Test completed booking
        booking_obj.status = 'completed'
        booking_obj.save()
        booking_obj.update_room_status()
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'available'

        # Test cancelled booking
        booking_obj.status = 'cancelled'
        booking_obj.save()
        booking_obj.update_room_status()
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'available'

        # Test terminated booking
        booking_obj.status = 'terminated'
        booking_obj.save()
        booking_obj.update_room_status()
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'available'

    def test_signal_update_room_status_on_booking_change(self, booking_obj):
        """Test the signal that updates room status when booking changes"""
        # Change booking status and check if room status is updated automatically
        booking_obj.status = 'confirmed'
        booking_obj.save()

        # Check room status is updated to reserved
        booking_obj.room.refresh_from_db()
        assert booking_obj.room.status == 'reserved'

    def test_signal_handle_booking_status_change(self, booking_obj):
        """Test the signal that handles automatic status transitions"""
        today = timezone.now().date()

        # Test auto-activation on move-in date
        booking_obj.status = 'confirmed'
        booking_obj.move_in_date = today
        booking_obj.move_out_date = today + timedelta(days=90)
        booking_obj.save()

        # Refresh from database
        booking_obj.refresh_from_db()
        assert booking_obj.status == 'active'
        assert booking_obj.actual_move_in_date == today

        # Test auto-completion after move-out date
        booking_obj.status = 'active'
        booking_obj.move_in_date = today - timedelta(days=90)
        booking_obj.move_out_date = today - timedelta(days=1)
        booking_obj.save()

        # Refresh from database
        booking_obj.refresh_from_db()
        assert booking_obj.status == 'completed'
        assert booking_obj.actual_move_out_date == today