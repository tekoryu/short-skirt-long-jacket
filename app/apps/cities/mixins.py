"""
This module is responsible for providing admin mixins for region-scoped permission control.
"""
import logging

from django.core.exceptions import PermissionDenied

from apps.auth.decorators import check_resource_permission, get_user_permitted_regions
from apps.auth.models import PermissionLog
from .models import Region, State, IntermediateRegion, ImmediateRegion, Municipality

logger = logging.getLogger(__name__)


class RegionScopedAdminMixin:
    """
    This class is responsible for restricting admin actions based on region-scoped permissions.
    Uses the existing GroupResourcePermission infrastructure with region FK.
    
    Configure via class attributes:
        - region_resource_name: Resource name for permission checks (e.g., 'cities.municipality')
    """
    
    region_resource_name = None  # Must be set by subclass
    
    def get_region_resource_name(self):
        """Returns the resource name used for permission checks."""
        if self.region_resource_name:
            return self.region_resource_name
        return f"cities.{self.model._meta.model_name}"
    
    def _resolve_region(self, obj):
        """
        This method is responsible for extracting the Region from any cities model instance.
        """
        if obj is None:
            return None
        if isinstance(obj, Region):
            return obj
        if isinstance(obj, State):
            return obj.region
        if isinstance(obj, IntermediateRegion):
            return obj.state.region if obj.state else None
        if isinstance(obj, ImmediateRegion):
            state = obj.intermediate_region.state if obj.intermediate_region else None
            return state.region if state else None
        if isinstance(obj, Municipality):
            immediate = obj.immediate_region
            if immediate and immediate.intermediate_region:
                state = immediate.intermediate_region.state
                return state.region if state else None
        return None
    
    def _user_can_access_region(self, user, region, permission_type):
        """
        This method is responsible for checking if user has permission for a specific region.
        """
        if user.is_superuser:
            return True
        return check_resource_permission(
            user,
            self.get_region_resource_name(),
            permission_type,
            region=region
        )
    
    def _get_user_region_ids(self, user, permission_type):
        """
        This method is responsible for returning region IDs user can access.
        Returns None for global access.
        """
        if user.is_superuser:
            return None
        return get_user_permitted_regions(
            user,
            self.get_region_resource_name(),
            permission_type
        )
    
    def _log_denied(self, request, obj, action):
        """
        This method is responsible for logging permission denials for audit.
        """
        region = self._resolve_region(obj)
        try:
            PermissionLog.objects.create(
                user=request.user,
                action='access_denied',
                resource=self.get_region_resource_name(),
                details=f"Denied {action} for {self.model._meta.label}:{getattr(obj, 'pk', 'new')} region={getattr(region, 'name', 'unknown')}",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
        except Exception as e:
            logger.error(f"Failed to log permission denial: {e}")

    def has_view_permission(self, request, obj=None):
        base = super().has_view_permission(request, obj)
        if not base or request.user.is_superuser:
            return base
        
        # For list view (obj=None), allow if user has any region access
        if obj is None:
            region_ids = self._get_user_region_ids(request.user, 'view')
            return region_ids is None or len(region_ids) > 0
        
        region = self._resolve_region(obj)
        return self._user_can_access_region(request.user, region, 'view')

    def has_change_permission(self, request, obj=None):
        base = super().has_change_permission(request, obj)
        if not base or request.user.is_superuser:
            return base
        if obj is None:
            return base
        
        region = self._resolve_region(obj)
        return self._user_can_access_region(request.user, region, 'change')

    def has_delete_permission(self, request, obj=None):
        base = super().has_delete_permission(request, obj)
        if not base or request.user.is_superuser:
            return base
        if obj is None:
            return base
        
        region = self._resolve_region(obj)
        return self._user_can_access_region(request.user, region, 'delete')

    def has_add_permission(self, request):
        base = super().has_add_permission(request)
        if not base or request.user.is_superuser:
            return base
        
        # Allow add if user has any region with 'add' permission
        region_ids = self._get_user_region_ids(request.user, 'add')
        return region_ids is None or len(region_ids) > 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        region_ids = self._get_user_region_ids(request.user, 'view')
        if region_ids is None:
            return qs  # Global access
        
        if not region_ids:
            return qs.none()
        
        # Filter queryset by region
        return self._filter_queryset_by_regions(qs, region_ids)
    
    def _filter_queryset_by_regions(self, qs, region_ids):
        """
        This method is responsible for filtering queryset to only include objects in specified regions.
        """
        model = qs.model
        if model == Region:
            return qs.filter(id__in=region_ids)
        elif model == State:
            return qs.filter(region_id__in=region_ids)
        elif model == IntermediateRegion:
            return qs.filter(state__region_id__in=region_ids)
        elif model == ImmediateRegion:
            return qs.filter(intermediate_region__state__region_id__in=region_ids)
        elif model == Municipality:
            return qs.filter(immediate_region__intermediate_region__state__region_id__in=region_ids)
        return qs

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            region = self._resolve_region(obj)
            action = 'change' if change else 'add'
            if not self._user_can_access_region(request.user, region, action):
                self._log_denied(request, obj, action)
                raise PermissionDenied(f"You don't have {action} permission for this region.")
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        if not request.user.is_superuser:
            region = self._resolve_region(obj)
            if not self._user_can_access_region(request.user, region, 'delete'):
                self._log_denied(request, obj, 'delete')
                raise PermissionDenied("You don't have delete permission for this region.")
        super().delete_model(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.is_superuser:
            return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        # For 'add' permission, filter FK choices to allowed regions
        region_ids = self._get_user_region_ids(request.user, 'add')
        
        if region_ids is None:
            return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if not region_ids:
            region_ids = []
        
        if db_field.name == 'region':
            kwargs['queryset'] = Region.objects.filter(id__in=region_ids)
        elif db_field.name == 'state':
            kwargs['queryset'] = State.objects.filter(region_id__in=region_ids)
        elif db_field.name == 'intermediate_region':
            kwargs['queryset'] = IntermediateRegion.objects.filter(state__region_id__in=region_ids)
        elif db_field.name == 'immediate_region':
            kwargs['queryset'] = ImmediateRegion.objects.filter(
                intermediate_region__state__region_id__in=region_ids
            )
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

