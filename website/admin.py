from django.contrib import admin
from .models import WebsiteConfig, CustomerInquiry, WebsiteFeedback, JobApplication


@admin.register(WebsiteConfig)
class WebsiteConfigAdmin(admin.ModelAdmin):
    list_display = ['site_title', 'contact_email', 'contact_phone', 'updated_at']

    def has_add_permission(self, request):
        # Only allow one configuration
        return not WebsiteConfig.objects.exists()


@admin.register(CustomerInquiry)
class CustomerInquiryAdmin(admin.ModelAdmin):
    list_display = ['inquiry_id', 'name', 'email', 'inquiry_type', 'status', 'created_at']
    list_filter = ['inquiry_type', 'status', 'created_at']
    search_fields = ['name', 'email', 'message']
    list_editable = ['status']
    readonly_fields = ['inquiry_id', 'created_at', 'updated_at']


@admin.register(WebsiteFeedback)
class WebsiteFeedbackAdmin(admin.ModelAdmin):
    list_display = ['name', 'feedback_type', 'rating', 'approved', 'featured', 'created_at']
    list_filter = ['feedback_type', 'approved', 'featured', 'created_at']
    search_fields = ['name', 'message']
    list_editable = ['approved', 'featured']
    readonly_fields = ['created_at']


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_id', 'name', 'email', 'desired_position', 'job_type', 'status', 'created_at']
    list_filter = ['job_type', 'status', 'created_at']
    search_fields = ['name', 'email', 'desired_position']
    list_editable = ['status']
    readonly_fields = ['application_id', 'created_at', 'updated_at']