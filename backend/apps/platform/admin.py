from django.contrib import admin

from apps.platform.models import ContactMessage, DemoRequest


class LeadAdmin(admin.ModelAdmin):
    list_filter = ("is_handled", "created_at")
    list_editable = ("is_handled",)
    search_fields = ("name", "school_name", "email")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields if field.name != "is_handled"]


@admin.register(DemoRequest)
class DemoRequestAdmin(LeadAdmin):
    list_display = ("name", "school_name", "email", "phone", "plan", "is_handled", "created_at")


@admin.register(ContactMessage)
class ContactMessageAdmin(LeadAdmin):
    list_display = ("name", "school_name", "email", "is_handled", "created_at")
