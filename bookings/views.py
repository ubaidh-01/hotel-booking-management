from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json

from django.utils import timezone

from bookings.models import Booking
from notifications.services import EmailService


@login_required
def tenant_move_out_portal(request, booking_id):
    """Tenant portal for move out process"""
    booking = get_object_or_404(Booking, id=booking_id, tenant__user=request.user)

    if request.method == 'POST' and 'photos' in request.FILES:
        # Handle photo uploads
        photos = request.FILES.getlist('photos')
        uploaded_urls = []

        for photo in photos:
            # Save photo and get URL (implement your file storage logic)
            # For now, we'll store file names
            uploaded_urls.append(photo.name)

            # In production, you'd save the files properly:
            # from django.core.files.storage import default_storage
            # file_path = default_storage.save(f'move_out_photos/{photo.name}', photo)
            # uploaded_urls.append(default_storage.url(file_path))

        # Update booking with new photos
        current_photos = booking.move_out_photos
        current_photos.extend(uploaded_urls)
        booking.move_out_photos = current_photos
        booking.save()

        return JsonResponse({'success': True, 'photos': uploaded_urls})

    context = {
        'booking': booking,
        'tenant': booking.tenant,
        'room': booking.room,
    }
    return render(request, 'bookings/tenant_move_out.html', context)


@login_required
def staff_move_out_inspection(request, booking_id):
    """Staff interface for move out inspection"""
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST' and request.user.is_staff:
        clean_status = request.POST.get('clean_status')
        inspection_notes = request.POST.get('inspection_notes')
        deductions = request.POST.get('deductions', 0)

        booking.move_out_clean_status = clean_status
        booking.move_out_inspection_notes = inspection_notes
        booking.move_out_inspection_date = timezone.now()
        booking.refund_status = 'processing'

        # Calculate refund amount
        booking.calculate_refund_amount()
        booking.save()

        # Send notification to tenant
        EmailService.send_move_out_inspection_result(booking)

        return redirect('bookings:move_out_inspection', booking_id=booking.id)

    context = {
        'booking': booking,
        'photos': booking.move_out_photos,
    }
    return render(request, 'bookings/staff_move_out_inspection.html', context)


@login_required
def process_refund(request, booking_id):
    """Process refund payment"""
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST' and request.user.is_staff:
        # Process refund logic here
        # This would integrate with your payment system

        booking.refund_status = 'completed'
        booking.refund_issued_date = timezone.now()
        booking.save()

        # Generate refund receipt
        booking.generate_refund_receipt()

        # Send confirmation to tenant
        EmailService.send_refund_confirmation(booking)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request'})