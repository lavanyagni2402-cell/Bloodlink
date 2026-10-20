# Django admin panel: open http://127.0.0.1:8000/admin and log in as admin / admin123

from django.contrib import admin

from .models import BloodRequest, Donor, DonorResponse


@admin.action(description="Mark selected donors as verified")
def verify_donors(modeladmin, request, queryset):
    queryset.update(is_verified=True)


class DonorAdmin(admin.ModelAdmin):
    list_display = ["full_name", "blood_group", "city", "phone", "is_available", "is_verified", "last_donation"]
    list_filter = ["blood_group", "city", "is_verified", "is_available"]
    search_fields = ["full_name", "city", "phone"]
    actions = [verify_donors]


class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ["patient_name", "blood_group", "units_needed", "hospital", "city", "urgency", "status", "needed_by"]
    list_filter = ["status", "urgency", "blood_group", "city"]
    search_fields = ["patient_name", "hospital", "city"]


class DonorResponseAdmin(admin.ModelAdmin):
    list_display = ["donor", "request", "status", "created_at"]
    list_filter = ["status"]


admin.site.register(Donor, DonorAdmin)
admin.site.register(BloodRequest, BloodRequestAdmin)
admin.site.register(DonorResponse, DonorResponseAdmin)

admin.site.site_header = "BloodLink Admin"
