import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from bookings.models import Booking



@pytest.mark.django_db
class TestEdgeCases:
    def test_same_day_move_in_move_out(self, property_obj, room_obj, tenant_obj):
        """Test edge case where move-in and move-out are the same day"""
        today = timezone.now().date()

        # Create a booking with same day move-in and move-out
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today,
            move_out_date=today,
            duration_months=0,
            monthly_rent=Decimal("5000.00"),
            status='confirmed'
        )

        # Check that the booking doesn't auto-activate
        booking.refresh_from_db()
        assert booking.status == 'confirmed'

        # Check room status remains reserved
        room_obj.refresh_from_db()
        assert room_obj.status == 'reserved'

    def test_booking_with_past_dates(self, property_obj, room_obj, tenant_obj):
        """Test edge case where booking is created with past dates"""
        today = timezone.now().date()

        # Create a booking with past dates
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today - timedelta(days=30),
            move_out_date=today - timedelta(days=15),
            duration_months=1,
            monthly_rent=Decimal("5000.00"),
            status='confirmed'
        )

        # Check that the booking doesn't auto-activate
        booking.refresh_from_db()
        assert booking.status == 'confirmed'

        # Check room status remains reserved
        room_obj.refresh_from_db()
        assert room_obj.status == 'reserved'

    def test_room_status_with_maintenance(self, property_obj, room_obj, tenant_obj):
        """Test edge case where room is under maintenance"""
        today = timezone.now().date()

        # Set room status to maintenance
        room_obj.status = 'maintenance'
        room_obj.save()

        # Create a booking
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today,
            move_out_date=today + timedelta(days=30),
            duration_months=1,
            monthly_rent=Decimal("5000.00"),
            status='confirmed'
        )

        # Check room status remains maintenance
        room_obj.refresh_from_db()
        assert room_obj.status == 'maintenance'

    def test_zero_duration_booking(self, property_obj, room_obj, tenant_obj):
        """Test edge case where booking has zero duration"""
        today = timezone.now().date()

        # Create a booking with zero duration
        booking = Booking.objects.create(
            tenant=tenant_obj,
            room=room_obj,
            move_in_date=today,
            move_out_date=today,
            duration_months=0,
            monthly_rent=Decimal("5000.00"),
            status='confirmed'
        )

        # Check total rent amount is zero
        assert booking.total_rent_amount == Decimal("0.00")

        # Check balance due is negative of amount paid
        assert booking.balance_due == -booking.total_amount_paid