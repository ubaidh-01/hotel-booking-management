import logging

from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from notifications.services import EmailService
from notifications.whatsapp_service import WhatsAppService
from reports.views import staff_required
from .models import Contract
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json


logger = logging.getLogger(__name__)


@staff_required
@require_POST
def switch_to_permanent_room(request, contract_id):
    """Switch from temporary to permanent room"""
    contract = get_object_or_404(Contract, id=contract_id)

    if contract.switch_to_permanent_room():
        messages.success(request,
                         f"Successfully switched {contract.booking.tenant.full_name} to permanent room {contract.temporary_room.room_code}")
    else:
        messages.error(request, "Failed to switch rooms. Please check the contract details.")

    return redirect('reports:temporary_stay')


def contract_signing_page(request, contract_id):
    """Page for tenants to sign contracts digitally"""
    contract = get_object_or_404(Contract, id=contract_id)

    # Verify access (in real implementation, use proper authentication)
    if request.method == 'POST':
        verification_code = request.POST.get('verification_code')
        if verification_code == contract.email_verification_code:
            contract.tenant_email_verified = True
            contract.save()

    context = {
        'contract': contract,
        'tenant': contract.booking.tenant,
        'room': contract.booking.room,
        'email_verified': contract.tenant_email_verified,
        'whatsapp_verified': contract.tenant_whatsapp_verified,
    }
    return render(request, 'contracts/signing_page.html', context)


@csrf_exempt
def save_tenant_signature(request, contract_id):
    """Save tenant's digital signature"""
    if request.method == 'POST':
        contract = get_object_or_404(Contract, id=contract_id)

        try:
            data = json.loads(request.body)
            signature_data = data.get('signature')

            if signature_data:
                contract.digital_signature_tenant = signature_data
                contract.tenant_signed_date = timezone.now()
                contract.save()

                # Generate PDF version
                contract.generate_contract_pdf()

                # Send confirmation
                EmailService.send_contract_signed_confirmation(contract)
                WhatsAppService.send_contract_signed_confirmation(contract)

                return JsonResponse({'success': True, 'message': 'Signature saved successfully'})

        except Exception as e:
            logger.error(f"Failed to save signature: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def staff_sign_contract(request, contract_id):
    """Staff interface to sign contract"""
    contract = get_object_or_404(Contract, id=contract_id)

    if request.method == 'POST' and request.user.is_staff:
        signature_data = request.POST.get('signature')

        if signature_data:
            contract.digital_signature_staff = signature_data
            contract.staff_signed_date = timezone.now()
            contract.staff_signed_by = request.user
            contract.status = 'signed'
            contract.save()

            # Update booking status
            booking = contract.booking
            booking.status = 'confirmed'
            booking.save()

            return redirect('contracts:contract_detail', contract_id=contract.id)

    context = {
        'contract': contract,
        'staff_member': request.user,
    }
    return render(request, 'contracts/staff_signing.html', context)