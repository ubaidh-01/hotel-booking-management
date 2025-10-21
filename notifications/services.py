from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime, timedelta
import logging

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

    @staticmethod
    def send_late_fee_invoice(payment):
        """Send automatic late fee invoice (Requirement #9b)"""
        try:
            tenant = payment.booking.tenant
            room = payment.booking.room
            today = datetime.now().date()

            days_overdue = (today - payment.due_date).days
            late_fee = days_overdue * 100
            total_amount_due = payment.amount + late_fee

            context = {
                'tenant_name': tenant.full_name,
                'room_code': room.room_code,
                'original_amount': payment.amount,
                'late_fee': late_fee,
                'total_amount_due': total_amount_due,
                'days_overdue': days_overdue,
                'due_date': payment.due_date.strftime('%Y-%m-%d'),
                'invoice_date': today.strftime('%Y-%m-%d'),
                'payment_url': f"https://wing-kong.com/payments/{payment.id}",
            }

            if days_overdue >= 14:
                subject = f"COURT NOTICE: Rent Overdue {days_overdue} Days - {room.room_code}"
            else:
                subject = f"Late Fee Invoice - {room.room_code}"

            html_content = render_to_string('emails/late_fee_invoice.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                # to=[tenant.user.email],
                to=['ubaidafzal022@gmail.com'],
                reply_to=['accounts@wing-kong.com']
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Late fee invoice sent to {tenant.full_name} for {room.room_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to send late fee invoice: {e}")
            return False