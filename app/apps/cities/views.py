from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from apps.auth.mixins import ViewPermissionMixin, DownloadPermissionMixin, EditPermissionMixin
from apps.auth.decorators import view_permission_required, download_permission_required, edit_permission_required
from apps.auth.models import PermissionLog
from .models import Municipality, MunicipalityLog
from .forms import MunicipalityEditForm
import logging

logger = logging.getLogger(__name__)


class CityListView(LoginRequiredMixin, ViewPermissionMixin, ListView):
    """
    List view for cities with view permission check.
    """
    model = Municipality
    template_name = 'cities/city_list.html'
    context_object_name = 'cities'
    resource_name = 'cities.city'
    permission_type = 'view'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Municipality.objects.select_related(
            'immediate_region__intermediate_region__state'
        ).all()
        
        # Search/filter functionality
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Capital cities filter
        is_capital = self.request.GET.get('is_capital', '')
        if is_capital == 'true':
            queryset = queryset.filter(is_capital=True)
        
        # SEAF category filter
        seaf_category = self.request.GET.get('seaf_category', '')
        if seaf_category == 'null':
            queryset = queryset.filter(seaf_category__isnull=True)
        elif seaf_category and seaf_category.isdigit():
            queryset = queryset.filter(seaf_category=int(seaf_category))
        
        # Sort functionality
        sort_by = self.request.GET.get('sort', 'name')
        direction = self.request.GET.get('direction', 'asc')
        
        valid_sort_fields = ['name', 'seaf_category', 'mayor_name', 'mayor_party']
        if sort_by in valid_sort_fields:
            order_field = f"-{sort_by}" if direction == 'desc' else sort_by
            queryset = queryset.order_by(order_field)
        else:
            queryset = queryset.order_by('name')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['current_sort'] = self.request.GET.get('sort', 'name')
        context['current_direction'] = self.request.GET.get('direction', 'asc')
        context['is_capital'] = self.request.GET.get('is_capital', '')
        context['seaf_category'] = self.request.GET.get('seaf_category', '')
        return context


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
    This view is responsible for editing city data with comprehensive audit logging.
    Requires edit permission.
    """
    municipality = get_object_or_404(
        Municipality.objects.select_related(
            'immediate_region__intermediate_region__state'
        ),
        id=city_id
    )
    
    if request.method == 'POST':
        form = MunicipalityEditForm(request.POST, instance=municipality)
        if form.is_valid():
            # Get IP and User Agent for logging
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Track changes before saving
            changed_fields = []
            for field in form.changed_data:
                old_value = str(getattr(municipality, field)) if getattr(municipality, field) is not None else ''
                new_value = str(form.cleaned_data[field]) if form.cleaned_data[field] is not None else ''
                
                # Get field label from form
                field_label = form.fields[field].label or field
                
                changed_fields.append({
                    'field': field,
                    'label': field_label,
                    'old': old_value,
                    'new': new_value
                })
            
            # Save the form
            form.save()
            
            # Log each change in MunicipalityLog
            for change in changed_fields:
                MunicipalityLog.objects.create(
                    municipality=municipality,
                    user=request.user,
                    action='Atualização',
                    field_name=change['label'],
                    old_value=change['old'],
                    new_value=change['new'],
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            # Also log in PermissionLog for general audit
            if changed_fields:
                change_summary = ', '.join([f"{c['label']}" for c in changed_fields[:5]])
                if len(changed_fields) > 5:
                    change_summary += f" (e mais {len(changed_fields) - 5} campos)"
                
                PermissionLog.objects.create(
                    user=request.user,
                    action='granted',
                    resource='cities.city.edit',
                    details=f"Município '{municipality.name}' editado. Campos alterados: {change_summary}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                logger.info(
                    f"Municipality {municipality.name} (ID: {municipality.id}) edited by {request.user.email}. "
                    f"Fields changed: {change_summary}"
                )
            
            messages.success(request, f'Município "{municipality.name}" atualizado com sucesso!')
            return redirect('cities:city_list')
    else:
        form = MunicipalityEditForm(instance=municipality)
    
    # Get recent change history
    recent_logs = municipality.change_logs.select_related('user').all()[:20]
    
    context = {
        'form': form,
        'municipality': municipality,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'cities/edit_city.html', context)


def city_api(request):
    """
    API endpoint that checks permissions dynamically.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Superusers have all permissions
    if request.user.is_superuser:
        has_view_permission = True
    else:
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


def seaf_data_api(request):
    """
    This endpoint is responsible for returning municipality SEAF category data for choropleth map visualization.
    Returns JSON with municipality codes and their SEAF categories.
    """
    municipalities = Municipality.objects.filter(
        seaf_category__isnull=False
    ).values('code', 'name', 'seaf_category')
    
    # Create a dictionary mapping IBGE code to SEAF category
    data = {
        municipality['code']: {
            'name': municipality['name'],
            'seaf_category': municipality['seaf_category']
        }
        for municipality in municipalities
    }
    
    return JsonResponse(data)


def seaf_data_by_state_api(request):
    """
    This endpoint is responsible for returning aggregated SEAF category data by state.
    Returns JSON with state codes and their average SEAF categories.
    """
    from django.db.models import Avg, Count, F
    
    # Aggregate SEAF categories by state
    state_data = Municipality.objects.filter(
        seaf_category__isnull=False
    ).values(
        state_code=F('immediate_region__intermediate_region__state__code'),
        state_name=F('immediate_region__intermediate_region__state__name')
    ).annotate(
        avg_category=Avg('seaf_category'),
        total_municipalities=Count('id')
    )
    
    # Create dictionary mapping state code to aggregated data
    data = {
        item['state_code']: {
            'name': item['state_name'],
            'avg_category': round(item['avg_category'], 1),
            'total_municipalities': item['total_municipalities']
        }
        for item in state_data
    }
    
    return JsonResponse(data)