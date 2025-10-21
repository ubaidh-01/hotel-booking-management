import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wing_kon_property.settings')
django.setup()

from properties.models import Property, Room
from tenants.models import Tenant
from bookings.models import Booking
from payments.models import Payment
from contracts.models import Contract
from django.contrib.auth.models import User
from notifications.tasks import (
    send_rent_reminders,
    send_contract_reminders,
    send_birthday_wishes,
    process_late_fees,
    sync_room_status,
    send_test_email
)


def create_test_data():
    """Create dummy data for testing all Celery tasks"""
    print("🧪 Creating test data for Celery tasks...")

    # Create test property and room if they don't exist
    property, _ = Property.objects.get_or_create(
        name="Test Property",
        defaults={
            'property_type': 'apartment',
            'total_rooms': 5,
            'address': '123 Test Street, Hong Kong'
        }
    )

    room, _ = Room.objects.get_or_create(
        property=property,
        room_code='TEST01',
        defaults={
            'room_number': 'Test Room 1',
            'description': 'Test room for Celery tasks',
            'monthly_rent': 4500.00,
            'deposit_amount': 2500.00,
            'status': 'available'
        }
    )

    # Create test user and tenant
    user, _ = User.objects.get_or_create(
        username='test_tenant',
        defaults={
            'email': 'test@wing-kong.com',
            'first_name': 'Test',
            'last_name': 'Tenant'
        }
    )

    tenant, _ = Tenant.objects.get_or_create(
        user=user,
        defaults={
            'full_name': 'Test Tenant',
            'hkid_number': 'T123456(7)',
            'nationality': 'Test Nationality',
            'date_of_birth': date(1990, 1, 15),  # Set birthday to today's date for testing
            'gender': 'male',
            'phone_number': '+852 1234 5678'
        }
    )

    # Update birthday to today for birthday test
    today = date.today()
    tenant.date_of_birth = date(today.year, today.month, today.day)
    tenant.save()

    # Create test booking
    booking, _ = Booking.objects.get_or_create(
        tenant=tenant,
        room=room,
        defaults={
            'move_in_date': date.today() - timedelta(days=30),
            'move_out_date': date.today() + timedelta(days=30),
            'duration_months': 2,
            'monthly_rent': 4500.00,
            'status': 'active'
        }
    )

    # Create test payments for different scenarios
    payments_data = [
        # Payment due in 3 days
        {
            'due_date': date.today() + timedelta(days=3),
            'status': 'pending',
            'amount': 4500.00
        },
        # Payment overdue by 1 day
        {
            'due_date': date.today() - timedelta(days=1),
            'status': 'pending',
            'amount': 4500.00
        },
        # Payment overdue by 8 days (for late fee testing)
        {
            'due_date': date.today() - timedelta(days=8),
            'status': 'pending',
            'amount': 4500.00
        },
        # Payment overdue by 15 days (for court notice testing)
        {
            'due_date': date.today() - timedelta(days=15),
            'status': 'pending',
            'amount': 4500.00
        }
    ]

    for i, payment_data in enumerate(payments_data):
        Payment.objects.get_or_create(
            booking=booking,
            payment_type='rent',
            due_date=payment_data['due_date'],
            defaults={
                'amount': payment_data['amount'],
                'status': payment_data['status'],
                'payment_method': 'bank_transfer',
                'payment_date': payment_data['due_date'] - timedelta(days=1)
            }
        )

    # Create test contract ending in 21 days
    contract, _ = Contract.objects.get_or_create(
        booking=booking,
        defaults={
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() + timedelta(days=21),  # 3 weeks from now
            'monthly_rent': 4500.00,
            'security_deposit': 2500.00,
            'stamp_duty': 100.00,
            'status': 'signed'
        }
    )

    print("✅ Test data created successfully!")
    return {
        'property': property,
        'room': room,
        'tenant': tenant,
        'booking': booking,
        'contract': contract
    }


def test_all_celery_tasks():
    """Test all Celery tasks at once"""
    print("\n🚀 Testing All Celery Tasks...")

    # Create test data first
    test_data = create_test_data()

    # Test 1: Send Test Email
    print("\n1. Testing: send_test_email")
    # result1 = send_test_email()
    # print(f"   ✅ Task queued: {result1.id}")

    # Test 2: Rent Reminders
    print("\n2. Testing: send_rent_reminders")
    result2 = send_rent_reminders.delay()
    print(f"   ✅ Task queued: {result2.id}")

    # Test 3: Contract Reminders
    print("\n3. Testing: send_contract_reminders")
    result3 = send_contract_reminders.delay()
    print(f"   ✅ Task queued: {result3.id}")

    # Test 4: Birthday Wishes
    print("\n4. Testing: send_birthday_wishes")
    result4 = send_birthday_wishes.delay()
    print(f"   ✅ Task queued: {result4.id}")

    # Test 5: Process Late Fees
    print("\n5. Testing: process_late_fees")
    result5 = process_late_fees.delay()
    print(f"   ✅ Task queued: {result5.id}")

    # Test 6: Sync Room Status
    print("\n6. Testing: sync_room_status")
    result6 = sync_room_status.delay()
    print(f"   ✅ Task queued: {result6.id}")

    print(f"\n🎉 All 6 Celery tasks queued successfully!")
    print(f"   Check your Celery worker terminal for task execution logs.")
    print(f"   Check email inbox for test messages.")
    print(f"   Check /admin/notifications/notificationlog/ for sent notifications.")

    return [result2, result3, result4, result5, result6]


def quick_test():
    """Quick test without creating data (use existing data)"""
    print("\n⚡ Quick Testing Celery Tasks...")

    tasks = [
        ('send_rent_reminders', send_rent_reminders),
        ('send_contract_reminders', send_contract_reminders),
        ('send_birthday_wishes', send_birthday_wishes),
        ('process_late_fees', process_late_fees),
        ('sync_room_status', sync_room_status),
    ]

    results = []
    for name, task in tasks:
        print(f"   Queuing: {name}")
        result = task.delay()
        results.append(result)
        print(f"   ✅ {name}: {result.id}")

    print(f"\n✅ All {len(tasks)} tasks queued!")
    return results


if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Full test with dummy data")
    print("2. Quick test (existing data)")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        test_all_celery_tasks()
    else:
        quick_test()