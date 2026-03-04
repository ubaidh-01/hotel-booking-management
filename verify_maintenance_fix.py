import os
import django
import sys

# Setup Django environment
sys.path.append('/home/ubaid/Pycharm-projects/wing_kon_property')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wing_kon_property.settings')
django.setup()

from django.contrib.auth.models import User
from tenants.models import Tenant
from bookings.models import Booking
from maintenance.models import MaintenanceTicket
from properties.models import Property, Room
from django.test import RequestFactory
from website.views import tenant_maintenance
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone

def verify_maintenance_fix():
    print("Starting verification of maintenance fix...")
    
    # 1. Setup mock data
    username = "test_tenant_fix"
    email = "test@example.com"
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, email=email, password="password")
        tenant = Tenant.objects.create(user=user, full_name="Test Tenant Fix")
    else:
        user = User.objects.get(username=username)
        tenant = user.tenant

    # Ensure a property and room exists
    prop, _ = Property.objects.get_or_create(name="Test Prop", address="123 Test St", defaults={'property_type': 'residential'})
    room, _ = Room.objects.get_or_create(property=prop, room_code="R101", defaults={'room_type': 'standard', 'monthly_rent': 5000, 'status': 'available'})

    # 2. Create a CONFIRMED booking (not active)
    Booking.objects.filter(tenant=tenant).delete()
    booking = Booking.objects.create(
        tenant=tenant,
        room=room,
        move_in_date=timezone.now().date() + timezone.timedelta(days=7),
        move_out_date=timezone.now().date() + timezone.timedelta(days=37),
        duration_months=1,
        monthly_rent=5000,
        status='confirmed' # This is the critical part
    )
    print(f"Created confirmed booking #{booking.id}")

    # 3. Simulate POST request to tenant_maintenance
    factory = RequestFactory()
    request = factory.post('/tenant/maintenance/', {
        'title': 'Test Issue',
        'description': 'This is a test maintenance issue for a confirmed booking.',
        'priority': 'medium'
    })
    request.user = user
    
    # Add messages middleware support
    setattr(request, '_messages', FallbackStorage(request))

    # 4. Call the view
    print("Calling tenant_maintenance view...")
    response = tenant_maintenance(request)
    
    # 5. Verify results
    ticket_exists = MaintenanceTicket.objects.filter(tenant=tenant, title='Test Issue').exists()
    if ticket_exists:
        print("✅ SUCCESS: Maintenance ticket created for confirmed booking!")
    else:
        print("❌ FAILURE: Maintenance ticket NOT created.")
        # Check messages to see why
        messages = [m.message for m in request._messages]
        print(f"Messages: {messages}")

if __name__ == "__main__":
    verify_maintenance_fix()
