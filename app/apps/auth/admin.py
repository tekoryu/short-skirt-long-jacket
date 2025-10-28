from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    User, PermissionGroup, ResourcePermission, UserPermission,
    GroupPermission, UserGroup, PermissionLog
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin with additional fields and permission management.
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'department', 'is_active', 'is_verified', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'department', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'department')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Professional info', {'fields': ('department', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(PermissionGroup)
class PermissionGroupAdmin(admin.ModelAdmin):
    """
    Admin for permission groups.
    """
    list_display = ('name', 'description', 'is_active', 'created_at', 'user_count')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def user_count(self, obj):
        return obj.group_users.filter(is_active=True).count()
    user_count.short_description = 'Active Users'


@admin.register(ResourcePermission)
class ResourcePermissionAdmin(admin.ModelAdmin):
    """
    Admin for resource permissions.
    """
    list_display = ('name', 'codename', 'permission_type', 'resource_name', 'is_active', 'created_at')
    list_filter = ('permission_type', 'is_active', 'created_at')
    search_fields = ('name', 'codename', 'resource_name', 'description')
    ordering = ('resource_name', 'permission_type')
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related()


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    """
    Admin for user permissions.
    """
    list_display = ('user', 'resource_permission', 'granted_by', 'granted_at', 'expires_at', 'is_active')
    list_filter = ('is_active', 'granted_at', 'expires_at', 'resource_permission__permission_type')
    search_fields = ('user__email', 'user__username', 'resource_permission__name', 'granted_by__email')
    ordering = ('-granted_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'resource_permission', 'granted_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # New permission
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GroupPermission)
class GroupPermissionAdmin(admin.ModelAdmin):
    """
    Admin for group permissions.
    """
    list_display = ('group', 'resource_permission', 'created_at')
    list_filter = ('created_at', 'resource_permission__permission_type')
    search_fields = ('group__name', 'resource_permission__name')
    ordering = ('group__name', 'resource_permission__resource_name')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'resource_permission')


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    """
    Admin for user groups.
    """
    list_display = ('user', 'group', 'added_by', 'added_at', 'is_active')
    list_filter = ('is_active', 'added_at', 'group')
    search_fields = ('user__email', 'user__username', 'group__name', 'added_by__email')
    ordering = ('-added_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'group', 'added_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # New group assignment
            obj.added_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PermissionLog)
class PermissionLogAdmin(admin.ModelAdmin):
    """
    Admin for permission logs (read-only).
    """
    list_display = ('user', 'action', 'resource', 'ip_address', 'created_at')
    list_filter = ('action', 'created_at', 'user')
    search_fields = ('user__email', 'user__username', 'resource', 'details')
    ordering = ('-created_at',)
    readonly_fields = ('user', 'action', 'resource', 'details', 'ip_address', 'user_agent', 'created_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Custom admin site configuration
admin.site.site_header = "Auth System Administration"
admin.site.site_title = "Auth Admin"
admin.site.index_title = "Permission Management"