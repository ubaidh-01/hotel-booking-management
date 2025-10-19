import os
import django
from django.utils import timezone
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wing_kon_property.settings')
django.setup()

from properties.models import Property, Room
from tenants.models import Tenant
from django.contrib.auth.models import User


def create_sample_data():
    print("Creating sample data...")

    # 1. Create Properties
    property1, created = Property.objects.get_or_create(
        name="Wing Kong Tower",
        property_type="apartment",
        total_rooms=20,
        address="123 Wing Kong Road, Central, Hong Kong"
    )

    property2, created = Property.objects.get_or_create(
        name="Kowloon Heights",
        property_type="building",
        total_rooms=90,
        address="456 Kowloon Bay, Kowloon, Hong Kong"
    )

    # 2. Create Rooms with unique codes
    room_codes = ['c5a', 'c5b', 'c5c', 'c5d', 'c6a', 'c6b', 'c6c', 'k1a', 'k1b', 'k2a']

    for i, code in enumerate(room_codes):
        property_obj = property1 if i < 6 else property2
        Room.objects.get_or_create(
            property=property_obj,
            room_code=code,
            room_number=f"Room {code.upper()}",
            description=f"Comfortable room {code} with basic amenities",
            monthly_rent=4500.00 + (i * 500),
            deposit_amount=2500.00,
            status='available' if i % 3 != 0 else 'occupied',
            size_sqft=180 + (i * 10),
            has_private_bathroom=(i % 2 == 0),
            has_balcony=(i % 3 == 0)
        )

    # 3. Create Sample Tenant
    user, created = User.objects.get_or_create(
        username='john_doe',
        defaults={'email': 'john@example.com', 'first_name': 'John', 'last_name': 'Doe'}
    )

    tenant, created = Tenant.objects.get_or_create(
        user=user,
        full_name="John Doe",
        hkid_number="A123456(7)",
        nationality="American",
        date_of_birth=datetime(1990, 5, 15).date(),
        gender="male",
        phone_number="+852 1234 5678",
        whatsapp_number="+852 1234 5678"
    )

    print("✅ Sample data created successfully!")
    print(f"   - Properties: {Property.objects.count()}")
    print(f"   - Rooms: {Room.objects.count()}")
    print(f"   - Tenants: {Tenant.objects.count()}")


if __name__ == "__main__":
    create_sample_data()