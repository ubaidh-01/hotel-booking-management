import logging
from twilio.rest import Client
from django.conf import settings
import random

logger = logging.getLogger(__name__)


class WhatsAppService:
    @staticmethod
    def send_verification_code(contract):
        """Send WhatsApp verification code (Requirement #18)"""
        try:
            # Initialize Twilio client (you'll need to set up Twilio)
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

            tenant = contract.booking.tenant
            verification_code = contract.whatsapp_verification_code

            message = f"""
🏠 *Wing Kong Property Management - Verification*

Hello {tenant.full_name},

Your verification code for contract signing is: *{verification_code}*

This code verifies your WhatsApp number for your tenancy agreement.

Please enter this code on the contract signing page.

Thank you,
Wing Kong Property Management
            """

            # For now, we'll log instead of actually sending
            # Once you set up Twilio, uncomment the code below:
            """
            message = client.messages.create(
                body=message,
                from_='whatsapp:+14155238886',  # Twilio WhatsApp number
                to=f'whatsapp:{tenant.whatsapp_number}'
            )
            """

            logger.info(f"WhatsApp verification code {verification_code} for {tenant.full_name}")
            logger.info(f"WhatsApp message would be sent to: {tenant.whatsapp_number}")

            # Mark as verified for demo purposes
            contract.tenant_whatsapp_verified = True
            contract.save()

            return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp verification: {e}")
            return False

    @staticmethod
    def send_contract_signed_confirmation(contract):
        """Send confirmation when contract is signed"""
        try:
            tenant = contract.booking.tenant

            message = f"""
✅ *Contract Signed Successfully*

Dear {tenant.full_name},

Your tenancy agreement for Room {contract.booking.room.room_code} has been successfully signed and executed.

*Contract Details:*
• Room: {contract.booking.room.room_code}
• Start Date: {contract.start_date}
• End Date: {contract.end_date}
• Monthly Rent: HK$ {contract.monthly_rent}

You can access your contract anytime through your tenant portal.

Thank you for choosing Wing Kong Property Management!
            """

            logger.info(f"Contract signed confirmation for {tenant.full_name}")
            logger.info(f"WhatsApp message: {message}")

            return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp confirmation: {e}")
            return False