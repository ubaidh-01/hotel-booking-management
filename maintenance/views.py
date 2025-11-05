# maintenance/views.py - ADD TENANT VIEWS:

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from bookings.models import Booking
from maintenance.models import MaintenanceTicket
from notifications.services import EmailService


@login_required
def tenant_maintenance_dashboard(request):
    """Tenant portal for viewing maintenance tickets"""
    # Get tenant associated with logged-in user
    try:
        tenant = request.user.tenant
    except:
        return render(request, 'error.html', {'message': 'Tenant profile not found'})

    # Get all maintenance tickets for this tenant
    maintenance_tickets = MaintenanceTicket.objects.filter(
        tenant=tenant
    ).select_related('room').order_by('-reported_date')

    # Statistics
    open_tickets = maintenance_tickets.filter(status__in=['open', 'in_progress'])
    resolved_tickets = maintenance_tickets.filter(status='resolved')

    context = {
        'tickets': maintenance_tickets,
        'open_count': open_tickets.count(),
        'resolved_count': resolved_tickets.count(),
        'total_count': maintenance_tickets.count(),
    }
    return render(request, 'maintenance/tenant_dashboard.html', context)


@login_required
def tenant_ticket_detail(request, ticket_id):
    """Tenant view of specific maintenance ticket"""
    ticket = get_object_or_404(MaintenanceTicket, id=ticket_id, tenant__user=request.user)

    # Get all updates for this ticket
    updates = ticket.updates.all().order_by('-created_at')

    context = {
        'ticket': ticket,
        'updates': updates,
    }
    return render(request, 'maintenance/tenant_ticket_detail.html', context)


@login_required
def create_maintenance_request(request):
    """Tenant creates new maintenance request"""
    if request.method == 'POST':
        try:
            tenant = request.user.tenant
            current_booking = Booking.objects.filter(
                tenant=tenant,
                status='active'
            ).first()

            if not current_booking:
                return JsonResponse({'success': False, 'error': 'No active booking found'})

            ticket = MaintenanceTicket.objects.create(
                tenant=tenant,
                room=current_booking.room,
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                priority=request.POST.get('priority', 'medium'),
            )

            # Handle photo uploads
            if 'photos' in request.FILES:
                photos = []
                for photo in request.FILES.getlist('photos'):
                    # Save photos (implement your file storage)
                    photos.append(photo.name)
                ticket.photos = photos
                ticket.save()

            # Send notification to staff
            EmailService.send_new_maintenance_request(ticket)

            return JsonResponse({'success': True, 'ticket_id': ticket.id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'maintenance/create_request.html')