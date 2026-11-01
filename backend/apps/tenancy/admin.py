from django.contrib import admin

from apps.tenancy.models import Membership, School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_ar", "code", "is_active")
    search_fields = ("name_en", "name_ar", "code")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "role", "status")
    list_filter = ("school", "role", "status")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user", "school")
