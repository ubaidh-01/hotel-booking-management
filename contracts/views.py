from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from reports.views import staff_required
from .models import Contract


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