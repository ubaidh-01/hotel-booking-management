# test_room_booking_sync.py
import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wing_kon_property.settings')
django.setup()

from properties.models import Room
from bookings.models import Booking
from tenants.models import Tenant
from django.contrib.auth.models import User


def test_room_booking_sync():
    print("Testing Room-Booking Synchronization...")

    # Get a room and tenant for testing
    room = Room.objects.filter(status='available').first()
    tenant = Tenant.objects.first()

    if not room or not tenant:
        print("Need at least one available room and tenant for testing")
        return

    print(f"Testing with Room: {room.room_code} (Current status: {room.status})")
    print(f"Tenant: {tenant.full_name}")

    # Test 1: Create pending booking
    print("\n1. Creating PENDING booking...")
    booking = Booking.objects.create(
        tenant=tenant,
        room=room,
        move_in_date=date.today() + timedelta(days=7),
        move_out_date=date.today() + timedelta(days=37),
        duration_months=1,
        monthly_rent=room.monthly_rent,
        status='pending'
    )
    room.refresh_from_db()
    print(f"   Room status after pending booking: {room.status}")

    # Test 2: Confirm booking
    print("\n2. Confirming booking...")
    booking.status = 'confirmed'
    booking.payment_status = 'deposit_paid'
    booking.deposit_paid = room.deposit_amount
    booking.save()
    room.refresh_from_db()
    print(f"   Room status after confirmation: {room.status}")

    # Test 3: Activate booking (simulate move-in)
    print("\n3. Activating booking...")
    booking.status = 'active'
    booking.actual_move_in_date = date.today()
    booking.save()
    room.refresh_from_db()
    print(f"   Room status after activation: {room.status}")

    # Test 4: Complete booking (simulate move-out)
    print("\n4. Completing booking...")
    booking.status = 'completed'
    booking.actual_move_out_date = date.today()
    booking.save()
    room.refresh_from_db()
    print(f"   Room status after completion: {room.status}")

    # Clean up
    booking.delete()
    print("\n✅ Test completed successfully!")


if __name__ == "__main__":
    test_room_booking_sync()