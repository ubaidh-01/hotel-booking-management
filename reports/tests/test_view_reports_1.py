import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from tenants.models import Tenant
from properties.models import Property, Room
from bookings.models import Booking
from payments.models import Payment


@pytest.mark.django_db
class TestReportsViews:

    def setup_method(self):
        # Staff user
        self.staff = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='pass',
            is_staff=True
        )

        # Tenant user
        user = User.objects.create_user(
            username='tenant_user',
            email='tenant@example.com',
            password='pass'
        )
        self.tenant = Tenant.objects.create(
            user=user,
            full_name="Tenant One",
            nationality="Country",
            date_of_birth="1990-01-01",
            gender="male",
            phone_number="999"
        )

        # Property & Room
        self.property = Property.objects.create(
            name="P1",
            address="Somewhere",
            property_type="apartment",
            total_rooms=2
        )
        self.room = Room.objects.create(
            property=self.property,
            room_code="A1",
            room_number="1",
            monthly_rent=5000
        )

        # Booking
        today = timezone.now().date()
        self.booking = Booking.objects.create(
            tenant=self.tenant,
            room=self.room,
            move_in_date=today - timedelta(days=1),
            move_out_date=today + timedelta(days=30),
            duration_months=1,
            monthly_rent=5000,
            status='active'
        )

    def login_client(self, client):
        """Helper to login staff user"""
        assert client.login(username='staff', password='pass')

    def test_dashboard_context(self, client):
        self.login_client(client)
        url = reverse('reports:dashboard')
        res = client.get(url)
        assert res.status_code == 200
        assert 'empty_rooms' in res.context
        assert 'active_bookings' in res.context
        assert 'total_tenants' in res.context

    def test_empty_rooms_report_and_csv_export(self, client):
        self.room.status = 'available'
        self.room.save()

        self.login_client(client)
        url = reverse('reports:empty_rooms')
        res = client.get(url)
        assert res.status_code == 200
        assert 'empty_rooms' in res.context

        csv_res = client.get(url + '?export=1')
        assert csv_res.status_code == 200
        assert csv_res['Content-Type'] == 'text/csv'

    def test_rent_owed_report_and_csv_export(self, client):
        due = timezone.now().date() - timedelta(days=3)
        Payment.objects.create(
            booking=self.booking,
            amount=5000,
            payment_type='rent',
            status='pending',
            due_date=due,
            payment_date=due  # ✅ added to fix IntegrityError
        )

        self.login_client(client)
        url = reverse('reports:rent_owed')
        res = client.get(url)
        assert res.status_code == 200
        assert 'total_late_fees' in res.context

        csv_res = client.get(url + '?export=1')
        assert csv_res.status_code == 200
        assert csv_res['Content-Type'] == 'text/csv'

    def test_move_out_report_labels_and_counts(self, client):
        self.booking.move_out_date = timezone.now().date() + timedelta(days=5)
        self.booking.save()

        self.login_client(client)
        url = reverse('reports:move_out')
        res = client.get(url)
        assert res.status_code == 200
        upcoming = res.context['upcoming_move_outs']
        # Ensure bookings have computed status
        found_label = any(hasattr(b, 'move_out_status') for b in upcoming)
        assert found_label

    def test_monthly_sales_report_summary(self, client):
        Payment.objects.create(
            booking=self.booking,
            amount=3000,
            payment_type='rent',
            status='completed',
            payment_date=timezone.now().date()
        )

        self.login_client(client)
        url = reverse('reports:monthly_sales')
        res = client.get(url)
        assert res.status_code == 200
        assert 'payment_summary' in res.context
        assert 'total_income' in res.context

    def test_utilities_report_aggregates(self, client):
        Payment.objects.create(
            booking=self.booking,
            amount=800,
            payment_type='utility',
            status='pending',
            due_date=timezone.now().date() - timedelta(days=2),
            payment_date=timezone.now().date() - timedelta(days=2)  # ✅ added
        )

        self.login_client(client)
        url = reverse('reports:utilities')
        res = client.get(url)
        assert res.status_code == 200
        assert 'unpaid_utilities' in res.context
        assert 'average_bill' in res.context
