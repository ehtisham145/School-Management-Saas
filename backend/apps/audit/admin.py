from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Read-only: the audit log is append-only for everyone."""

    list_display = ("created_at", "action", "actor_label", "target_label", "ip_address")
    list_filter = ("action", "target_type")
    search_fields = ("actor_label", "target_label")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
