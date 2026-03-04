from django.urls import reverse
from django.contrib.auth.models import User

from bookings.models import Booking
from payments.models import Payment
from contracts.models import Contract
import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from properties.models import Room


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

    # Create payments
    overdue_payment = Payment.objects.create(
        booking=booking,
        amount=Decimal("5500.00"),
        payment_type='rent',
        status='pending',
        due_date=today - timedelta(days=5)
    )

    completed_payment = Payment.objects.create(
        booking=booking,
        amount=Decimal("5500.00"),
        payment_type='rent',
        status='completed',
        payment_date=today,
        due_date=today - timedelta(days=1)
    )

    utility_payment = Payment.objects.create(
        booking=booking,
        amount=Decimal("500.00"),
        payment_type='utility',
        status='pending',
        due_date=today + timedelta(days=5)
    )

    # Create contract
    contract = Contract.objects.create(
        booking=booking,
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=30),
        status='signed'
    )

    return {
        'room1': room1,
        'room2': room2,
        'booking': booking,
        'overdue_payment': overdue_payment,
        'completed_payment': completed_payment,
        'utility_payment': utility_payment,
        'contract': contract
    }


@pytest.mark.django_db
class TestReportsViews:
    def test_dashboard_view(self, client_with_staff_user, test_data):
        """Test the dashboard view"""
        url = reverse('dashboard')
        response = client_with_staff_user.get(url)

        assert response.status_code == 200
        assert 'reports/dashboard.html' in [t.name for t in response.templates]

        # Check context data
        assert 'empty_rooms' in response.context
        assert 'rent_owed_payments' in response.context
        assert 'upcoming_move_outs' in response.context
        assert 'ending_contracts' in response.context

        # Check specific data
        assert response.context['empty_rooms_count'] == 1
        assert response.context['rent_owed_count'] == 1
        assert response.context['total_rooms'] == 2
        assert response.context['active_bookings'] == 1
        assert response.context['total_tenants'] == 1

    def test_empty_rooms_report_view(self, client_with_staff_user, test_data):
        """Test the empty rooms report view"""
        url = reverse('empty_rooms_report')
        response = client_with_staff_user.get(url)

        assert response.status_code == 200
        assert 'reports/empty_rooms.html' in [t.name for t in response.templates]

        # Check context data
        assert 'empty_rooms' in response.context
        assert 'total_count' in response.context
        assert 'total_rent_value' in response.context

        # Check specific data
        assert response.context['total_count'] == 1
        assert response.context['total_rent_value'] == Decimal("5000.00")

        # Test CSV export
        response = client_with_staff_user.get(url, {'export': 'csv'})
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert response['Content-Disposition'] == 'attachment; filename="empty_rooms.csv"'

    def test_rent_owed_report_view(self, client_with_staff_user, test_data):
        """Test the rent owed report view"""
        url = reverse('rent_owed_report')
        response = client_with_staff_user.get(url)

        assert response.status_code == 200
        assert 'reports/rent_owed.html' in [t.name for t in response.templates]

        # Check context data
        assert 'overdue_rent' in response.context
        assert 'total_rent_owed' in response.context
        assert 'total_late_fees' in response.context
        assert 'total_owed' in response.context

        # Check specific data
        assert len(response.context['overdue_rent']) == 1
        assert response.context['total_rent_owed'] == Decimal("5500.00")
        assert response.context['total_late_fees'] == Decimal("500.00")  # 5 days * 100
        assert response.context['total_owed'] == Decimal("6000.00")

        # Test CSV export
        response = client_with_staff_user.get(url, {'export': 'csv'})
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert response['Content-Disposition'] == 'attachment; filename="rent_owed.csv"'

    def test_move_out_report_view(self, client_with_staff_user, test_data):
        """Test the move out report view"""
        url = reverse('move_out_report')
        response = client_with_staff_user.get(url)

        assert response.status_code == 200
        assert 'reports/move_out.html' in [t.name for t in response.templates]

        # Check context data
        assert 'upcoming_move_outs' in response.context
        assert 'total_refunds' in response.context
        assert 'total_deposits' in response.context
        assert 'this_week_count' in response.context
        assert 'next_week_count' in response.context

        # Check specific data
        assert len(response.context['upcoming_move_outs']) == 1
        assert response.context['total_refunds'] == Decimal("2500.00")
        assert response.context['total_deposits'] == Decimal("2500.00")
        assert response.context['this_week_count'] == 0
        assert response.context['next_week_count'] == 1

    def test_monthly_sales_report_view(self, client_with_staff_user, test_data):
        """Test the monthly sales report view"""
        url = reverse('monthly_sales_report')
        response = client_with_staff_user.get(url)

        assert response.status_code == 200
        assert 'reports/monthly_sales.html' in [t.name for t in response.templates]

        # Check context data
        assert 'payment_summary' in response.context
        assert 'total_income' in response.context
        assert 'selected_month' in response.context
        assert 'total_transactions' in response.context

        # Check specific data
        assert response.context['total_income'] == Decimal("5500.00")
        assert response.context['total_transactions'] == 1

        # Test with a specific month
        current_month = timezone.now().strftime('%Y-%m')
        response = client_with_staff_user.get(url, {'month': current_month})
        assert response.status_code == 200
        assert response.context['selected_month'] == current_month

    def test_utilities_report_view(self, client_with_staff_user, test_data):
        """Test the utilities report view"""
        url = reverse('utilities_report')
        response = client_with_staff_user.get(url)

        assert response.status_code == 200
        assert 'reports/utilities.html' in [t.name for t in response.templates]

        # Check context data
        assert 'unpaid_utilities' in response.context
        assert 'total_unpaid' in response.context
        assert 'average_bill' in response.context
        assert 'unpaid_count' in response.context

        # Check specific data
        assert len(response.context['unpaid_utilities']) == 1
        assert response.context['total_unpaid'] == Decimal("500.00")
        assert response.context['average_bill'] == Decimal("500.00")
        assert response.context['unpaid_count'] == 1

    def test_staff_required_decorator(self, client_with_non_staff_user, client_with_staff_user):
        """Test that views require staff permissions"""
        # Try to access dashboard with non-staff user
        url = reverse('dashboard')
        response = client_with_non_staff_user.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/admin/login/' in response.url

        # Try to access dashboard with staff user
        response = client_with_staff_user.get(url)

        # Should succeed
        assert response.status_code == 200
