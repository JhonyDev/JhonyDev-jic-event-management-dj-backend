from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import CustomUser

# Make sure we're not registering the default User model
User = get_user_model()

# Unregister the default User admin if it exists
if hasattr(admin.site, '_registry'):
    from django.contrib.auth.models import User as DefaultUser
    if DefaultUser in admin.site._registry:
        admin.site.unregister(DefaultUser)


class CustomUserAdmin(UserAdmin):
    # Fields to display in the admin list view
    list_display = ('email', 'first_name', 'last_name', 'username', 'is_active', 'is_staff', 'date_joined')

    # Fields to use for searching users
    search_fields = ('email', 'first_name', 'last_name', 'username')

    # Filters to show in the admin sidebar
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')

    # Order by email (since that's our USERNAME_FIELD)
    ordering = ('email',)

    # Fields to display in the user detail/edit form
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'username', 'profile_image')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    # Fields for adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    # Use email as the username field
    filter_horizontal = ('groups', 'user_permissions')

    # Read-only fields
    readonly_fields = ('date_joined', 'last_login')


# Register the CustomUser model with the admin
admin.site.register(CustomUser, CustomUserAdmin)
