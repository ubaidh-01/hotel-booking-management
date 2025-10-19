from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class Tenant(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    # Personal Information
    full_name = models.CharField(max_length=200)
    hkid_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        validators=[RegexValidator(regex='^[A-Z]{1,2}[0-9]{6}\\([0-9A]\\)$', message='Enter valid HKID format')]
    )
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    nationality = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    # Contact Information
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    # Job-related (for your tccl-hk.com integration)
    resume = models.FileField(upload_to='tenant_resumes/', null=True, blank=True)
    job_search_status = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} - {self.hkid_number or self.passport_number}"

    @property
    def identifier(self):
        return self.hkid_number or self.passport_number
