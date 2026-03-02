from .models import Property, Owner, PropertyOwnership, PropertyImage
from django.contrib import admin
from .models import Room, RoomPhoto, RoomVideo
from django.utils.html import format_html



class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ['property', 'image_type', 'is_primary', 'uploaded_at']
    list_filter = ['image_type', 'property']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'property_type', 'total_rooms', 'created_at']
    list_filter = ['property_type', 'created_at']
    search_fields = ['name', 'address']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PropertyImageInline]



class RoomPhotoInline(admin.TabularInline):
    model = RoomPhoto
    extra = 1
    fields = ["image", "preview"]
    readonly_fields = ["preview"]

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 120px; height:auto; border-radius:4px;" />',
                obj.image.url
            )
        return "No Image"

    preview.short_description = "Preview"


class RoomVideoInline(admin.TabularInline):
    model = RoomVideo
    extra = 1
    fields = ["video", "preview"]
    readonly_fields = ["preview"]

    def preview(self, obj):
        if obj.video:
            return format_html(
                '<video width="200" controls>'
                '<source src="{}" type="video/mp4">'
                'Your browser does not support video.'
                '</video>',
                obj.video.url
            )
        return "No Video"

    preview.short_description = "Preview"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['room_code', 'property', 'monthly_rent', 'status', 'current_tenant', 'has_private_bathroom']
    list_filter = ['status', 'property', 'has_private_bathroom', 'has_balcony']
    search_fields = ['room_code', 'property__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'current_tenant_display']
    list_editable = ['status']

    inlines = [RoomPhotoInline, RoomVideoInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('property', 'room_code', 'room_number', 'description')
        }),
        ('Financial', {
            'fields': ('monthly_rent', 'deposit_amount')
        }),
        ('Status & Features', {
            'fields': ('status', 'size_sqft', 'has_private_bathroom', 'has_balcony')
        }),
        ('Current Occupancy', {
            'fields': ('current_tenant_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def current_tenant(self, obj):
        booking = obj.get_current_booking()
        return booking.tenant.full_name if booking else "Available"

    current_tenant.short_description = 'Current Tenant'

    def current_tenant_display(self, obj):
        booking = obj.get_current_booking()
        if booking:
            return f"{booking.tenant.full_name} (Until {booking.move_out_date})"
        return "No current tenant"

    current_tenant_display.short_description = 'Current Tenant'



@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_email', 'phone_number', 'active_properties_count', 'total_rent_owed']
    list_filter = ['created_at']
    search_fields = ['name', 'contact_email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PropertyOwnership)
class PropertyOwnershipAdmin(admin.ModelAdmin):
    list_display = ['owner', 'property_obj', 'monthly_rent_to_owner', 'management_fee', 'contract_start', 'contract_end', 'is_active', 'rent_owed']  # Updated to property_obj
    list_filter = ['is_active', 'contract_start', 'contract_end']
    search_fields = ['owner__name', 'property_obj__name']
    readonly_fields = ['created_at', 'updated_at', 'rent_owed']