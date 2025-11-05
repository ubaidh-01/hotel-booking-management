import logging
from datetime import timedelta
from django.db import models
from django.utils import timezone
from bookings.models import Booking
import uuid


logger = logging.getLogger(__name__)


class Payment(models.Model):
    PAYMENT_TYPES = [
        ('deposit', 'Deposit'),
        ('rent', 'Rent'),
        ('security_deposit', 'Security Deposit'),
        ('stamp_duty', 'Stamp Duty'),
        ('utility', 'Utility Bill'),
        ('late_fee', 'Late Fee'),
        ('refund', 'Refund'),
    ]

    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # Payment Identification
    receipt_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)

    # Payment Details
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    # Dates
    payment_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)

    # Reference & Proof
    bank_reference = models.CharField(max_length=200, blank=True)
    proof_of_payment = models.FileField(upload_to='payment_proofs/', null=True, blank=True)

    # For rent payments
    rent_month = models.DateField(null=True, blank=True)  # Which month's rent
    is_rent_paid = models.BooleanField(default=False)

    # Late fee tracking
    late_fee_days = models.IntegerField(default=0)
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    receipt_generated = models.BooleanField(default=False)
    receipt_generated_date = models.DateTimeField(null=True, blank=True)
    receipt_pdf = models.FileField(upload_to='receipts/', null=True, blank=True)

    proof_verified = models.BooleanField(default=False)
    proof_verified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    proof_verified_date = models.DateTimeField(null=True, blank=True)
    proof_verification_notes = models.TextField(blank=True)
    proof_status = models.CharField(
        max_length=20,
        choices=[
            ('pending_review', 'Pending Review'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
            ('needs_clarification', 'Needs Clarification'),
        ],
        default='pending_review'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.amount} - {self.get_payment_type_display()}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCPT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    # ADD THESE METHODS:
    def generate_receipt_pdf(self):
        """Generate PDF receipt for payment"""
        try:
            from weasyprint import HTML
            from django.template.loader import render_to_string
            from django.core.files.base import ContentFile

            context = {
                'payment': self,
                'tenant': self.booking.tenant,
                'room': self.booking.room,
                'today': timezone.now().date(),
            }

            html_string = render_to_string('payments/receipt_pdf.html', context)
            pdf_file = HTML(string=html_string).write_pdf()

            # Save PDF file
            filename = f"receipt_{self.receipt_number}_{timezone.now().strftime('%Y%m%d')}.pdf"
            self.receipt_pdf.save(filename, ContentFile(pdf_file), save=False)

            self.receipt_generated = True
            self.receipt_generated_date = timezone.now()
            self.save()

            logger.info(f"Receipt generated for payment {self.receipt_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate receipt for payment {self.id}: {e}")
            return False

    def send_receipt_email(self):
        from notifications.services import EmailService

        """Send receipt email to tenant"""
        try:
            success = EmailService.send_payment_receipt(self)
            if success:
                logger.info(f"Receipt email sent for payment {self.receipt_number}")
            return success
        except Exception as e:
            logger.error(f"Failed to send receipt email for payment {self.id}: {e}")
            return False

    def verify_payment_proof(self, verified_by, notes=""):
        """Verify payment proof and update status"""
        self.proof_verified = True
        self.proof_verified_by = verified_by
        self.proof_verified_date = timezone.now()
        self.proof_status = 'verified'
        self.proof_verification_notes = notes
        self.status = 'completed'  # Mark payment as completed
        self.save()

        # Generate receipt automatically
        self.generate_receipt_pdf()
        self.send_receipt_email()

        logger.info(f"Payment proof verified for {self.receipt_number} by {verified_by.username}")
        return True

    def reject_payment_proof(self, verified_by, rejection_reason):
        from notifications.services import EmailService

        """Reject payment proof and notify tenant"""
        self.proof_verified = False
        self.proof_verified_by = verified_by
        self.proof_verified_date = timezone.now()
        self.proof_status = 'rejected'
        self.proof_verification_notes = rejection_reason
        self.save()

        # Send rejection notification to tenant
        EmailService.send_payment_proof_rejected(self, rejection_reason)

        logger.info(f"Payment proof rejected for {self.receipt_number}")
        return True

    def request_clarification(self, verified_by, clarification_request):
        from notifications.services import EmailService

        """Request clarification on payment proof"""
        self.proof_status = 'needs_clarification'
        self.proof_verified_by = verified_by
        self.proof_verified_date = timezone.now()
        self.proof_verification_notes = clarification_request
        self.save()

        # Send clarification request to tenant
        EmailService.send_payment_proof_clarification(self, clarification_request)

        logger.info(f"Clarification requested for payment {self.receipt_number}")
        return True

    @property
    def needs_proof_verification(self):
        """Check if payment proof needs verification"""
        return (self.proof_of_payment and
                self.status == 'pending' and
                self.proof_status == 'pending_review')


class UtilityBill(models.Model):
    property_obj = models.ForeignKey('properties.Property', on_delete=models.CASCADE)
    bill_type = models.CharField(max_length=20, choices=[
        ('electricity', 'Electricity'),
        ('water', 'Water'),
        ('gas', 'Gas'),
        ('internet', 'Internet'),
    ])
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bill_date = models.DateField()
    due_date = models.DateField()
    bill_photo = models.FileField(upload_to='utility_bills/', null=True, blank=True)
    is_allocated = models.BooleanField(default=False)
    allocation_date = models.DateTimeField(null=True, blank=True)
    total_allocated_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # For pro-rata calculation
    total_tenants = models.IntegerField(default=1)
    is_settled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_bill_type_display()} - {self.property_obj.name} - {self.bill_date}"

    def calculate_pro_rata_shares(self):
        """Calculate pro-rata shares for all active tenants during bill period"""
        from bookings.models import Booking
        from django.db.models import Q

        active_bookings = Booking.objects.filter(
            room__property=self.property_obj,
            status='active',
            move_in_date__lte=self.due_date,
            move_out_date__gte=self.bill_date
        ).select_related('tenant', 'room')

        total_share_days = 0
        tenant_shares = []

        for booking in active_bookings:
            # Calculate days tenant was responsible for this bill
            bill_start = max(booking.move_in_date, self.bill_date)
            bill_end = min(booking.move_out_date, self.due_date)
            tenant_days = (bill_end - bill_start).days + 1

            if tenant_days > 0:
                total_share_days += tenant_days
                tenant_shares.append({
                    'booking': booking,
                    'tenant': booking.tenant,
                    'room': booking.room,
                    'days': tenant_days,
                    'share_amount': 0,  # Will calculate after total
                    'is_paid': False
                })

        # Calculate each tenant's share amount
        for tenant_share in tenant_shares:
            if total_share_days > 0:
                tenant_share['share_amount'] = (self.bill_amount / total_share_days) * tenant_share['days']

        return tenant_shares, total_share_days

    def create_utility_payments(self):
        """Create utility payment records for all tenants"""
        tenant_shares, total_days = self.calculate_pro_rata_shares()

        created_payments = []
        for share in tenant_shares:
            # Check if payment already exists
            existing_payment = Payment.objects.filter(
                booking=share['booking'],
                payment_type='utility',
                payment_date=self.due_date,
                amount=share['share_amount']
            ).exists()

            if not existing_payment and share['share_amount'] > 0:
                payment = Payment.objects.create(
                    booking=share['booking'],
                    payment_type='utility',
                    amount=share['share_amount'],
                    payment_date=self.due_date,
                    due_date=self.due_date + timedelta(days=14),  # 14 days to pay
                    status='pending',
                    receipt_number=f"UTIL-{self.id}-{share['booking'].id}"
                )
                created_payments.append(payment)

        # Update bill allocation status
        if created_payments:
            self.is_allocated = True
            self.allocation_date = timezone.now()
            self.total_allocated_amount = sum(p.amount for p in created_payments)
            self.save()

        return created_payments

    @property
    def allocated_percentage(self):
        """Percentage of bill amount allocated to tenants"""
        if self.bill_amount > 0:
            return (self.total_allocated_amount / self.bill_amount) * 100
        return 0


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Expense Categories"


class Expense(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('cheque', 'Cheque'),
    ]

    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateField()
    receipt_photo = models.FileField(upload_to='expense_receipts/', null=True, blank=True)

    # Optional relationships
    maintenance_ticket = models.ForeignKey('maintenance.MaintenanceTicket', null=True, blank=True,
                                           on_delete=models.SET_NULL)
    property_obj = models.ForeignKey('properties.Property', null=True, blank=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Expense: {self.category.name} - HK${self.amount} - {self.payment_date}"

    class Meta:
        ordering = ['-payment_date']
