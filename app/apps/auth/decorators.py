from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.db import models
from functools import wraps
from .models import UserPermission, GroupResourcePermission
import logging

logger = logging.getLogger(__name__)


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
