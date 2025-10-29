from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.auth.mixins import ViewPermissionMixin, DownloadPermissionMixin, EditPermissionMixin
from apps.auth.decorators import view_permission_required, download_permission_required, edit_permission_required
from .models import Municipality


class CityListView(LoginRequiredMixin, ViewPermissionMixin, ListView):
    """
    List view for cities with view permission check.
    """
    model = Municipality
    template_name = 'cities/city_list.html'
    context_object_name = 'cities'
    resource_name = 'cities.city'
    permission_type = 'view'


@download_permission_required('cities.city')
def download_cities(request):
    """
    Download cities data - requires download permission.
    """
    cities = Municipality.objects.select_related(
        'immediate_region__intermediate_region__state'
    ).all()

    # In a real implementation, you would generate a file (CSV, Excel, etc.)
    # For this example, we'll return JSON
    data = {
        'cities': [
            {
                'code': city.code,
                'name': city.name,
                'state': city.immediate_region.intermediate_region.state.name,
                'state_code': city.immediate_region.intermediate_region.state.code
            }
            for city in cities
        ]
    }

    return JsonResponse(data)


@edit_permission_required('cities.city')
def edit_city(request, city_id):
    """
    Edit city data - requires edit permission.
    """
    # This would be a form view in a real implementation
    return JsonResponse({'message': f'Edit city {city_id} - Permission granted'})


def city_api(request):
    """
    API endpoint that checks permissions dynamically.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Check if user has view permission
    from apps.auth.models import UserPermission, GroupPermission, UserGroup
    
    has_view_permission = False
    
    # Check direct permissions
    user_perms = request.user.custom_permissions.filter(
        resource_permission__resource_name='cities.city',
        resource_permission__permission_type='view',
        is_active=True
    )
    
    if user_perms.exists():
        has_view_permission = True
    else:
        # Check group permissions
        user_groups = UserGroup.objects.filter(
            user=request.user,
            is_active=True
        ).values_list('group', flat=True)
        
        group_perms = GroupPermission.objects.filter(
            group__in=user_groups,
            resource_permission__resource_name='cities.city',
            resource_permission__permission_type='view'
        )
        
        if group_perms.exists():
            has_view_permission = True
    
    if not has_view_permission:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    cities = Municipality.objects.select_related(
        'immediate_region__intermediate_region__state'
    ).all()[:10]  # Limit for demo
    data = {
        'cities': [
            {
                'id': city.id,
                'code': city.code,
                'name': city.name,
                'state': city.immediate_region.intermediate_region.state.name,
                'state_code': city.immediate_region.intermediate_region.state.code,
                'region': city.immediate_region.name
            }
            for city in cities
        ]
    }

    return JsonResponse(data)