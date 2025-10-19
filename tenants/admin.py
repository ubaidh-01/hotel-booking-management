from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Tenant


class TenantInline(admin.StackedInline):
    model = Tenant
    can_delete = False
    verbose_name_plural = 'Tenant Profile'
    fields = ('full_name', 'hkid_number', 'passport_number', 'nationality',
              'date_of_birth', 'gender', 'phone_number', 'whatsapp_number',
              'emergency_contact_name', 'emergency_contact_phone',
              'resume', 'job_search_status')


class CustomUserAdmin(UserAdmin):
    inlines = (TenantInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_tenant_name', 'is_staff')

    def get_tenant_name(self, obj):
        if hasattr(obj, 'tenant'):
            return obj.tenant.full_name
        return "No tenant profile"

    get_tenant_name.short_description = 'Tenant Name'


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'hkid_number', 'nationality', 'phone_number', 'created_at']
    list_filter = ['nationality', 'gender', 'job_search_status', 'created_at']
    search_fields = ['full_name', 'hkid_number', 'passport_number', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'full_name', 'hkid_number', 'passport_number',
                       'nationality', 'date_of_birth', 'gender')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'whatsapp_number', 'emergency_contact_name', 'emergency_contact_phone')
        }),
        ('Job Related', {
            'fields': ('resume', 'job_search_status'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)