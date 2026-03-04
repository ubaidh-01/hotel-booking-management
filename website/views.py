from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.contrib import messages
from django.core.exceptions import ValidationError
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

    # Get current booking (active or confirmed)
    current_booking = Booking.objects.filter(
        tenant=tenant,
        status__in=['active', 'confirmed']
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

        # Allow requests for both active and confirmed bookings
        current_booking = Booking.objects.filter(
            tenant=tenant,
            status__in=['active', 'confirmed']
        ).first()

        if not current_booking:
            messages.error(request, 'You do not have an active or confirmed booking to report maintenance for.')
            return redirect('website:tenant_maintenance')

        if title and description:
            try:
                ticket = MaintenanceTicket.objects.create(
                    tenant=tenant,
                    room=current_booking.room,
                    title=title,
                    description=description,
                    priority=priority,
                )

                # Handle photo uploads properly
                if 'photos' in request.FILES:
                    from django.core.files.storage import FileSystemStorage
                    import os
                    fs = FileSystemStorage()
                    saved_photos = []
                    
                    for photo in request.FILES.getlist('photos'):
                        # Generate unique filename to avoid collisions
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"maintenance/T{ticket.id}_{timestamp}_{photo.name}"
                        name = fs.save(filename, photo)
                        saved_photos.append(name)
                    
                    ticket.photos = saved_photos
                    ticket.save()

                messages.success(request, 'Maintenance request submitted successfully.')
                return redirect('website:tenant_maintenance')
            except Exception as e:
                messages.error(request, f'Failed to create maintenance request: {str(e)}')
        else:
            messages.error(request, 'Please provide both a title and description for your request.')

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

            # Check min stay duration
            if config and duration_months < config.min_stay_months:
                messages.error(request, f'Minimum stay duration is {config.min_stay_months} months.')
                return redirect('website:start_booking', room_code=room_code)

            # Create booking instance
            booking = Booking(
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

            # Calculate total deposit and run full validation
            booking.calculate_total_deposit()
            booking.full_clean()
            booking.save()

            # Redirect to payment page with deposit amount
            return redirect('website:booking_payment', booking_id=booking.id)

        except ValidationError as e:
            # Handle Django validation errors
            if hasattr(e, 'message_dict'):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                for error in e.messages:
                    messages.error(request, error)
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

            # Send booking confirmation email
            EmailService.send_booking_confirmation(booking)

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


# ===== TENANT REGISTRATION & LOGIN =====

def tenant_register(request):
    """Tenant self-registration - creates User + Tenant profile"""
    from django.contrib.auth.models import User
    from django.contrib.auth import login

    if request.user.is_authenticated:
        return redirect('website:tenant_dashboard')

    config = WebsiteConfig.objects.first()

    if request.method == 'POST':
        # Collect registration information
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        whatsapp = request.POST.get('whatsapp_number', '').strip()
        nationality = request.POST.get('nationality', '').strip()
        date_of_birth = request.POST.get('date_of_birth', '').strip()
        gender = request.POST.get('gender', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        # Validation
        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        if not phone:
            errors.append('Phone number is required.')
        if not nationality:
            errors.append('Nationality is required.')
        if not date_of_birth:
            errors.append('Date of birth is required.')
        if not gender:
            errors.append('Gender is required.')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != password_confirm:
            errors.append('Passwords do not match.')
        if User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'website/tenant/register.html', {
                'config': config,
                'form_data': request.POST,
            })

        try:
            # Create Django User
            username = email  # Use email as username
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name.split()[0] if full_name else '',
                last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
            )

            # Create Tenant profile
            from datetime import datetime as dt
            tenant = Tenant.objects.create(
                user=user,
                full_name=full_name,
                phone_number=phone,
                whatsapp_number=whatsapp or phone,
                nationality=nationality,
                date_of_birth=dt.strptime(date_of_birth, '%Y-%m-%d').date(),
                gender=gender,
            )

            # Auto-login
            login(request, user)
            messages.success(request, f'Welcome, {full_name}! Your account has been created successfully.')
            return redirect('website:tenant_dashboard')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'website/tenant/register.html', {
                'config': config,
                'form_data': request.POST,
            })

    return render(request, 'website/tenant/register.html', {'config': config})


def tenant_login_view(request):
    """Custom tenant login page"""
    from django.contrib.auth import authenticate, login

    if request.user.is_authenticated:
        return redirect('website:tenant_dashboard')

    config = WebsiteConfig.objects.first()

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Try to authenticate with email as username
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            # Check if user is staff → redirect to admin
            if user.is_staff:
                return redirect('reports:dashboard')
            return redirect('website:tenant_dashboard')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'website/tenant/login.html', {'config': config})


def tenant_logout_view(request):
    """Tenant logout"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('website:home')


# ===== CONTRACT RENEWAL FLOW =====

@tenant_login_required
def tenant_renewal_response(request, contract_id):
    """Handle tenant's response to contract renewal offer"""
    contract = get_object_or_404(
        Contract,
        id=contract_id,
        booking__tenant__user=request.user,
        status='signed'
    )

    config = WebsiteConfig.objects.first()

    if request.method == 'POST':
        response = request.POST.get('renewal_response')

        if response == 'yes':
            # Tenant wants to renew
            new_duration = int(request.POST.get('new_duration_months', 3))
            new_end_date = contract.end_date + timedelta(days=30 * new_duration)

            # Create new booking for renewal
            old_booking = contract.booking
            new_booking = Booking.objects.create(
                tenant=old_booking.tenant,
                room=old_booking.room,
                move_in_date=contract.end_date,
                move_out_date=new_end_date,
                duration_months=new_duration,
                monthly_rent=old_booking.monthly_rent,
                status='pending',
                payment_status='pending',
            )

            # Create new contract (draft)
            new_contract = Contract.objects.create(
                booking=new_booking,
                start_date=contract.end_date,
                end_date=new_end_date,
                monthly_rent=old_booking.monthly_rent,
                security_deposit=contract.security_deposit,
                status='draft',
            )

            # Update old contract renewal status
            contract.renewal_status = 'renewed'
            contract.save()

            # Send renewal agreement email
            EmailService.send_contract_for_signature(new_contract)

            messages.success(request, 'Thank you! Your renewal contract has been created. Please check your email to sign the new agreement.')
            return redirect('website:tenant_contract_view', contract_id=new_contract.id)

        elif response == 'no':
            # Tenant declines renewal
            contract.renewal_status = 'declined'
            contract.save()

            messages.info(request, 'Thank you for letting us know. We wish you well!')
            return redirect('website:tenant_dashboard')

    context = {
        'config': config,
        'contract': contract,
        'booking': contract.booking,
        'room': contract.booking.room,
    }
    return render(request, 'website/tenant/renewal_response.html', context)


# ===== CUSTOMER SELF-FILL CONTRACT =====

@tenant_login_required
def tenant_contract_fill(request, contract_id):
    """Tenant fills in their own details on the flatshare agreement"""
    contract = get_object_or_404(
        Contract,
        id=contract_id,
        booking__tenant__user=request.user,
    )

    tenant = request.user.tenant
    config = WebsiteConfig.objects.first()

    if request.method == 'POST':
        # Update tenant details from form
        tenant.full_name = request.POST.get('full_name', tenant.full_name)
        tenant.phone_number = request.POST.get('phone_number', tenant.phone_number)
        tenant.whatsapp_number = request.POST.get('whatsapp_number', tenant.whatsapp_number)
        tenant.emergency_contact_name = request.POST.get('emergency_contact_name', tenant.emergency_contact_name)
        tenant.emergency_contact_phone = request.POST.get('emergency_contact_phone', tenant.emergency_contact_phone)

        # Update user email
        new_email = request.POST.get('email', '').strip()
        if new_email and new_email != tenant.user.email:
            tenant.user.email = new_email
            tenant.user.save()

        # Update HKID/Passport on booking
        hkid = request.POST.get('hkid_number', '').strip()
        passport = request.POST.get('passport_number', '').strip()
        if hkid:
            tenant.hkid_number = hkid
        if passport:
            tenant.passport_number = passport

        tenant.save()

        # Mark contract as ready for signing if it's still draft
        if contract.status == 'draft':
            contract.status = 'sent'
            contract.save()
            # Send contract for signature
            contract.send_for_tenant_signature()

        messages.success(request, 'Your details have been updated. Please proceed to sign the contract.')
        return redirect('website:tenant_contract_view', contract_id=contract.id)

    context = {
        'config': config,
        'contract': contract,
        'tenant': tenant,
        'booking': contract.booking,
        'room': contract.booking.room,
    }
    return render(request, 'website/tenant/contract_fill.html', context)