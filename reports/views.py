from django.db import models
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from properties.models import Room, Owner, PropertyOwnership
from bookings.models import Booking
from payments.models import Payment, UtilityBill, Expense
from tenants.models import Tenant
from contracts.models import Contract


def staff_required(view_func):
    return login_required(
        user_passes_test(lambda u: u.is_staff)(view_func),
        login_url='/admin/login/'
    )


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
    ).select_related('property_obj').prefetch_related('property_obj__rooms__booking_set')

    # Calculate pro-rata amounts for each bill
    bills_with_details = []
    total_unpaid = 0

    for bill in utility_bills:
        # Get active tenants in this property during bill period
        active_bookings = Booking.objects.filter(
            room__property=bill.property_obj,
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


@staff_required
def owners_report(request):
    """Requirement #15: Owners Report (Confidential in CRM)"""
    """Requirement #15: Owners Report (Confidential in CRM)"""
    owners = Owner.objects.prefetch_related('property_ownerships__property_obj').all()

    # CSV Export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="owners_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Owner Name', 'Email', 'Phone', 'Properties Count', 'Total Rent Owed', 'Management Fee %'])

        for owner in owners:
            writer.writerow([
                owner.name,
                owner.contact_email,
                owner.phone_number,
                owner.active_properties_count,
                owner.total_rent_owed,
                owner.management_fee_percentage
            ])
        return response
    # Calculate statistics
    total_owners = owners.count()
    active_ownerships = PropertyOwnership.objects.filter(is_active=True)
    total_rent_owed = sum(owner.total_rent_owed for owner in owners)

    # Contracts expiring soon
    expiring_contracts = PropertyOwnership.objects.filter(
        contract_end__lte=timezone.now().date() + timedelta(days=30),
        contract_end__gte=timezone.now().date(),
        is_active=True
    )

    context = {
        'title': 'Owners Report',
        'owners': owners,
        'total_owners': total_owners,
        'active_ownerships_count': active_ownerships.count(),
        'total_rent_owed': total_rent_owed,
        'expiring_contracts': expiring_contracts,
        'today': timezone.now().date(),
    }
    return render(request, 'reports/owners.html', context)


@staff_required
def profit_loss_report(request):
    """Requirement #14: P&L Report (Confidential in CRM)"""
    # Get selected month (default to current)
    selected_month = request.GET.get('month', timezone.now().strftime('%Y-%m'))
    year, month = map(int, selected_month.split('-'))

    # Calculate date range for the month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year, month, 31).date()
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

    # INCOME: Completed payments for the month
    monthly_income = Payment.objects.filter(
        payment_date__range=[start_date, end_date],
        status='completed'
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    # EXPENSES: Expenses for the month
    monthly_expenses = Expense.objects.filter(
        payment_date__range=[start_date, end_date]
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    # OWNER PAYMENTS: Rent paid to owners for the month
    owner_payments = PropertyOwnership.objects.filter(
        last_rent_paid_date__range=[start_date, end_date],
        is_active=True
    ).aggregate(total=models.Sum('monthly_rent_to_owner'))['total'] or 0

    # Calculate net profit
    net_profit = monthly_income - monthly_expenses - owner_payments

    # Detailed breakdowns with percentages
    income_by_type_raw = Payment.objects.filter(
        payment_date__range=[start_date, end_date],
        status='completed'
    ).values('payment_type').annotate(
        total=models.Sum('amount'),
        count=models.Count('id')
    ).order_by('-total')

    # Calculate percentages for income
    income_by_type = []
    for item in income_by_type_raw:
        percentage = (item['total'] / monthly_income * 100) if monthly_income > 0 else 0
        income_by_type.append({
            'payment_type': item['payment_type'],
            'total': item['total'],
            'count': item['count'],
            'percentage': round(percentage, 1)
        })

    expenses_by_category_raw = Expense.objects.filter(
        payment_date__range=[start_date, end_date]
    ).values('category__name').annotate(
        total=models.Sum('amount'),
        count=models.Count('id')
    ).order_by('-total')

    # Calculate percentages for expenses
    expenses_by_category = []
    for item in expenses_by_category_raw:
        percentage = (item['total'] / monthly_expenses * 100) if monthly_expenses > 0 else 0
        expenses_by_category.append({
            'category_name': item['category__name'],
            'total': item['total'],
            'count': item['count'],
            'percentage': round(percentage, 1)
        })

    # Monthly comparison (previous month)
    prev_month = start_date - timedelta(days=start_date.day)
    prev_income = Payment.objects.filter(
        payment_date__year=prev_month.year,
        payment_date__month=prev_month.month,
        status='completed'
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    income_change = monthly_income - prev_income
    income_change_percent = (income_change / prev_income * 100) if prev_income > 0 else 0

    # CSV Export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="profit_loss_report_{selected_month}.csv"'
        writer = csv.writer(response)

        # Header
        writer.writerow(['Wing Kong Property Management - Profit & Loss Report'])
        writer.writerow([f'Period: {start_date.strftime("%B %Y")}'])
        writer.writerow(['Generated on:', timezone.now().strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])

        # Summary Section
        writer.writerow(['FINANCIAL SUMMARY'])
        writer.writerow(['Total Income', f'HK$ {monthly_income}'])
        writer.writerow(['Total Expenses', f'HK$ {monthly_expenses}'])
        writer.writerow(['Owner Payments', f'HK$ {owner_payments}'])
        writer.writerow(['Net Profit/Loss', f'HK$ {net_profit}'])
        writer.writerow([])

        # Income Breakdown
        writer.writerow(['INCOME BREAKDOWN BY TYPE'])
        writer.writerow(['Payment Type', 'Amount', 'Transaction Count', 'Percentage'])
        for item in income_by_type:
            writer.writerow([
                item['payment_type'].title(),
                f'HK$ {item["total"]}',
                item['count'],
                f'{item["percentage"]}%'
            ])
        writer.writerow([])

        # Expense Breakdown
        writer.writerow(['EXPENSE BREAKDOWN BY CATEGORY'])
        writer.writerow(['Category', 'Amount', 'Expense Count', 'Percentage'])
        for item in expenses_by_category:
            writer.writerow([
                item['category_name'],
                f'HK$ {item["total"]}',
                item['count'],
                f'{item["percentage"]}%'
            ])
        writer.writerow([])

        # Monthly Comparison
        writer.writerow(['MONTHLY COMPARISON'])
        writer.writerow(['Current Month Income', f'HK$ {monthly_income}'])
        writer.writerow(['Previous Month Income', f'HK$ {prev_income}'])
        writer.writerow(['Income Change', f'HK$ {income_change}'])
        writer.writerow(['Income Change %', f'{income_change_percent}%'])

        return response

    context = {
        'title': f'Profit & Loss Report - {start_date.strftime("%B %Y")}',
        'selected_month': selected_month,
        'start_date': start_date,
        'end_date': end_date,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'owner_payments': owner_payments,
        'net_profit': net_profit,
        'income_by_type': income_by_type,
        'expenses_by_category': expenses_by_category,
        'income_change': income_change,
        'income_change_percent': round(income_change_percent, 1),
        'today': timezone.now().date(),
    }
    return render(request, 'reports/profit_loss.html', context)


@staff_required
def rent_increase_report(request):
    """Requirement #17: Rent Increase Detection Report"""
    rooms_needing_increase = []
    all_rooms = Room.objects.select_related('property').prefetch_related(
        'booking_set',
        'booking_set__contract'
    )
    for room in all_rooms:
        if room.needs_rent_increase_notice():
            ending_contracts = room.get_ending_contracts()
            if ending_contracts:
                rooms_needing_increase.append({
                    'room': room,
                    'ending_contracts': ending_contracts,
                    'current_rent': room.monthly_rent,
                    'advertised_price': room.post_ad_price,
                    'rent_difference': (room.post_ad_price - room.monthly_rent) if room.post_ad_price else 0
                })

    # Calculate statistics
    total_rooms_needing_increase = len(rooms_needing_increase)
    total_contracts_ending = sum(len(item['ending_contracts']) for item in rooms_needing_increase)
    total_potential_increase = sum(
        item['rent_difference'] for item in rooms_needing_increase if item['rent_difference'] > 0)

    # CSV Export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rent_increase_report.csv"'
        writer = csv.writer(response)

        writer.writerow(['Wing Kong Property Management - Rent Increase Report'])
        writer.writerow(['Generated on:', timezone.now().strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])

        writer.writerow(['RENT INCREASE ALERTS - Rooms below HK$1500 with contracts ending soon'])
        writer.writerow(
            ['Room Code', 'Property', 'Current Rent', 'Advertised Price', 'Rent Difference', 'Contracts Ending',
             'Tenants Affected'])

        for item in rooms_needing_increase:
            room = item['room']
            tenant_names = ", ".join([contract.booking.tenant.full_name for contract in item['ending_contracts']])
            contract_dates = ", ".join(
                [contract.end_date.strftime('%Y-%m-%d') for contract in item['ending_contracts']])

            writer.writerow([
                room.room_code,
                room.property.name,
                f"HK$ {item['current_rent']}",
                f"HK$ {item['advertised_price']}",
                f"HK$ {item['rent_difference']}",
                contract_dates,
                tenant_names
            ])

        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total rooms needing increase notice:', total_rooms_needing_increase])
        writer.writerow(['Total contracts ending soon:', total_contracts_ending])
        writer.writerow(['Total potential rent increase:', f"HK$ {total_potential_increase}"])

        return response

    context = {
        'title': 'Rent Increase Report',
        'rooms_needing_increase': rooms_needing_increase,
        'total_rooms_needing_increase': total_rooms_needing_increase,
        'total_contracts_ending': total_contracts_ending,
        'total_potential_increase': total_potential_increase,
        'threshold': 1500,  # HK$1500 as per requirement
        'today': timezone.now().date(),
    }
    return render(request, 'reports/rent_increase.html', context)