from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from properties.models import Room
from bookings.models import Booking
from payments.models import Payment, UtilityBill
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
def temporary_stay_report(request):
    today = timezone.now().date()

    # Active temporary stays
    active_temporary_stays = Contract.objects.filter(
        is_temporary_stay_active=True
    ).select_related(
        'booking__tenant',
        'booking__room',
        'temporary_room'
    )

    # Upcoming temporary stay endings (next 7 days)
    upcoming_endings = Contract.objects.filter(
        is_temporary_stay_active=True,
        temporary_stay_end__range=[today, today + timedelta(days=7)]
    ).select_related('booking__tenant', 'booking__room', 'temporary_room')

    # Stays needing room switch
    needs_switch = Contract.objects.filter(
        is_temporary_stay_active=True,
        temporary_stay_end__lt=today
    ).select_related('booking__tenant', 'booking__room', 'temporary_room')

    # Calculate totals
    total_refunds_due = sum(
        contract.rent_difference for contract in active_temporary_stays if contract.rent_difference > 0)
    total_additional_payments = sum(
        abs(contract.rent_difference) for contract in active_temporary_stays if contract.rent_difference < 0)

    context = {
        'title': 'Temporary Stay Report',
        'active_temporary_stays': active_temporary_stays,
        'upcoming_endings': upcoming_endings,
        'needs_switch': needs_switch,
        'total_refunds_due': total_refunds_due,
        'total_additional_payments': total_additional_payments,
        'today': today,
    }
    return render(request, 'reports/temporary_stay.html', context)


@staff_required
def utilities_report(request):
    """Requirement #13: Electricity/Water/Gas Report with Pro-Rata Calculation"""
    today = timezone.now().date()

    # Get all utility bills
    utility_bills = UtilityBill.objects.filter(
        is_settled=False
    ).select_related('property').prefetch_related('property__rooms__booking_set')

    # Calculate pro-rata amounts for each bill
    bills_with_details = []
    total_unpaid = 0

    for bill in utility_bills:
        # Get active tenants in this property during bill period
        active_bookings = Booking.objects.filter(
            room__property=bill.property,
            status='active',
            move_in_date__lte=bill.due_date,
            move_out_date__gte=bill.bill_date
        ).select_related('tenant', 'room')

        # Calculate pro-rata share per tenant
        total_share_days = 0
        tenant_shares = []

        for booking in active_bookings:
            # Calculate days tenant was responsible for this bill
            bill_start = max(booking.move_in_date, bill.bill_date)
            bill_end = min(booking.move_out_date, bill.due_date)
            tenant_days = (bill_end - bill_start).days + 1

            if tenant_days > 0:
                total_share_days += tenant_days
                tenant_shares.append({
                    'booking': booking,
                    'days': tenant_days,
                    'share_amount': 0,  # Will calculate after total
                })

        # Calculate each tenant's share amount
        for tenant_share in tenant_shares:
            if total_share_days > 0:
                tenant_share['share_amount'] = (bill.bill_amount / total_share_days) * tenant_share['days']

        # Check if payments received for this bill
        utility_payments = Payment.objects.filter(
            payment_type='utility',
            booking__in=[ts['booking'] for ts in tenant_shares],
            payment_date__range=[bill.bill_date, bill.due_date]
        )

        paid_tenants = set(payment.booking_id for payment in utility_payments)

        bills_with_details.append({
            'bill': bill,
            'tenant_shares': tenant_shares,
            'total_share_days': total_share_days,
            'paid_tenants': paid_tenants,
            'total_amount': bill.bill_amount,
            'unpaid_amount': bill.bill_amount - sum(p.amount for p in utility_payments),
        })

        total_unpaid += bills_with_details[-1]['unpaid_amount']

    # Also show simple unpaid utility payments (fallback)
    unpaid_utility_payments = Payment.objects.filter(
        payment_type='utility',
        status='pending'
    ).select_related('booking__tenant', 'booking__room')

    context = {
        'title': 'Utilities Payment Report',
        'bills_with_details': bills_with_details,
        'total_unpaid': total_unpaid,
        'unpaid_utility_payments': unpaid_utility_payments,
        'today': today,
    }
    return render(request, 'reports/utilities.html', context)