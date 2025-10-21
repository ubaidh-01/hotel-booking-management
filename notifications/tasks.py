import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from bookings.models import Booking
from payments.models import Payment
from contracts.models import Contract
from tenants.models import Tenant
from .services import EmailService
from .models import NotificationLog

logger = logging.getLogger(__name__)


@shared_task
def send_rent_reminders():
    """Send automated rent reminders (Requirement #9a)"""
    today = timezone.now().date()
    logger.info("Starting rent reminder task...")

    # Rent due in 3 days
    due_soon_date = today + timedelta(days=3)
    due_soon_payments = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date=due_soon_date
    ).select_related('booking__tenant', 'booking__room')

    for payment in due_soon_payments:
        try:
            success = EmailService.send_rent_reminder(payment)
            NotificationLog.objects.create(
                tenant=payment.booking.tenant,
                notification_type='rent_reminder',
                status='sent' if success else 'failed',
                subject=f'Rent Due Soon - {payment.booking.room.room_code}',
                related_booking=payment.booking,
                related_payment=payment,
                sent_at=timezone.now() if success else None
            )
        except Exception as e:
            logger.error(f"Failed to send rent reminder for {payment.id}: {e}")

    # Overdue rent (due yesterday)
    overdue_payments = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date__lt=today
    ).select_related('booking__tenant', 'booking__room')

    for payment in overdue_payments:
        try:
            success = EmailService.send_rent_reminder(payment)
            NotificationLog.objects.create(
                tenant=payment.booking.tenant,
                notification_type='rent_reminder',
                status='sent' if success else 'failed',
                subject=f'Rent Overdue - {payment.booking.room.room_code}',
                related_booking=payment.booking,
                related_payment=payment,
                sent_at=timezone.now() if success else None
            )
        except Exception as e:
            logger.error(f"Failed to send overdue reminder for {payment.id}: {e}")

    logger.info(
        f"Rent reminder task completed. Processed {due_soon_payments.count() + overdue_payments.count()} payments.")


@shared_task
def send_contract_reminders():
    """Send contract renewal reminders (Requirement #11)"""
    today = timezone.now().date()
    reminder_date = today + timedelta(days=21)  # 3 weeks before

    ending_contracts = Contract.objects.filter(
        end_date=reminder_date,
        status='signed'
    ).select_related('booking__tenant', 'booking__room')

    logger.info(f"Found {ending_contracts.count()} contracts ending soon.")

    for contract in ending_contracts:
        try:
            success = EmailService.send_contract_reminder(contract)
            NotificationLog.objects.create(
                tenant=contract.booking.tenant,
                notification_type='contract_reminder',
                status='sent' if success else 'failed',
                subject=f'Contract Renewal - {contract.booking.room.room_code}',
                related_booking=contract.booking,
                sent_at=timezone.now() if success else None
            )
        except Exception as e:
            logger.error(f"Failed to send contract reminder for {contract.id}: {e}")


@shared_task
def send_birthday_wishes():
    """Send birthday wishes to current tenants (Requirement #19)"""
    today = timezone.now().date()

    # Get current tenants with birthdays today
    current_tenants = Tenant.objects.filter(
        date_of_birth__month=today.month,
        date_of_birth__day=today.day
    )

    # Filter only tenants with active bookings
    birthday_tenants = []
    for tenant in current_tenants:
        active_booking = Booking.objects.filter(
            tenant=tenant,
            status='active',
            move_in_date__lte=today,
            move_out_date__gte=today
        ).exists()
        if active_booking:
            birthday_tenants.append(tenant)

    logger.info(f"Found {len(birthday_tenants)} tenants with birthdays today.")

    for tenant in birthday_tenants:
        try:
            success = EmailService.send_birthday_wish(tenant)
            NotificationLog.objects.create(
                tenant=tenant,
                notification_type='birthday_wish',
                status='sent' if success else 'failed',
                subject='Happy Birthday from Wing Kong Properties!',
                sent_at=timezone.now() if success else None
            )
        except Exception as e:
            logger.error(f"Failed to send birthday wish to {tenant.id}: {e}")


@shared_task
def process_late_fees():
    """Process automatic late fees and send invoices (Requirement #9b)"""
    today = timezone.now().date()

    # Payments overdue by 7 days (send invoice)
    seven_days_overdue = today - timedelta(days=7)
    weekly_overdue = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date=seven_days_overdue
    ).select_related('booking__tenant', 'booking__room')

    for payment in weekly_overdue:
        try:
            success = EmailService.send_late_fee_invoice(payment)
            NotificationLog.objects.create(
                tenant=payment.booking.tenant,
                notification_type='late_fee_invoice',
                status='sent' if success else 'failed',
                subject=f'Late Fee Invoice - {payment.booking.room.room_code}',
                related_booking=payment.booking,
                related_payment=payment,
                sent_at=timezone.now() if success else None
            )
        except Exception as e:
            logger.error(f"Failed to send weekly late fee invoice for {payment.id}: {e}")

    # Payments overdue by 14 days (send court notice)
    fourteen_days_overdue = today - timedelta(days=14)
    court_notice_overdue = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date=fourteen_days_overdue
    ).select_related('booking__tenant', 'booking__room')

    for payment in court_notice_overdue:
        try:
            success = EmailService.send_late_fee_invoice(payment)  # Same function handles court notice
            NotificationLog.objects.create(
                tenant=payment.booking.tenant,
                notification_type='late_fee_invoice',
                status='sent' if success else 'failed',
                subject=f'Court Notice - Rent Overdue - {payment.booking.room.room_code}',
                related_booking=payment.booking,
                related_payment=payment,
                sent_at=timezone.now() if success else None
            )
        except Exception as e:
            logger.error(f"Failed to send court notice for {payment.id}: {e}")


@shared_task
def sync_room_status():
    """Daily sync of room status based on bookings"""
    try:
        from django.core.management import call_command
        call_command('sync_room_status')
        logger.info("Daily room status sync completed.")
    except Exception as e:
        logger.error(f"Failed to sync room status: {e}")



def send_test_email():
    """Test task to verify email setup"""
    print("INN")
    try:
        send_mail(
            'Test Email from Wing Kong CRM',
            'This is a test email to verify your email configuration.',
            'ubaidafzal022@gmail.com',
            ['ubaidafzal022@gmail.com'],
            fail_silently=False,
        )
        print("Test email sent successfully.")
        return True
    except Exception as e:
        print(f"Failed to send test email: {e}")
        return False