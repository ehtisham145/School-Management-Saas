# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Platform", {"fields": ("is_platform_admin",)}),)
    list_display = ("username", "email", "is_platform_admin", "is_staff", "is_active")
    search_fields = ("username", "email")
