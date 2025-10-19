from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from properties.models import Room
from bookings.models import Booking
from payments.models import Payment
from tenants.models import Tenant
from contracts.models import Contract


def staff_required(view_func):
    """Decorator that checks if user is staff member"""
    decorated_view_func = login_required(user_passes_test(
        lambda u: u.is_staff,
        login_url='/admin/login/'
    )(view_func))
    return decorated_view_func


@staff_required
def dashboard(request):
    """CRM Dashboard - Main overview with all key metrics"""
    today = timezone.now().date()

    # Empty Rooms Report (Requirement #7)
    empty_rooms = Room.objects.filter(status='available').select_related('property')

    # Rent Owed Report (Requirement #9)
    rent_owed_payments = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date__lt=today
    ).select_related('booking__tenant', 'booking__room')

    # Calculate late fees (HK$100 per day)
    total_late_fees = 0
    for payment in rent_owed_payments:
        days_overdue = (today - payment.due_date).days
        payment.late_fee_amount = days_overdue * 100
        total_late_fees += payment.late_fee_amount

    # Move Out Report (Requirement #8)
    move_out_cutoff = today + timedelta(days=30)
    upcoming_move_outs = Booking.objects.filter(
        move_out_date__lte=move_out_cutoff,
        move_out_date__gte=today,
        status='active'
    ).select_related('tenant', 'room')

    # Contracts ending soon (for reminders)
    contract_cutoff = today + timedelta(days=21)  # 3 weeks
    ending_contracts = Contract.objects.filter(
        end_date__lte=contract_cutoff,
        end_date__gte=today,
        status='signed'
    ).select_related('booking__tenant', 'booking__room')

    context = {
        'title': 'CRM Dashboard - Wing Kong Property Management',
        'empty_rooms': empty_rooms,
        'empty_rooms_count': empty_rooms.count(),
        'rent_owed_payments': rent_owed_payments,
        'rent_owed_count': rent_owed_payments.count(),
        'total_rent_owed': sum(p.amount for p in rent_owed_payments),
        'total_late_fees': total_late_fees,
        'upcoming_move_outs': upcoming_move_outs,
        'ending_contracts': ending_contracts,
        'total_rooms': Room.objects.count(),
        'active_bookings': Booking.objects.filter(status='active').count(),
        'total_tenants': Tenant.objects.count(),
        'today': today,
    }
    return render(request, 'reports/dashboard.html', context)


@staff_required
def empty_rooms_report(request):
    """Requirement #7: Empty Rooms Report - can be printed"""
    empty_rooms = Room.objects.filter(status='available').select_related('property')

    # Export to CSV
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="empty_rooms.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ['Room Code', 'Property', 'Monthly Rent', 'Size (sqft)', 'Private Bathroom', 'Balcony', 'Status'])
        for room in empty_rooms:
            writer.writerow([
                room.room_code,
                room.property.name,
                f"HK${room.monthly_rent}",
                room.size_sqft or 'N/A',
                'Yes' if room.has_private_bathroom else 'No',
                'Yes' if room.has_balcony else 'No',
                room.get_status_display()
            ])
        return response

    context = {
        'title': 'Empty Rooms Report',
        'empty_rooms': empty_rooms,
        'total_count': empty_rooms.count(),
        'total_rent_value': sum(room.monthly_rent for room in empty_rooms),
        'today': timezone.now().date(),
    }
    return render(request, 'reports/empty_rooms.html', context)


@staff_required
def rent_owed_report(request):
    """Requirement #9: Rent Owed Report with Late Fees"""
    today = timezone.now().date()

    # Rent payments that are overdue
    overdue_rent = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date__lt=today
    ).select_related('booking__tenant', 'booking__room')

    # Calculate late fees (HK$100 per day - Requirement #9)
    total_rent = 0
    total_late_fees = 0
    for payment in overdue_rent:
        days_overdue = (today - payment.due_date).days
        payment.late_fee_days = days_overdue
        payment.late_fee_amount = days_overdue * 100  # HK$100 per day
        payment.total_owed = payment.amount + payment.late_fee_amount
        total_rent += payment.amount
        total_late_fees += payment.late_fee_amount

    # Export to CSV
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rent_owed.csv"'
        writer = csv.writer(response)
        writer.writerow(['Tenant', 'Room', 'Rent Amount', 'Due Date', 'Days Overdue', 'Late Fees', 'Total Owed'])
        for payment in overdue_rent:
            writer.writerow([
                payment.booking.tenant.full_name,
                payment.booking.room.room_code,
                f"HK${payment.amount}",
                payment.due_date,
                payment.late_fee_days,
                f"HK${payment.late_fee_amount}",
                f"HK${payment.total_owed}"
            ])
        return response

    context = {
        'title': 'Rent Owed Report',
        'overdue_rent': overdue_rent,
        'total_rent_owed': total_rent,
        'total_late_fees': total_late_fees,
        'total_owed': total_rent + total_late_fees,
        'today': today,
    }
    return render(request, 'reports/rent_owed.html', context)

@staff_required
def move_out_report(request):
    """Requirement #8: Move Out Report (Refund Report)"""
    today = timezone.now().date()

    # Define report window (next 30 days)
    move_out_date_start = today
    move_out_date_end = today + timedelta(days=30)

    # Fetch upcoming move-outs
    upcoming_move_outs = Booking.objects.filter(
        move_out_date__range=[move_out_date_start, move_out_date_end],
        status='active'
    ).select_related('tenant', 'room')

    total_refunds = 0
    total_deposits = 0

    # Compute refund and days remaining for each booking
    for booking in upcoming_move_outs:
        booking.days_until_move_out = (booking.move_out_date - today).days
        booking.refund_amount = booking.deposit_paid or 0  # Simple full refund for now
        total_refunds += booking.refund_amount
        total_deposits += booking.deposit_paid or 0

        # Determine move-out status label
        if booking.move_out_date == today:
            booking.move_out_status = "MOVING OUT TODAY"
        elif booking.days_until_move_out <= 7:
            booking.move_out_status = "THIS WEEK"
        elif booking.days_until_move_out <= 14:
            booking.move_out_status = "NEXT WEEK"
        else:
            booking.move_out_status = "UPCOMING"

    # Weekly breakdown for dashboard summary
    this_week_count = sum(1 for b in upcoming_move_outs if 0 <= b.days_until_move_out <= 7)
    next_week_count = sum(1 for b in upcoming_move_outs if 8 <= b.days_until_move_out <= 14)

    context = {
        'title': 'Move Out Report',
        'upcoming_move_outs': upcoming_move_outs,
        'total_refunds': total_refunds,
        'total_deposits': total_deposits,
        'this_week_count': this_week_count,
        'next_week_count': next_week_count,
        'report_range': f"{move_out_date_start} to {move_out_date_end}",
        'today': today,
    }

    return render(request, 'reports/move_out.html', context)

@staff_required
def monthly_sales_report(request):
    """Requirement #6: Monthly Sales Report"""
    today = timezone.now().date()

    # Get selected month (default to current)
    selected_month = request.GET.get('month', today.strftime('%Y-%m'))
    year, month = map(int, selected_month.split('-'))

    # Get payments for the selected month
    monthly_payments = Payment.objects.filter(
        payment_date__year=year,
        payment_date__month=month,
        status='completed'
    ).select_related('booking__tenant', 'booking__room')

    total_income = sum(p.amount for p in monthly_payments)
    total_transactions = monthly_payments.count()

    # Group by payment type
    payment_summary = {}
    for payment_type, label in Payment.PAYMENT_TYPES:
        type_payments = monthly_payments.filter(payment_type=payment_type)
        total = sum(p.amount for p in type_payments)
        count = type_payments.count()
        avg = total / count if count > 0 else 0
        percent = (total / total_income * 100) if total_income > 0 else 0

        payment_summary[payment_type] = {
            'label': label,
            'count': count,
            'total': total,
            'average': avg,
            'percentage': percent,
            'payments': type_payments,
        }

    context = {
        'title': f'Monthly Sales Report - {datetime(year, month, 1).strftime("%B %Y")}',
        'payment_summary': payment_summary,
        'total_income': total_income,
        'selected_month': selected_month,
        'today': today,
        'total_transactions': total_transactions,
    }

    return render(request, 'reports/monthly_sales.html', context)


@staff_required
def utilities_report(request):
    """Requirement #13: Electricity/Water/Gas Report"""
    today = timezone.now().date()

    # Unpaid utility bills
    unpaid_utilities = Payment.objects.filter(
        payment_type='utility',
        status='pending'
    ).select_related('booking__tenant', 'booking__room')

    total_unpaid = sum(p.amount for p in unpaid_utilities)
    unpaid_count = unpaid_utilities.count()
    average_bill = total_unpaid / unpaid_count if unpaid_count > 0 else 0

    # Calculate days overdue for each payment (if due_date exists)
    for payment in unpaid_utilities:
        if payment.due_date:
            days_overdue = (today - payment.due_date).days
            payment.days_overdue = days_overdue if days_overdue > 0 else 0
        else:
            payment.days_overdue = None

    context = {
        'title': 'Utilities Payment Report',
        'unpaid_utilities': unpaid_utilities,
        'total_unpaid': total_unpaid,
        'average_bill': average_bill,
        'unpaid_count': unpaid_count,
        'today': today,
    }
    return render(request, 'reports/utilities.html', context)