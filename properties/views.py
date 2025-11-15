from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test

from properties.models import Room


def staff_required(view_func):
    """Decorator that checks if user is staff member"""
    decorated_view_func = login_required(user_passes_test(
        lambda u: u.is_staff,
        login_url='/admin/login/'
    )(view_func))
    return decorated_view_func


@staff_required
def crm_room_detail(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)

    # Get current booking if any
    current_booking = room.get_current_booking()

    # Get payment history for this room
    from payments.models import Payment
    payment_history = Payment.objects.filter(
        booking__room=room
    ).select_related('booking__tenant').order_by('-payment_date')[:10]

    # Get maintenance tickets
    from maintenance.models import MaintenanceTicket
    maintenance_tickets = MaintenanceTicket.objects.filter(
        room=room
    ).select_related('tenant').order_by('-reported_date')[:5]

    context = {
        'room': room,
        'current_booking': current_booking,
        'payment_history': payment_history,
        'maintenance_tickets': maintenance_tickets,
        'title': f'Room {room.room_code} - CRM'
    }
    return render(request, 'properties/room_details.html', context)


@staff_required
def crm_room_list(request):
    """CRM room list - all rooms with status"""
    rooms = Room.objects.all().select_related('property').order_by('room_code')

    # Calculate room statistics
    total_rooms = rooms.count()
    available_rooms = rooms.filter(status='available').count()
    occupied_rooms = rooms.filter(status='occupied').count()
    reserved_rooms = rooms.filter(status='reserved').count()
    maintenance_rooms = rooms.filter(status='maintenance').count()

    context = {
        'rooms': rooms,
        'title': 'All Rooms - CRM',
        'stats': {
            'total_rooms': total_rooms,
            'available_rooms': available_rooms,
            'occupied_rooms': occupied_rooms,
            'reserved_rooms': reserved_rooms,
            'maintenance_rooms': maintenance_rooms,
        }
    }
    return render(request, 'properties/crm_room_list.html', context)