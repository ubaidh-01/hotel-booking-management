from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime, timedelta
import logging

from contracts.models import Contract
from payments.models import Payment

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_rent_reminder(payment):
        """Send rent reminder email (Requirement #9a)"""
        try:
            tenant = payment.booking.tenant
            room = payment.booking.room
            today = datetime.now().date()

            # Calculate days and fees
            days_until_due = (payment.due_date - today).days if payment.due_date else 0
            days_overdue = (today - payment.due_date).days if payment.due_date and payment.due_date < today else 0
            late_fee = days_overdue * 100  # HK$100 per day
            total_amount_due = payment.amount + late_fee

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'due_date': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else 'Not set',
                'amount_due': payment.amount,
                'late_fee': late_fee,
                'total_amount_due': total_amount_due,
                'days_until_due': max(0, days_until_due),
                'days_overdue': max(0, days_overdue),
                'payment_url': f"https://wing-kong.com/payments/{payment.id}",
            }

            subject = f"Rent Reminder - {room.room_code}"
            if days_overdue > 0:
                subject = f"URGENT: Rent Overdue {days_overdue} Days - {room.room_code}"
                if days_overdue >= 14:
                    subject = f"COURT NOTICE: Rent Overdue {days_overdue} Days - {room.room_code}"

            html_content = render_to_string('emails/rent_reminder.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],
                # to=[tenant.user.email],
                reply_to=['accounts@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Rent reminder sent to {tenant.full_name} for {room.room_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to send rent reminder: {e}")
            return False

    @staticmethod
    def send_contract_reminder(contract):
        """Send contract renewal reminder (Requirement #11)"""
        try:
            tenant = contract.booking.tenant
            room = contract.booking.room
            today = datetime.now().date()

            days_until_end = (contract.end_date - today).days
            response_deadline = (today + timedelta(days=7)).strftime('%Y-%m-%d')

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'current_rent': contract.monthly_rent,
                'contract_end_date': contract.end_date.strftime('%Y-%m-%d'),
                'days_until_end': days_until_end,
                'response_deadline': response_deadline,
                'renew_url': f"https://wing-kong.com/contracts/{contract.id}/renew",
                'move_out_url': f"https://wing-kong.com/contracts/{contract.id}/move-out",
            }

            subject = f"Contract Renewal Reminder - {room.room_code}"

            html_content = render_to_string('emails/contract_reminder.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],
                # to=[tenant.user.email],
                reply_to=['leasing@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Contract reminder sent to {tenant.full_name} for {room.room_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to send contract reminder: {e}")
            return False

    @staticmethod
    def send_birthday_wish(tenant):
        """Send birthday wish to tenant (Requirement #19)"""
        try:
            context = {
                'tenant_name': tenant.full_name,
            }

            subject = "🎉 Happy Birthday from Wing Kong Properties!"

            html_content = render_to_string('emails/birthday_wish.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                # to=[tenant.user.email]
                to=['ubaidafzal022@gmail.com'],
                reply_to=['info@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Birthday wish sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send birthday wish: {e}")
            return False

    # notifications/services.py - UPDATE send_late_fee_invoice METHOD:

    @staticmethod
    def send_late_fee_invoice(payment, is_court_notice=False):
        """Send automatic late fee invoice (Requirement #9b) - UPDATED"""
        try:
            tenant = payment.booking.tenant
            room = payment.booking.room
            today = timezone.now().date()

            # Calculate total amounts
            if payment.payment_type == 'late_fee':
                # This is a late fee payment itself
                late_fee_amount = payment.amount
                days_overdue = payment.late_fee_days
                # Find the original rent payment
                rent_payment = Payment.objects.filter(
                    booking=payment.booking,
                    payment_type='rent',
                    due_date=payment.payment_date - timedelta(days=days_overdue)
                ).first()
                original_amount = rent_payment.amount if rent_payment else 0
            else:
                # This is a rent payment with late fees
                days_overdue = (today - payment.due_date).days
                late_fee_amount = days_overdue * 100
                original_amount = payment.amount

            total_amount_due = original_amount + late_fee_amount

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'original_amount': original_amount,
                'late_fee': late_fee_amount,
                'total_amount_due': total_amount_due,
                'days_overdue': days_overdue,
                'due_date': payment.due_date.strftime('%Y-%m-%d'),
                'invoice_date': today.strftime('%Y-%m-%d'),
                'payment_url': f"https://wing-kong.com/payments/{payment.id}",
                'is_court_notice': is_court_notice,
            }

            if is_court_notice:
                subject = f"COURT NOTICE: Rent Overdue {days_overdue} Days - {room.room_code}"
            elif days_overdue >= 14:
                subject = f"FINAL NOTICE: Rent Overdue {days_overdue} Days - {room.room_code}"
            elif days_overdue >= 7:
                subject = f"URGENT: Rent Overdue {days_overdue} Days - {room.room_code}"
            else:
                subject = f"Late Fee Invoice - {room.room_code}"

            html_content = render_to_string('emails/late_fee_invoice.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['accounts@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Late fee invoice sent to {tenant.full_name} for {room.room_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to send late fee invoice: {e}")
            return False


    @staticmethod
    def send_rent_increase_notice(tenant, room, new_rent_amount=None):
        """Send rent increase notice (Requirement #17)"""
        try:
            # Get current contract ending soon
            today = timezone.now().date()
            current_contract = Contract.objects.filter(
                booking__tenant=tenant,
                booking__room=room,
                end_date__lte=today + timedelta(days=30),
                status='signed'
            ).first()

            if not current_contract:
                logger.error(f"No ending contract found for tenant {tenant.id} in room {room.room_code}")
                return False

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'current_rent': room.monthly_rent,
                'proposed_rent': new_rent_amount or room.post_ad_price,
                'contract_end_date': current_contract.end_date.strftime('%Y-%m-%d'),
                'days_until_end': (current_contract.end_date - today).days,
                'renewal_url': f"https://wing-kong.com/contracts/{current_contract.id}/renew",
            }

            subject = f"Rent Increase Notice - {room.room_code}"

            html_content = render_to_string('emails/rent_increase_notice.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['leasing@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Rent increase notice sent to {tenant.full_name} for {room.room_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to send rent increase notice: {e}")
            return False


    @staticmethod
    def send_contract_renewal_reminder(contract):
        """Send contract renewal reminder (Requirement #11)"""
        try:
            tenant = contract.booking.tenant
            room = contract.booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'current_rent': contract.monthly_rent,
                'contract_end_date': contract.end_date.strftime('%Y-%m-%d'),
                'days_until_end': contract.days_until_expiry,
                'renewal_deadline': (contract.end_date - timedelta(days=7)).strftime('%Y-%m-%d'),
                'renewal_url': f"https://wing-kong.com/contracts/{contract.id}/renew",
                'move_out_url': f"https://wing-kong.com/contracts/{contract.id}/move-out",
            }

            subject = f"Contract Renewal Reminder - {room.room_code}"

            html_content = render_to_string('emails/contract_renewal_reminder.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['leasing@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Contract renewal reminder sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send contract renewal reminder: {e}")
            return False

    @staticmethod
    def send_move_out_reminder(contract):
        """Send move out reminder (Requirement #8, #11)"""
        try:
            tenant = contract.booking.tenant
            room = contract.booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'contract_end_date': contract.end_date.strftime('%Y-%m-%d'),
                'days_until_end': contract.days_until_expiry,
                'move_out_checklist_url': f"https://wing-kong.com/move-out/checklist",
                'deposit_refund_info_url': f"https://wing-kong.com/deposit-refund-info",
            }

            subject = f"Move Out Reminder - {room.room_code}"

            html_content = render_to_string('emails/move_out_reminder.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['operations@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Move out reminder sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send move out reminder: {e}")
            return False

    @staticmethod
    def send_final_move_out_warning(contract):
        """Send final move out warning"""
        try:
            tenant = contract.booking.tenant
            room = contract.booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'contract_end_date': contract.end_date.strftime('%Y-%m-%d'),
                'days_until_end': contract.days_until_expiry,
                'urgent_action_required': contract.days_until_expiry <= 3,
            }

            if contract.days_until_expiry <= 3:
                subject = f"URGENT: Final Move Out Warning - {room.room_code}"
            else:
                subject = f"Final Move Out Warning - {room.room_code}"

            html_content = render_to_string('emails/final_move_out_warning.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['operations@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Final move out warning sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send final move out warning: {e}")
            return False



    @staticmethod
    def send_utility_bill_notification(payment, utility_bill):
        """Send utility bill notification to tenant"""
        try:
            tenant = payment.booking.tenant
            room = payment.booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'utility_type': utility_bill.get_bill_type_display(),
                'amount_due': payment.amount,
                'due_date': payment.due_date.strftime('%Y-%m-%d'),
                'bill_period': f"{utility_bill.bill_date} to {utility_bill.due_date}",
                'payment_url': f"https://wing-kong.com/payments/{payment.id}",
                'utility_bill_url': f"https://wing-kong.com/utilities/{utility_bill.id}",
            }

            subject = f"Utility Bill - {utility_bill.get_bill_type_display()} - {room.room_code}"

            html_content = render_to_string('emails/utility_bill_notification.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['utilities@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Utility bill notification sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send utility bill notification: {e}")
            return False


    @staticmethod
    def send_utility_payment_reminder(payment):
        """Send utility payment reminder"""
        try:
            tenant = payment.booking.tenant
            room = payment.booking.room

            days_overdue = (timezone.now().date() - payment.due_date).days

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'amount_due': payment.amount,
                'original_due_date': payment.due_date.strftime('%Y-%m-%d'),
                'days_overdue': days_overdue,
                'payment_url': f"https://wing-kong.com/payments/{payment.id}",
            }

            if days_overdue > 7:
                subject = f"URGENT: Utility Payment Overdue {days_overdue} Days - {room.room_code}"
            else:
                subject = f"Utility Payment Reminder - {room.room_code}"

            html_content = render_to_string('emails/utility_payment_reminder.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['utilities@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Utility payment reminder sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send utility payment reminder: {e}")
            return False


    @staticmethod
    def send_maintenance_update(ticket, message):
        """Send maintenance update to tenant"""
        try:
            tenant = ticket.tenant
            room = ticket.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'ticket_number': ticket.ticket_number,
                'ticket_title': ticket.title,
                'update_message': message,
                'current_status': ticket.get_status_display(),
                'priority': ticket.get_priority_display(),
                'ticket_url': f"https://wing-kong.com/maintenance/{ticket.id}",
            }

            subject = f"Maintenance Update - {ticket.ticket_number} - {room.room_code}"

            html_content = render_to_string('emails/maintenance_update.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['maintenance@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Maintenance update sent to {tenant.full_name} for ticket {ticket.ticket_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to send maintenance update: {e}")
            return False

    @staticmethod
    def send_maintenance_overdue_alert(ticket):
        """Send overdue alert to assigned staff"""
        try:
            if not ticket.assigned_staff:
                return False

            staff = ticket.assigned_staff
            room = ticket.room

            context = {
                'staff_name': staff.get_full_name() or staff.username,
                'ticket_number': ticket.ticket_number,
                'ticket_title': ticket.title,
                'room_code': room.room_code,
                'days_overdue': (timezone.now().date() - ticket.estimated_completion_date).days,
                'days_open': ticket.days_open,
                'ticket_url': f"https://wing-kong.com/crm/maintenance/{ticket.id}",
            }

            subject = f"OVERDUE: Maintenance Ticket {ticket.ticket_number} - {room.room_code}"

            html_content = render_to_string('emails/maintenance_overdue_alert.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[staff.email],
                reply_to=['maintenance@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Maintenance overdue alert sent to {staff.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send maintenance overdue alert: {e}")
            return False

    @staticmethod
    def send_maintenance_escalation_alert(ticket):
        """Send escalation alert to management"""
        try:
            context = {
                'ticket_number': ticket.ticket_number,
                'ticket_title': ticket.title,
                'room_code': ticket.room.room_code,
                'tenant_name': ticket.tenant.full_name,
                'days_open': ticket.days_open,
                'priority': ticket.get_priority_display(),
                'assigned_staff': ticket.assigned_staff.get_full_name() if ticket.assigned_staff else 'Unassigned',
                'ticket_url': f"https://wing-kong.com/crm/maintenance/{ticket.id}",
            }

            subject = f"ESCALATION REQUIRED: Urgent Maintenance Ticket {ticket.ticket_number}"

            html_content = render_to_string('emails/maintenance_escalation_alert.html', context)
            text_content = strip_tags(html_content)

            # Send to management email (you can add multiple emails)
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['management@wing-kong.com', 'ubaidafzal022@gmail.com'],
                reply_to=['maintenance@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Maintenance escalation alert sent for ticket {ticket.ticket_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to send maintenance escalation alert: {e}")
            return False


    @staticmethod
    def send_contract_for_signature(contract):
        """Send contract to tenant for digital signature (Requirement #16)"""
        try:
            tenant = contract.booking.tenant
            room = contract.booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'contract_number': contract.contract_number,
                'start_date': contract.start_date.strftime('%Y-%m-%d'),
                'end_date': contract.end_date.strftime('%Y-%m-%d'),
                'monthly_rent': contract.monthly_rent,
                'security_deposit': contract.security_deposit,
                'signing_url': f"https://wing-kong.com/contracts/{contract.id}/sign",
                'email_verification_code': contract.email_verification_code,
            }

            subject = f"Tenancy Agreement for Signature - Room {room.room_code}"

            html_content = render_to_string('emails/contract_for_signature.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['contracts@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            # Mark email as verified after sending
            contract.tenant_email_verified = True
            contract.save()

            logger.info(f"Contract sent for signature to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send contract for signature: {e}")
            return False

    @staticmethod
    def send_contract_signed_confirmation(contract):
        """Send confirmation when contract is fully signed"""
        try:
            tenant = contract.booking.tenant
            room = contract.booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'contract_number': contract.contract_number,
                'start_date': contract.start_date.strftime('%Y-%m-%d'),
                'end_date': contract.end_date.strftime('%Y-%m-%d'),
                'monthly_rent': contract.monthly_rent,
                'contract_url': f"https://wing-kong.com/contracts/{contract.id}/view",
                'tenant_portal_url': "https://wing-kong.com/tenant",
            }

            subject = f"Tenancy Agreement Executed - Room {room.room_code}"

            html_content = render_to_string('emails/contract_signed_confirmation.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['contracts@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Contract signed confirmation sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send contract confirmation: {e}")
            return False

    @staticmethod
    def send_move_out_reminder_with_photos(booking):
        """Send move out reminder with photo upload instructions"""
        try:
            tenant = booking.tenant
            room = booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'move_out_date': booking.move_out_date.strftime('%Y-%m-%d'),
                'days_until_move_out': (booking.move_out_date - timezone.now().date()).days,
                'photo_upload_url': f"https://wing-kong.com/bookings/{booking.id}/move-out",
                'cleaning_guidelines_url': "https://wing-kong.com/cleaning-guidelines",
                'deposit_refund_policy_url': "https://wing-kong.com/deposit-policy",
            }

            subject = f"Move Out Reminder - Photo Upload Required - {room.room_code}"

            html_content = render_to_string('emails/move_out_photo_reminder.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['moveout@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Move out photo reminder sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send move out photo reminder: {e}")
            return False

    @staticmethod
    def send_move_out_inspection_result(booking):
        """Send move out inspection results to tenant"""
        try:
            tenant = booking.tenant
            room = booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'clean_status': booking.get_move_out_clean_status_display(),
                'inspection_notes': booking.move_out_inspection_notes,
                'refund_amount': booking.refund_amount,
                'original_deposit': booking.deposit_paid,
                'deductions': booking.deposit_paid - booking.refund_amount,
                'inspection_date': booking.move_out_inspection_date.strftime('%Y-%m-%d'),
                'refund_timeline': '7-10 business days',
            }

            subject = f"Move Out Inspection Results - {room.room_code}"

            html_content = render_to_string('emails/move_out_inspection_result.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['moveout@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Move out inspection results sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send move out inspection results: {e}")
            return False

    @staticmethod
    def send_refund_confirmation(booking):
        """Send refund confirmation to tenant"""
        try:
            tenant = booking.tenant
            room = booking.room

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'refund_amount': booking.refund_amount,
                'refund_date': booking.refund_issued_date.strftime('%Y-%m-%d'),
                'payment_method': 'Bank Transfer',  # Would come from tenant's payment info
                'receipt_url': f"https://wing-kong.com/bookings/{booking.id}/refund-receipt",
            }

            subject = f"Refund Processed - HK$ {booking.refund_amount} - {room.room_code}"

            html_content = render_to_string('emails/refund_confirmation.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['ubaidafzal022@gmail.com'],  # Replace with tenant.user.email
                reply_to=['accounts@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Refund confirmation sent to {tenant.full_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send refund confirmation: {e}")
            return False