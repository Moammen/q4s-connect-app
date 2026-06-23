from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User

    list_display = UserAdmin.list_display + ("role", "is_deleted")
    list_filter  = UserAdmin.list_filter  + ("role", "is_deleted")

    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'all_sites', 'ets_sites', 'is_deleted')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('role', 'all_sites', 'ets_sites', 'is_deleted')}),
    )

    actions = ["soft_delete_users", "restore_users"]

    def soft_delete_users(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f"{count} user(s) soft-deleted.")
    soft_delete_users.short_description = "Soft delete selected users"

    def restore_users(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f"{count} user(s) restored.")
    restore_users.short_description = "Restore selected users"


admin.site.register(User, CustomUserAdmin)
