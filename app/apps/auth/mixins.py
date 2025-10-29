from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from .models import UserPermission, GroupPermission, UserGroup, PermissionLog
import logging

logger = logging.getLogger(__name__)


class PermissionRequiredMixin:
    """
    Mixin to check if user has required permission for a resource.
    """
    permission_required = None
    permission_type = 'view'
    resource_name = None
    raise_exception = True
    redirect_url = None
    
    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self):
        if not self.permission_required and not self.resource_name:
            return True
        
        if not self.request.user.is_authenticated:
            return False
        
        # Check if user has the specific permission
        if self.permission_required:
            return self.request.user.has_perm(self.permission_required)
        
        # Check resource-based permission
        if self.resource_name:
            return self.check_resource_permission(self.resource_name, self.permission_type)
        
        return False
    
    def check_resource_permission(self, resource_name, permission_type):
        """
        Check if user has permission for specific resource and action.
        """
        user = self.request.user
        
        # Check direct user permissions
        user_perms = user.custom_permissions.filter(
            resource_permission__resource_name=resource_name,
            resource_permission__permission_type=permission_type,
            is_active=True
        )
        
        # Check if any permission has expired
        active_user_perms = user_perms.filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        )
        
        if active_user_perms.exists():
            # Don't log successful accesses to prevent database bloat
            # Only log in application-level logging if needed
            logger.debug(f"User {user.email} accessed {resource_name} with {permission_type}")
            return True

        # Check group permissions
        user_groups = UserGroup.objects.filter(
            user=user,
            is_active=True
        ).values_list('group', flat=True)

        group_perms = GroupPermission.objects.filter(
            group__in=user_groups,
            resource_permission__resource_name=resource_name,
            resource_permission__permission_type=permission_type
        )

        if group_perms.exists():
            # Don't log successful accesses to prevent database bloat
            logger.debug(f"User {user.email} accessed {resource_name} with {permission_type} via group")
            return True

        # Only log access denials to the database for security auditing
        self.log_permission_access(resource_name, permission_type, False)
        return False
    
    def log_permission_access(self, resource_name, permission_type, granted):
        """
        Log permission access denials to the database.
        Note: Only denials are logged to prevent database bloat.
        Successful accesses are logged via application logging (logger.debug).
        """
        try:
            if not granted:
                PermissionLog.objects.create(
                    user=self.request.user,
                    action='access_denied',
                    resource=f"{resource_name}.{permission_type}",
                    details=f"Access denied for {resource_name}",
                    ip_address=self.get_client_ip(),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', '')
                )
        except Exception as e:
            logger.error(f"Failed to log permission denial: {e}")
    
    def get_client_ip(self):
        """
        Get client IP address from request.
        Safely handles X-Forwarded-For header to prevent IP spoofing.
        """
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the rightmost IP that isn't a loopback or private IP
            # This prevents users from spoofing their IP via X-Forwarded-For
            ips = [ip.strip() for ip in x_forwarded_for.split(',')]
            # Take the last IP before hitting our reverse proxy
            # In production, you may want to configure trusted proxies
            for ip in reversed(ips):
                if ip and not ip.startswith(('127.', '10.', '172.16.', '192.168.')):
                    return ip
        return self.request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    def handle_no_permission(self):
        if self.raise_exception:
            raise PermissionDenied("You don't have permission to access this resource.")
        
        if self.redirect_url:
            return redirect(self.redirect_url)
        
        messages.error(self.request, "You don't have permission to access this resource.")
        return redirect('core:main')


class DownloadPermissionMixin(PermissionRequiredMixin):
    """
    Mixin specifically for download permissions.
    """
    permission_type = 'download'
    
    def has_permission(self):
        return super().has_permission()


class EditPermissionMixin(PermissionRequiredMixin):
    """
    Mixin specifically for edit permissions.
    """
    permission_type = 'change'
    
    def has_permission(self):
        return super().has_permission()


class ViewPermissionMixin(PermissionRequiredMixin):
    """
    Mixin specifically for view permissions.
    """
    permission_type = 'view'
    
    def has_permission(self):
        return super().has_permission()




class APIResponseMixin:
    """
    Mixin for API views that need permission checking.
    """
    def handle_no_permission(self):
        return JsonResponse({
            'error': 'Permission denied',
            'message': 'You don\'t have permission to access this resource.'
        }, status=403)
    
    def permission_denied_response(self, message="Permission denied"):
        return JsonResponse({
            'error': 'Permission denied',
            'message': message
        }, status=403)
