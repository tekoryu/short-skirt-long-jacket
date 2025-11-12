from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class User(AbstractUser):
    """
    Custom User model extending AbstractUser with additional fields
    for granular permission control.
    """
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.email} ({self.get_full_name() or self.username})"


class PermissionGroup(models.Model):
    """
    Custom permission groups for organizing permissions by functionality.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auth_permission_group'
        verbose_name = 'User Group'
        verbose_name_plural = 'User Groups'
    
    def __str__(self):
        return self.name


class ResourcePermission(models.Model):
    """
    Granular permissions for specific resources (models/views).
    """
    PERMISSION_TYPES = [
        ('view', 'View'),
        ('add', 'Add'),
        ('change', 'Change'),
        ('delete', 'Delete'),
        ('download', 'Download'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]
    
    name = models.CharField(max_length=100)
    codename = models.CharField(max_length=100, unique=True)
    permission_type = models.CharField(max_length=20, choices=PERMISSION_TYPES)
    resource_name = models.CharField(max_length=100)  # e.g., 'cities.city', 'core.settings'
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auth_resource_permission'
        verbose_name = 'Resource Permission'
        verbose_name_plural = 'Resource Permissions'
        unique_together = ['permission_type', 'resource_name']
    
    def __str__(self):
        return f"{self.permission_type} {self.resource_name}"


class UserPermission(models.Model):
    """
    Links users to specific resource permissions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_permissions')
    resource_permission = models.ForeignKey(ResourcePermission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'auth_user_permission'
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
        unique_together = ['user', 'resource_permission']
    
    def __str__(self):
        return f"{self.user.email} - {self.resource_permission}"


class GroupPermission(models.Model):
    """
    Links permission groups to resource permissions.
    """
    group = models.ForeignKey(PermissionGroup, on_delete=models.CASCADE, related_name='group_permissions')
    resource_permission = models.ForeignKey(ResourcePermission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auth_group_permission'
        verbose_name = 'Group-Permission Assignment'
        verbose_name_plural = 'Group-Permission Assignments'
        unique_together = ['group', 'resource_permission']
    
    def __str__(self):
        return f"{self.group.name} - {self.resource_permission}"


class UserGroup(models.Model):
    """
    Links users to permission groups.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_groups')
    group = models.ForeignKey(PermissionGroup, on_delete=models.CASCADE, related_name='group_users')
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_to_groups')
    added_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'auth_user_group'
        verbose_name = 'User Group'
        verbose_name_plural = 'User Groups'
        unique_together = ['user', 'group']
    
    def __str__(self):
        return f"{self.user.email} - {self.group.name}"


class PermissionLog(models.Model):
    """
    Logs permission-related actions for audit purposes.
    """
    ACTION_TYPES = [
        ('granted', 'Permission Granted'),
        ('revoked', 'Permission Revoked'),
        ('group_added', 'Added to Group'),
        ('group_removed', 'Removed from Group'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('access_denied', 'Access Denied'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_logs')
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    resource = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auth_permission_log'
        verbose_name = 'Permission Log'
        verbose_name_plural = 'Permission Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_action_display()} - {self.created_at}"