from django.db import models
import uuid


class WebsiteConfig(models.Model):
    """Configuration for the website"""
    site_title = models.CharField(max_length=200, default="Wing Kong Property Management")
    site_description = models.TextField(blank=True)
    contact_email = models.EmailField(default="info@wing-kong.com")
    contact_phone = models.CharField(max_length=20, default="+852 1234 5678")
    address = models.TextField()
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)

    # Booking settings
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2500.00)
    min_stay_months = models.IntegerField(default=3)
    max_stay_months = models.IntegerField(default=24)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Website Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one configuration exists
        if not self.pk and WebsiteConfig.objects.exists():
            return
        super().save(*args, **kwargs)


class CustomerInquiry(models.Model):
    """Contact form inquiries from website visitors"""
    INQUIRY_TYPES = [
        ('booking', 'Booking Inquiry'),
        ('general', 'General Inquiry'),
        ('maintenance', 'Maintenance Issue'),
        ('job_application', 'Job Application'),
        ('other', 'Other'),
    ]

    inquiry_id = models.CharField(max_length=20, unique=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPES)
    message = models.TextField()
    preferred_contact_method = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('whatsapp', 'WhatsApp'),
    ])

    # Room reference if applicable
    room_code = models.CharField(max_length=10, blank=True, null=True)

    status = models.CharField(max_length=20, choices=[
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('resolved', 'Resolved'),
        ('spam', 'Spam'),
    ], default='new')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Inquiry from {self.name} - {self.get_inquiry_type_display()}"

    def save(self, *args, **kwargs):
        if not self.inquiry_id:
            last_inquiry = CustomerInquiry.objects.order_by('-id').first()
            last_number = int(last_inquiry.inquiry_id.split('-')[1]) if last_inquiry else 0
            self.inquiry_id = f"INQ-{last_number + 1:05d}"
        super().save(*args, **kwargs)


class WebsiteFeedback(models.Model):
    """Customer feedback/testimonials"""
    FEEDBACK_TYPES = [
        ('testimonial', 'Testimonial'),
        ('review', 'Review'),
        ('complaint', 'Complaint'),
        ('suggestion', 'Suggestion'),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    message = models.TextField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)

    # Optional: Link to tenant if they're logged in
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.SET_NULL, null=True, blank=True)

    approved = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback from {self.name} - {self.get_feedback_type_display()}"


class JobApplication(models.Model):
    """Job applications through website"""
    JOB_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('internship', 'Internship'),
    ]

    application_id = models.CharField(max_length=20, unique=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Job preferences
    desired_position = models.CharField(max_length=200)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    available_from = models.DateField()
    expected_salary = models.CharField(max_length=100, blank=True)

    # Documents
    resume = models.FileField(upload_to='job_applications/resumes/')
    cover_letter = models.FileField(upload_to='job_applications/cover_letters/', blank=True)

    # Status
    status = models.CharField(max_length=20, choices=[
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('interview', 'Interview Scheduled'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
    ], default='new')

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job Application: {self.name} - {self.desired_position}"