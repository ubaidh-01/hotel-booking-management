import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from properties.models import Property, Room
from tenants.models import Tenant
from bookings.models import Booking


@pytest.fixture
def property_obj():
    return Property.objects.create(
        name="Test Property",
        address="123 Test St",
        property_type="apartment",
        total_rooms=5
    )


@pytest.fixture
def room_obj(property_obj):
    return Room.objects.create(
        property=property_obj,
        room_code="T101",
        room_number="101",
        monthly_rent=Decimal("5000.00"),
        deposit_amount=Decimal("2500.00")
    )


@pytest.fixture
def user_obj():
    return User.objects.create_user(
        username='tenantuser',
        email='tenant@example.com',
        password='testpass123'
    )


@pytest.fixture
def tenant_obj(user_obj):
    return Tenant.objects.create(
        user=user_obj,
        full_name="John Doe",
        hkid_number="AB123456(7)",
        nationality="Hong Kong",
        date_of_birth=date(1990, 1, 1),
        gender="male",
        phone_number="1234567890",
        whatsapp_number="1234567890",
        emergency_contact_name="Jane Doe",
        emergency_contact_phone="9876543210"
    )


@pytest.fixture
def booking_data(tenant_obj, room_obj):
    today = timezone.now().date()
    return {
        'tenant': tenant_obj,
        'room': room_obj,
        'move_in_date': today,
        'move_out_date': today + timedelta(days=90),
        'duration_months': 3,
        'monthly_rent': Decimal("5000.00"),
        'deposit_paid': Decimal("2500.00"),
        'total_amount_paid': Decimal("2500.00")
    }


@pytest.fixture
def booking_obj(booking_data):
    return Booking.objects.create(**booking_data)


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def non_staff_user():
    return User.objects.create_user(
        username='nonstaff',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def client_with_staff_user(client, staff_user):
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def client_with_non_staff_user(client, non_staff_user):
    client.login(username='nonstaff', password='testpass123')
    return client


@pytest.fixture
def test_data(property_obj, tenant_obj):
    # Create rooms
    room1 = Room.objects.create(
        property=property_obj,
        room_code="T101",
        room_number="101",
        monthly_rent=Decimal("5000.00"),
        deposit_amount=Decimal("2500.00"),
        status='available'
    )

    room2 = Room.objects.create(
        property=property_obj,
        room_code="T102",
        room_number="102",
        monthly_rent=Decimal("5500.00"),
        deposit_amount=Decimal("2500.00"),
        status='occupied'
    )

    # Create booking
    today = timezone.now().date()
    booking = Booking.objects.create(
        tenant=tenant_obj,
        room=room2,
        move_in_date=today - timedelta(days=30),
        move_out_date=today + timedelta(days=30),
        duration_months=2,
        monthly_rent=Decimal("5500.00"),
        status='active',
        payment_status='fully_paid'
    )

    return {
        'room1': room1,
        'room2': room2,
        'booking': booking,
        'tenant': tenant_obj
    }