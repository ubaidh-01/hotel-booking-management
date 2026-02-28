from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import json

from properties.models import Room, Property, PropertyImage
from bookings.models import Booking
from payments.models import Payment
from maintenance.models import MaintenanceTicket
from contracts.models import Contract
from tenants.models import Tenant
from .models import WebsiteConfig, CustomerInquiry, WebsiteFeedback, JobApplication
from notifications.services import EmailService


# Create your views here.
class HomeView(TemplateView):
    """Website homepage"""
    template_name = 'website/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get website configuration
        config = WebsiteConfig.objects.first()
        if not config:
            config = WebsiteConfig.objects.create(
                site_title="Wing Kong Property Management",
                contact_email="info@wing-kong.com",
                contact_phone="+852 1234 5678",
                address="Hong Kong",
                deposit_amount=2500.00
            )

        # Get featured/available rooms
        featured_rooms = Room.objects.filter(
            status='available'
        ).select_related('property').prefetch_related('room_photos')[:6]

        # Get testimonials
        testimonials = WebsiteFeedback.objects.filter(
            approved=True,
            featured=True,
            feedback_type='testimonial'
        )[:5]

        # Statistics
        total_rooms = Room.objects.count()
        available_rooms = Room.objects.filter(status='available').count()

        context.update({
            'config': config,
            'featured_rooms': featured_rooms,
            'testimonials': testimonials,
            'total_rooms': total_rooms,
            'available_rooms': available_rooms,
        })
        return context


class RoomListView(ListView):
    """List all available rooms"""
    model = Room
    template_name = 'website/room_list.html'
    context_object_name = 'rooms'
    paginate_by = 12

    def get_queryset(self):
        queryset = Room.objects.filter(
            status='available'  # Only available rooms
        ).select_related('property').prefetch_related('room_photos', 'room_videos')

        # Apply filters from GET parameters
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        property_type = self.request.GET.get('property_type')
        has_private_bathroom = self.request.GET.get('private_bathroom')
        has_balcony = self.request.GET.get('balcony')

        if min_price:
            queryset = queryset.filter(monthly_rent__gte=min_price)
        if max_price:
            queryset = queryset.filter(monthly_rent__lte=max_price)
        if property_type:
            queryset = queryset.filter(property__property_type=property_type)
        if has_private_bathroom:
            queryset = queryset.filter(has_private_bathroom=True)
        if has_balcony:
            queryset = queryset.filter(has_balcony=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()

        # Get filter options
        property_types = Property.objects.values_list('property_type', flat=True).distinct()

        context.update({
            'config': config,
            'property_types': property_types,
            'filter_params': self.request.GET,
        })
        return context


class RoomDetailView(DetailView):
    """Individual room detail page"""
    model = Room
    template_name = 'website/room_detail.html'
    context_object_name = 'room'

    def get_object(self):
        # Get room by room_code from URL
        room_code = self.kwargs.get('room_code')
        return get_object_or_404(
            Room.objects.select_related('property')
            .prefetch_related('room_photos', 'room_videos'),
            room_code=room_code
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = self.object
        config = WebsiteConfig.objects.first()

        # Get property images
        property_images = PropertyImage.objects.filter(property=room.property)

        # Check if room is available for specific dates
        check_in = self.request.GET.get('check_in')
        check_out = self.request.GET.get('check_out')

        is_available = True
        if check_in and check_out:
            try:
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

                # Check for overlapping bookings
                overlapping = Booking.objects.filter(
                    room=room,
                    status__in=['confirmed', 'active'],
                    move_in_date__lt=check_out_date,
                    move_out_date__gt=check_in_date
                ).exists()

                is_available = not overlapping
                context['check_in'] = check_in_date
                context['check_out'] = check_out_date

            except ValueError:
                pass

        context.update({
            'config': config,
            'property_images': property_images,
            'is_available': is_available,
            'today': timezone.now().date(),
            'min_date': timezone.now().date() + timedelta(days=1),
            'max_date': timezone.now().date() + timedelta(days=365),
        })
        return context


class AboutView(TemplateView):
    """About us page"""
    template_name = 'website/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context


class ContactView(CreateView):
    """Contact us page with inquiry form"""
    model = CustomerInquiry
    template_name = 'website/contact.html'
    fields = ['name', 'email', 'phone', 'inquiry_type', 'message', 'preferred_contact_method', 'room_code']
    success_url = reverse_lazy('website:contact_thanks')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Thank you for your inquiry. We will contact you soon.')

        # Send notification email
        EmailService.send_inquiry_notification(self.object)

        return response


class ContactThanksView(TemplateView):
    """Thank you page after contact form submission"""
    template_name = 'website/contact_thanks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context


class CareersView(CreateView):
    """Careers page with job application form"""
    model = JobApplication
    template_name = 'website/careers.html'
    fields = ['name', 'email', 'phone', 'desired_position', 'job_type',
              'available_from', 'expected_salary', 'resume', 'cover_letter']
    success_url = reverse_lazy('website:careers_thanks')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Thank you for your application. We will review it soon.')

        # Send notification email
        EmailService.send_job_application_notification(self.object)

        return response


class CareersThanksView(TemplateView):
    """Thank you page after job application"""
    template_name = 'website/careers_thanks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context


class TermsView(TemplateView):
    """Terms and conditions"""
    template_name = 'website/terms.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context


class PrivacyView(TemplateView):
    """Privacy policy"""
    template_name = 'website/privacy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context


# ===== TENANT PORTAL VIEWS =====

def tenant_login_required(view_func):
    """Decorator to ensure user is a tenant"""
    from django.contrib.auth.decorators import login_required

    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        # Check if user has tenant profile
        try:
            tenant = request.user.tenant
        except:
            messages.error(request, 'You need a tenant account to access this page.')
            return redirect('website:home')

        return view_func(request, *args, **kwargs)

    return login_required(_wrapped_view)


@tenant_login_required
def tenant_dashboard(request):
    """Tenant portal dashboard"""
    tenant = request.user.tenant

    # Get current booking
    current_booking = Booking.objects.filter(
        tenant=tenant,
        status='active'
    ).select_related('room', 'room__property').first()

    # Get upcoming payments
    upcoming_payments = Payment.objects.filter(
        booking__tenant=tenant,
        status='pending',
        due_date__gte=timezone.now().date()
    ).select_related('booking__room').order_by('due_date')[:5]

    # Get maintenance tickets
    maintenance_tickets = MaintenanceTicket.objects.filter(
        tenant=tenant
    ).select_related('room').order_by('-reported_date')[:5]

    config = WebsiteConfig.objects.first()

    context = {
        'config': config,
        'tenant': tenant,
        'current_booking': current_booking,
        'upcoming_payments': upcoming_payments,
        'maintenance_tickets': maintenance_tickets,
    }
    return render(request, 'website/tenant/dashboard.html', context)


@tenant_login_required
def tenant_booking_detail(request, booking_id):
    """Tenant view of their booking"""
    booking = get_object_or_404(Booking, id=booking_id, tenant__user=request.user)
    contract = Contract.objects.filter(booking=booking).first()
    payments = Payment.objects.filter(booking=booking).order_by('-payment_date')

    config = WebsiteConfig.objects.first()

    context = {
        'config': config,
        'booking': booking,
        'contract': contract,
        'payments': payments,
    }
    return render(request, 'website/tenant/booking_detail.html', context)


@tenant_login_required
def tenant_payments(request):
    """Tenant payment history"""
    tenant = request.user.tenant
    payments = Payment.objects.filter(
        booking__tenant=tenant
    ).select_related('booking__room').order_by('-payment_date')

    config = WebsiteConfig.objects.first()

    context = {
        'config': config,
        'payments': payments,
    }
    return render(request, 'website/tenant/payments.html', context)


@tenant_login_required
def tenant_maintenance(request):
    """Tenant maintenance request management"""
    tenant = request.user.tenant

    if request.method == 'POST':
        # Handle new maintenance request
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority', 'medium')

        current_booking = Booking.objects.filter(
            tenant=tenant,
            status='active'
        ).first()

        if current_booking and title and description:
            ticket = MaintenanceTicket.objects.create(
                tenant=tenant,
                room=current_booking.room,
                title=title,
                description=description,
                priority=priority,
            )

            # Handle photo uploads
            if 'photos' in request.FILES:
                photos = []
                for photo in request.FILES.getlist('photos'):
                    photos.append(photo.name)
                ticket.photos = photos
                ticket.save()

            messages.success(request, 'Maintenance request submitted successfully.')
            return redirect('website:tenant_maintenance')

    # Get maintenance tickets
    maintenance_tickets = MaintenanceTicket.objects.filter(
        tenant=tenant
    ).select_related('room').order_by('-reported_date')

    config = WebsiteConfig.objects.first()

    context = {
        'config': config,
        'maintenance_tickets': maintenance_tickets,
    }
    return render(request, 'website/tenant/maintenance.html', context)


@tenant_login_required
def tenant_contract_view(request, contract_id):
    """View contract"""
    contract = get_object_or_404(Contract, id=contract_id, booking__tenant__user=request.user)

    config = WebsiteConfig.objects.first()

    context = {
        'config': config,
        'contract': contract,
    }
    return render(request, 'website/tenant/contract_view.html', context)


# ===== BOOKING FLOW =====

@tenant_login_required
def start_booking(request, room_code):
    """Updated booking flow with all required information"""
    room = get_object_or_404(Room, room_code=room_code)
    tenant = request.user.tenant

    # Check if room is actually available
    if room.status != 'available':
        messages.error(request, f'Room {room_code} is not available for booking.')
        return redirect('website:room_detail', room_code=room_code)

    config = WebsiteConfig.objects.first()

    if request.method == 'POST':
        # Collect ALL required information
        move_in_date = request.POST.get('move_in_date')
        move_in_time = request.POST.get('move_in_time')
        duration_months = int(request.POST.get('duration_months', 3))

        # Identity information
        hkid_number = request.POST.get('hkid_number')
        passport_number = request.POST.get('passport_number')

        # Validate at least one ID is provided
        if not hkid_number and not passport_number:
            messages.error(request, 'Please provide either HKID or Passport number.')
            return redirect('website:start_booking', room_code=room_code)

        # Calculate dates
        try:
            move_in = datetime.strptime(move_in_date, '%Y-%m-%d').date()
            move_out = move_in + timedelta(days=30 * duration_months)  # Approximate

            # Create booking with ALL information
            booking = Booking.objects.create(
                tenant=tenant,
                room=room,
                move_in_date=move_in,
                move_in_time=move_in_time,
                move_out_date=move_out,
                duration_months=duration_months,
                monthly_rent=room.monthly_rent,

                # Identity information
                hkid_number=hkid_number,
                passport_number=passport_number,

                # Financials (set default values)
                key_deposit=500,  # Example amount
                security_deposit=room.monthly_rent,  # Typically one month rent
                stamp_duty=0,  # Would calculate based on rent

                status='pending',
                payment_status='pending',
                special_requests=request.POST.get('special_requests', ''),
            )

            # Calculate total deposit
            booking.calculate_total_deposit()
            booking.save()

            # Redirect to payment page with deposit amount
            return redirect('website:booking_payment', booking_id=booking.id)

        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')

    context = {
        'config': config,
        'room': room,
        'today': timezone.now().date(),
        'min_date': timezone.now().date() + timedelta(days=1),
        'deposit_amount': config.deposit_amount,
    }
    return render(request, 'website/booking/start_booking.html', context)


@tenant_login_required
def booking_payment(request, booking_id):
    """Updated payment page with multiple deposit options"""
    booking = get_object_or_404(Booking, id=booking_id, tenant__user=request.user)

    if booking.status != 'pending':
        messages.warning(request, 'This booking is no longer pending.')
        return redirect('website:tenant_dashboard')

    config = WebsiteConfig.objects.first()

    if request.method == 'POST':
        payment_option = request.POST.get('payment_option')

        if payment_option == 'deposit_only':
            amount = config.deposit_amount
            is_deposit = True
            is_non_refundable = True
            receipt_notes = "Deposit only - Non-refundable"

        elif payment_option == 'full_payment':
            # Calculate full amount: deposit + first month rent + key deposit + security deposit + stamp duty
            amount = (config.deposit_amount +
                      booking.monthly_rent +
                      booking.key_deposit +
                      booking.security_deposit +
                      booking.stamp_duty)
            is_deposit = True
            is_non_refundable = True
            receipt_notes = "Full payment including deposit, first month rent, key deposit, security deposit, and stamp duty"

        else:
            messages.error(request, 'Please select a payment option.')
            return redirect('website:booking_payment', booking_id=booking.id)

        payment_method = request.POST.get('payment_method')

        # Create payment
        payment = Payment.objects.create(
            booking=booking,
            payment_type='deposit',
            amount=amount,
            payment_method=payment_method,
            payment_date=timezone.now().date(),
            due_date=timezone.now().date(),
            status='pending',

            # Additional fields
            is_deposit=True,
            is_non_refundable=True if payment_option == 'deposit_only' else False,
            receipt_notes=receipt_notes,
        )

        # Update booking with deposit paid
        booking.deposit_paid = config.deposit_amount
        booking.total_amount_paid = amount
        booking.save()

        if payment_method == 'bank_transfer':
            return redirect('website:payment_proof_upload', payment_id=payment.id)
        else:
            # Mark as completed (for demo)
            payment.verify_payment_proof(request.user, "Auto-verified for demo")

            # Update booking status
            booking.status = 'confirmed'
            booking.payment_status = 'deposit_paid'
            booking.confirmed_date = timezone.now()
            booking.save()

            # Update room status
            booking.update_room_status()

            # Generate detailed receipt
            payment.generate_detailed_receipt()

            messages.success(request, 'Payment successful! Booking confirmed.')
            return redirect('website:booking_confirmation', booking_id=booking.id)

    # Calculate payment amounts
    total_full_payment = (config.deposit_amount +
                          booking.monthly_rent +
                          booking.key_deposit +
                          booking.security_deposit +
                          booking.stamp_duty)

    context = {
        'config': config,
        'booking': booking,
        'deposit_amount': config.deposit_amount,
        'monthly_rent': booking.monthly_rent,
        'key_deposit': booking.key_deposit,
        'security_deposit': booking.security_deposit,
        'stamp_duty': booking.stamp_duty,
        'total_full_payment': total_full_payment,
    }
    return render(request, 'website/booking/payment.html', context)


@tenant_login_required
def payment_proof_upload(request, payment_id):
    """Upload payment proof for bank transfer"""
    payment = get_object_or_404(Payment, id=payment_id, booking__tenant__user=request.user)

    if request.method == 'POST' and 'proof_file' in request.FILES:
        proof_file = request.FILES['proof_file']

        # Save proof file
        payment.proof_of_payment = proof_file
        payment.save()

        # Send notification to staff
        EmailService.send_payment_proof_uploaded(payment)

        messages.success(request, 'Payment proof uploaded. We will verify it shortly.')
        return redirect('website:booking_confirmation', booking_id=payment.booking.id)

    config = WebsiteConfig.objects.first()

    context = {
        'config': config,
        'payment': payment,
        'booking': payment.booking,
    }
    return render(request, 'website/booking/proof_upload.html', context)


@tenant_login_required
def booking_confirmation(request, booking_id):
    """Booking confirmation page"""
    booking = get_object_or_404(Booking, id=booking_id, tenant__user=request.user)

    config = WebsiteConfig.objects.first()

    context = {
        'config': config,
        'booking': booking,
    }
    return render(request, 'website/booking/confirmation.html', context)


# ===== PUBLIC FEEDBACK =====

class SubmitFeedbackView(CreateView):
    """Submit public feedback/testimonial"""
    model = WebsiteFeedback
    template_name = 'website/feedback.html'
    fields = ['name', 'email', 'feedback_type', 'message', 'rating']
    success_url = reverse_lazy('website:feedback_thanks')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context

    def form_valid(self, form):
        # If user is logged in as tenant, link to tenant profile
        if self.request.user.is_authenticated:
            try:
                form.instance.tenant = self.request.user.tenant
            except:
                pass

        response = super().form_valid(form)
        messages.success(self.request, 'Thank you for your feedback!')
        return response


class FeedbackThanksView(TemplateView):
    """Thank you page after feedback submission"""
    template_name = 'website/feedback_thanks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = WebsiteConfig.objects.first()
        context['config'] = config
        return context