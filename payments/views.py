from datetime import timedelta

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils import timezone

from notifications.services import EmailService
from payments.models import Payment


@login_required
@user_passes_test(lambda u: u.is_staff)
def payment_proof_dashboard(request):
    """Staff dashboard for payment proof verification"""
    # Payments needing verification
    pending_payments = Payment.objects.filter(
        proof_status='pending_review',
        proof_of_payment__isnull=False
    ).select_related('booking__tenant', 'booking__room').order_by('payment_date')

    # Recently verified payments
    recent_verified = Payment.objects.filter(
        proof_status='verified',
        proof_verified_date__gte=timezone.now() - timedelta(days=1)
    ).select_related('booking__tenant', 'booking__room').order_by('-proof_verified_date')

    # Statistics
    total_pending = pending_payments.count()
    total_verified_today = Payment.objects.filter(
        proof_status='verified',
        proof_verified_date__date=timezone.now().date()
    ).count()

    context = {
        'pending_payments': pending_payments,
        'recent_verified': recent_verified,
        'total_pending': total_pending,
        'total_verified_today': total_verified_today,
    }
    return render(request, 'payments/proof_dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def payment_proof_detail(request, payment_id):
    """Detailed view of payment proof for verification"""
    payment = get_object_or_404(Payment, id=payment_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')

        if action == 'verify':
            payment.verify_payment_proof(request.user, notes)
            return JsonResponse({'success': True, 'message': 'Payment verified successfully'})

        elif action == 'reject':
            payment.reject_payment_proof(request.user, notes)
            return JsonResponse({'success': True, 'message': 'Payment proof rejected'})

        elif action == 'clarify':
            payment.request_clarification(request.user, notes)
            return JsonResponse({'success': True, 'message': 'Clarification requested'})

    context = {
        'payment': payment,
        'tenant': payment.booking.tenant,
        'room': payment.booking.room,
    }
    return render(request, 'payments/proof_detail.html', context)


@login_required
def tenant_payment_proof_upload(request, payment_id):
    """Tenant uploads payment proof"""
    payment = get_object_or_404(Payment, id=payment_id, booking__tenant__user=request.user)

    if request.method == 'POST' and 'proof_file' in request.FILES:
        proof_file = request.FILES['proof_file']

        # Save proof file
        payment.proof_of_payment = proof_file
        payment.proof_status = 'pending_review'
        payment.save()

        # Send notification to staff
        EmailService.send_payment_proof_uploaded(payment)

        return JsonResponse({'success': True, 'message': 'Payment proof uploaded successfully'})

    context = {
        'payment': payment,
    }
    return render(request, 'payments/tenant_proof_upload.html', context)