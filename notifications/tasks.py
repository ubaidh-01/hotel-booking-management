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
    """Send contract renewal reminders (Enhanced for Requirement #11)"""
    today = timezone.now().date()

    # Contracts ending in 21 days (3 weeks) - for renewal reminders
    renewal_contracts = Contract.objects.filter(
        end_date=today + timedelta(days=21),
        status='signed',
        renewal_status='not_sent'
    ).select_related('booking__tenant', 'booking__room')

    logger.info(f"Found {renewal_contracts.count()} contracts needing renewal reminders.")

    for contract in renewal_contracts:
        try:
            success = EmailService.send_contract_renewal_reminder(contract)

            if success:
                contract.renewal_status = 'sent'
                contract.renewal_sent_date = timezone.now()
                contract.save()

            NotificationLog.objects.create(
                tenant=contract.booking.tenant,
                notification_type='contract_reminder',
                status='sent' if success else 'failed',
                subject=f'Contract Renewal Reminder - {contract.booking.room.room_code}',
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
    """Process automatic late fees and send invoices (Requirement #9b) - UPDATED"""
    today = timezone.now().date()

    # First, create any missing late fee payments
    create_late_fee_payments()

    # Now send notifications for overdue payments
    # Payments overdue by 7 days (send invoice)
    seven_days_overdue = today - timedelta(days=7)
    weekly_overdue = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date__lte=seven_days_overdue  # FIXED: Changed = to __lte
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
        due_date__lte=fourteen_days_overdue  # FIXED: Changed = to __lte
    ).select_related('booking__tenant', 'booking__room')

    for payment in court_notice_overdue:
        try:
            success = EmailService.send_late_fee_invoice(payment, is_court_notice=True)
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
def detect_rent_increases():
    """Automatically detect rooms needing rent increase notices (Requirement #17)"""
    from properties.models import Room
    from contracts.models import Contract

    logger.info("Starting rent increase detection task...")

    rooms_needing_increase = []
    threshold = 1500  # HK$1500

    # Get all rooms with post_ad_price below threshold
    low_rent_rooms = Room.objects.filter(
        post_ad_price__lt=threshold,
        post_ad_price__isnull=False
    ).select_related('property')

    for room in low_rent_rooms:
        # Check if any contracts are ending in next 30 days
        today = timezone.now().date()
        ending_contracts = Contract.objects.filter(
            booking__room=room,
            end_date__lte=today + timedelta(days=30),
            end_date__gte=today,
            status='signed'
        ).select_related('booking__tenant')

        if ending_contracts.exists():
            rooms_needing_increase.append({
                'room': room,
                'ending_contracts': list(ending_contracts),
                'current_rent': room.monthly_rent,
                'advertised_price': room.post_ad_price,
                'rent_difference': room.post_ad_price - room.monthly_rent
            })

            for contract in ending_contracts:
                try:
                    success = EmailService.send_rent_increase_notice(
                        contract.booking.tenant,
                        room,
                        room.post_ad_price
                    )
                    # Log the notification
                    NotificationLog.objects.create(
                        tenant=contract.booking.tenant,
                        notification_type='rent_increase',
                        status='sent' if success else 'failed',
                        subject=f'Rent Increase Notice - {room.room_code}',
                        related_booking=contract.booking,
                        sent_at=timezone.now() if success else None
                    )

                    if success:
                        logger.info(
                            f"Rent increase notice sent for {room.room_code} to {contract.booking.tenant.full_name}")
                    else:
                        logger.error(f"Failed to send rent increase notice for {room.room_code}")

                except Exception as e:
                    logger.error(f"Error sending rent increase notice: {e}")

    logger.info(
        f"Rent increase detection completed. Found {len(rooms_needing_increase)} rooms needing increase notices.")
    return len(rooms_needing_increase)


@shared_task
def sync_room_status():
    """Daily sync of room status based on bookings"""
    try:
        from django.core.management import call_command
        call_command('sync_room_status')
        logger.info("Daily room status sync completed.")
    except Exception as e:
        logger.error(f"Failed to sync room status: {e}")


@shared_task
def create_late_fee_payments():
    """Automatically create late fee payment records (Requirement #9)"""
    from payments.models import Payment
    from datetime import timedelta

    today = timezone.now().date()
    logger.info("Starting automatic late fee payment creation...")

    # Find all overdue rent payments
    overdue_rent_payments = Payment.objects.filter(
        payment_type='rent',
        status='pending',
        due_date__lt=today
    ).select_related('booking__tenant', 'booking__room')

    total_late_fees_created = 0

    for rent_payment in overdue_rent_payments:
        try:
            # Calculate days overdue and late fee amount
            days_overdue = (today - rent_payment.due_date).days
            late_fee_amount = days_overdue * 100  # HK$100 per day

            # Skip if no late fees or already created for today
            if late_fee_amount <= 0:
                continue

            # Check if late fee already exists for this period
            existing_late_fee = Payment.objects.filter(
                booking=rent_payment.booking,
                payment_type='late_fee',
                payment_date=today,
                status='pending'
            ).exists()

            if not existing_late_fee:
                # Create late fee payment record
                late_fee_payment = Payment.objects.create(
                    booking=rent_payment.booking,
                    payment_type='late_fee',
                    amount=late_fee_amount,
                    payment_date=today,
                    due_date=today,
                    status='pending',
                    receipt_number=f"LATE-{today.strftime('%Y%m%d')}-{rent_payment.booking.id}",
                    late_fee_days=days_overdue,
                    late_fee_amount=late_fee_amount
                )

                total_late_fees_created += 1
                logger.info(
                    f"Created late fee payment HK${late_fee_amount} for {rent_payment.booking.tenant.full_name}")

                # Send late fee invoice email
                EmailService.send_late_fee_invoice(late_fee_payment)

        except Exception as e:
            logger.error(f"Failed to create late fee for payment {rent_payment.id}: {e}")

    logger.info(f"Late fee creation completed: {total_late_fees_created} late fees created")
    return total_late_fees_created


@shared_task
def send_move_out_reminders():
    """Send move out reminders (Requirement #8, #11)"""
    today = timezone.now().date()

    # Contracts ending in 21 days - for move out reminders
    move_out_contracts = Contract.objects.filter(
        end_date=today + timedelta(days=21),
        status='signed',
        move_out_notice_sent=False
    ).select_related('booking__tenant', 'booking__room')

    logger.info(f"Found {move_out_contracts.count()} contracts needing move out reminders.")

    for contract in move_out_contracts:
        try:
            success = EmailService.send_move_out_reminder(contract)

            if success:
                contract.move_out_notice_sent = True
                contract.move_out_notice_sent_date = timezone.now()
                contract.save()

            NotificationLog.objects.create(
                tenant=contract.booking.tenant,
                notification_type='move_out_reminder',
                status='sent' if success else 'failed',
                subject=f'Move Out Reminder - {contract.booking.room.room_code}',
                related_booking=contract.booking,
                sent_at=timezone.now() if success else None
            )

        except Exception as e:
            logger.error(f"Failed to send move out reminder for {contract.id}: {e}")


@shared_task
def send_final_move_out_warnings():
    """Send final warnings for contracts ending in 7 days"""
    today = timezone.now().date()

    final_warning_contracts = Contract.objects.filter(
        end_date=today + timedelta(days=7),
        status='signed',
        renewal_status__in=['not_sent', 'sent', 'declined']
    ).select_related('booking__tenant', 'booking__room')

    logger.info(f"Found {final_warning_contracts.count()} contracts needing final warnings.")

    for contract in final_warning_contracts:
        try:
            success = EmailService.send_final_move_out_warning(contract)

            NotificationLog.objects.create(
                tenant=contract.booking.tenant,
                notification_type='move_out_reminder',
                status='sent' if success else 'failed',
                subject=f'FINAL: Move Out Warning - {contract.booking.room.room_code}',
                related_booking=contract.booking,
                sent_at=timezone.now() if success else None
            )

        except Exception as e:
            logger.error(f"Failed to send final move out warning for {contract.id}: {e}")


@shared_task
def allocate_utility_bills():
    """Automatically allocate utility bills to tenants (Requirement #13)"""
    from payments.models import UtilityBill

    logger.info("Starting utility bill allocation task...")

    # Get unallocated utility bills that are due soon or past due
    today = timezone.now().date()
    unallocated_bills = UtilityBill.objects.filter(
        is_allocated=False,
        due_date__lte=today + timedelta(days=7)  # Allocate bills due in next 7 days
    ).select_related('property')

    total_allocated = 0
    total_payments_created = 0

    for bill in unallocated_bills:
        try:
            created_payments = bill.create_utility_payments()
            total_payments_created += len(created_payments)

            if created_payments:
                total_allocated += 1
                logger.info(f"Allocated utility bill {bill.id} to {len(created_payments)} tenants")

                # Send notifications to tenants
                for payment in created_payments:
                    EmailService.send_utility_bill_notification(payment, bill)

        except Exception as e:
            logger.error(f"Failed to allocate utility bill {bill.id}: {e}")

    logger.info(
        f"Utility allocation completed: {total_allocated} bills allocated, {total_payments_created} payments created")
    return total_allocated


@shared_task
def send_utility_payment_reminders():
    """Send reminders for overdue utility payments"""
    from payments.models import Payment

    today = timezone.now().date()
    overdue_utility_payments = Payment.objects.filter(
        payment_type='utility',
        status='pending',
        due_date__lt=today
    ).select_related('booking__tenant', 'booking__room')

    logger.info(f"Found {overdue_utility_payments.count()} overdue utility payments")

    for payment in overdue_utility_payments:
        try:
            success = EmailService.send_utility_payment_reminder(payment)

            NotificationLog.objects.create(
                tenant=payment.booking.tenant,
                notification_type='utility_reminder',
                status='sent' if success else 'failed',
                subject=f'Utility Payment Overdue - {payment.booking.room.room_code}',
                related_booking=payment.booking,
                related_payment=payment,
                sent_at=timezone.now() if success else None
            )

        except Exception as e:
            logger.error(f"Failed to send utility reminder for {payment.id}: {e}")


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
