from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.db import models
from functools import wraps
from .models import UserPermission, GroupResourcePermission
import logging

logger = logging.getLogger(__name__)


def check_resource_permission(user, resource_name, permission_type, region=None):
    """
    This function is responsible for checking if a user has permission for a specific resource/action.
    Optionally filters by region scope. Returns True if access is granted.
    """
    if not user.is_authenticated:
        return False
    
    # Check direct user permissions (not region-scoped)
    user_perms = user.custom_permissions.filter(
        resource_permission__resource_name=resource_name,
        resource_permission__permission_type=permission_type,
        is_active=True
    ).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
    )
    
    if user_perms.exists():
        return True

    # Check group permissions
    user_groups = user.groups.values_list('id', flat=True)
    
    group_perms = GroupResourcePermission.objects.filter(
        group__in=user_groups,
        resource_permission__resource_name=resource_name,
        resource_permission__permission_type=permission_type
    )

    if region:
        # Filter: global (null) OR matching region
        group_perms = group_perms.filter(
            models.Q(region__isnull=True) | models.Q(region=region)
        )

    return group_perms.exists()


def get_user_permitted_regions(user, resource_name, permission_type):
    """
    This function is responsible for returning region IDs the user can access for a resource/permission.
    Returns None if user has global access (no region restriction).
    """
    if not user.is_authenticated:
        return []
    
    # Check direct user permissions (grants global access)
    user_perms = user.custom_permissions.filter(
        resource_permission__resource_name=resource_name,
        resource_permission__permission_type=permission_type,
        is_active=True
    ).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
    )
    
    if user_perms.exists():
        return None  # Global access
    
    user_groups = user.groups.values_list('id', flat=True)
    
    group_perms = GroupResourcePermission.objects.filter(
        group__in=user_groups,
        resource_permission__resource_name=resource_name,
        resource_permission__permission_type=permission_type
    )
    
    # If any permission has null region, user has global access
    if group_perms.filter(region__isnull=True).exists():
        return None
    
    # Return specific region IDs
    return list(group_perms.values_list('region_id', flat=True).distinct())


def permission_required(resource_name, permission_type='view', raise_exception=True):
    """
    This decorator is responsible for checking resource-based permissions.
    Checks both direct user permissions and group permissions via Django's built-in Group model.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if raise_exception:
                    raise PermissionDenied("Authentication required.")
                return redirect('auth:login')
            
            # Check direct user permissions
            user_perms = request.user.custom_permissions.filter(
                resource_permission__resource_name=resource_name,
                resource_permission__permission_type=permission_type,
                is_active=True
            )
            
            # Check if any permission has expired
            active_user_perms = user_perms.filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
            )
            
            if active_user_perms.exists():
                return view_func(request, *args, **kwargs)
            
            # Check group permissions via Django's built-in Group model
            user_groups = request.user.groups.values_list('id', flat=True)
            
            group_perms = GroupResourcePermission.objects.filter(
                group__in=user_groups,
                resource_permission__resource_name=resource_name,
                resource_permission__permission_type=permission_type
            )
            
            if group_perms.exists():
                return view_func(request, *args, **kwargs)
            
            if raise_exception:
                raise PermissionDenied(f"You don't have {permission_type} permission for {resource_name}.")
            
            messages.error(request, f"You don't have {permission_type} permission for {resource_name}.")
            return redirect('core:main')
        
        return wrapper
    return decorator


def download_permission_required(resource_name):
    """
    Decorator specifically for download permissions.
    """
    return permission_required(resource_name, 'download')


def edit_permission_required(resource_name):
    """
    Decorator specifically for edit permissions.
    """
    return permission_required(resource_name, 'change')


def view_permission_required(resource_name):
    """
    Decorator specifically for view permissions.
    """
    return permission_required(resource_name, 'view')
