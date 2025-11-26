from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.db import models
from django_ratelimit.decorators import ratelimit
from .models import (
    User, ResourcePermission, UserPermission,
    GroupResourcePermission, PermissionLog
)
from .mixins import PermissionRequiredMixin, APIResponseMixin
from .forms import UserRegistrationForm, PermissionAssignmentForm, GroupResourcePermissionForm
import logging

logger = logging.getLogger(__name__)


@ratelimit(key='ip', rate='5/5m', method='POST', block=True)
def login_view(request):
    """
    Custom login view with permission logging.
    Rate limited to 5 attempts per 5 minutes per IP to prevent brute force attacks.
    """
    if request.user.is_authenticated:
        return redirect('core:main')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                
                # Log successful login
                PermissionLog.objects.create(
                    user=user,
                    action='login',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect to 'next' parameter if present, otherwise go to main
                next_url = request.GET.get('next') or request.POST.get('next') or 'core:main'
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please provide both email and password.')
    
    return render(request, 'auth/login.html')


def logout_view(request):
    """
    Custom logout view with permission logging.
    """
    if request.user.is_authenticated:
        # Log logout
        PermissionLog.objects.create(
            user=request.user,
            action='logout',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('auth:login')


@ratelimit(key='ip', rate='3/1h', method='POST', block=True)
def register_view(request):
    """
    User registration view - RESTRICTED TO SUPERUSERS ONLY.
    Only superusers can create new accounts through this interface.
    Rate limited to 3 registrations per hour per IP to prevent spam.
    """
    # Only superusers can register new users
    if not request.user.is_authenticated:
        messages.error(request, 'Registration is restricted. Please contact an administrator.')
        return redirect('auth:login')
    
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to register new users.')
        return redirect('core:main')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_verified = False  # Require email verification
            user.save()
            
            # Log registration
            PermissionLog.objects.create(
                user=user,
                action='granted',
                resource='user.registration',
                details='User registered successfully'
            )
            
            messages.success(request, 'Registration successful! Please wait for admin approval.')
            return redirect('auth:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register.html', {'form': form})


@login_required
def profile_view(request):
    """
    User profile view with permission summary.
    """
    user = request.user
    
    # Get user's direct permissions
    user_permissions = user.custom_permissions.filter(
        is_active=True
    ).select_related('resource_permission')
    
    # Get user's group permissions
    user_groups = UserGroup.objects.filter(
        user=user,
        is_active=True
    ).select_related('group')
    
    group_permissions = GroupPermission.objects.filter(
        group__in=[ug.group for ug in user_groups]
    ).select_related('resource_permission')
    
    # Get recent permission logs
    recent_logs = PermissionLog.objects.filter(user=user).order_by('-created_at')[:10]
    
    context = {
        'user_permissions': user_permissions,
        'user_groups': user_groups,
        'group_permissions': group_permissions,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'auth/profile.html', context)


class PermissionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List all available permissions (admin only).
    """
    model = ResourcePermission
    template_name = 'auth/permission_list.html'
    context_object_name = 'permissions'
    paginate_by = 20
    permission_required = 'auth.view_resourcepermission'
    
    def get_queryset(self):
        queryset = ResourcePermission.objects.all()
        
        # Filter by permission type
        permission_type = self.request.GET.get('type')
        if permission_type:
            queryset = queryset.filter(permission_type=permission_type)
        
        # Filter by resource name
        resource = self.request.GET.get('resource')
        if resource:
            queryset = queryset.filter(resource_name__icontains=resource)
        
        # Filter by active status
        active = self.request.GET.get('active')
        if active is not None:
            queryset = queryset.filter(is_active=active == 'true')
        
        return queryset.order_by('resource_name', 'permission_type')


class UserPermissionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    List user permissions (admin only).
    """
    model = UserPermission
    template_name = 'auth/user_permission_list.html'
    context_object_name = 'user_permissions'
    paginate_by = 20
    permission_required = 'auth.view_userpermission'
    
    def get_queryset(self):
        queryset = UserPermission.objects.select_related(
            'user', 'resource_permission', 'granted_by'
        )
        
        # Filter by user
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by active status
        active = self.request.GET.get('active')
        if active is not None:
            queryset = queryset.filter(is_active=active == 'true')
        
        return queryset.order_by('-granted_at')


@login_required
def assign_permission_view(request):
    """
    Assign permission to user (admin only).
    """
    if not request.user.has_perm('auth.add_userpermission'):
        messages.error(request, 'You don\'t have permission to assign permissions.')
        return redirect('core:main')
    
    if request.method == 'POST':
        form = PermissionAssignmentForm(request.POST)
        if form.is_valid():
            permission = form.save(commit=False)
            permission.granted_by = request.user
            permission.save()
            
            # Log permission assignment
            PermissionLog.objects.create(
                user=permission.user,
                action='granted',
                resource=f"{permission.resource_permission.resource_name}.{permission.resource_permission.permission_type}",
                details=f"Permission granted by {request.user.email}",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, f'Permission assigned to {permission.user.email}')
            return redirect('auth:user_permission_list')
    else:
        form = PermissionAssignmentForm()
    
    return render(request, 'auth/assign_permission.html', {'form': form})


@login_required
def assign_group_view(request):
    """
    Assign user to group (admin only).
    """
    if not request.user.has_perm('auth.add_usergroup'):
        messages.error(request, 'You don\'t have permission to assign groups.')
        return redirect('core:main')
    
    if request.method == 'POST':
        form = GroupAssignmentForm(request.POST)
        if form.is_valid():
            user_group = form.save(commit=False)
            user_group.added_by = request.user
            user_group.save()
            
            # Log group assignment
            PermissionLog.objects.create(
                user=user_group.user,
                action='group_added',
                resource=user_group.group.name,
                details=f"Added to group by {request.user.email}",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, f'{user_group.user.email} added to {user_group.group.name}')
            return redirect('auth:user_group_list')
    else:
        form = GroupAssignmentForm()
    
    return render(request, 'auth/assign_group.html', {'form': form})


@login_required
def revoke_permission_view(request, permission_id):
    """
    Revoke user permission (admin only).
    """
    if not request.user.has_perm('auth.change_userpermission'):
        messages.error(request, 'You don\'t have permission to revoke permissions.')
        return redirect('core:main')
    
    user_permission = get_object_or_404(UserPermission, id=permission_id)
    
    if request.method == 'POST':
        user_permission.is_active = False
        user_permission.save()
        
        # Log permission revocation
        PermissionLog.objects.create(
            user=user_permission.user,
            action='revoked',
            resource=f"{user_permission.resource_permission.resource_name}.{user_permission.resource_permission.permission_type}",
            details=f"Permission revoked by {request.user.email}",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        messages.success(request, f'Permission revoked for {user_permission.user.email}')
        return redirect('auth:user_permission_list')
    
    return render(request, 'auth/revoke_permission.html', {'permission': user_permission})


@login_required
def check_permission_api(request):
    """
    API endpoint to check user permissions.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    resource_name = request.GET.get('resource')
    permission_type = request.GET.get('type', 'view')
    
    if not resource_name:
        return JsonResponse({'error': 'Resource name required'}, status=400)
    
    # Check permission using the same logic as mixin
    user_perms = request.user.custom_permissions.filter(
        resource_permission__resource_name=resource_name,
        resource_permission__permission_type=permission_type,
        is_active=True
    )
    
    # Check if any permission has expired
    active_user_perms = user_perms.filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
    )
    
    has_permission = active_user_perms.exists()
    
    if not has_permission:
        # Check group permissions
        user_groups = UserGroup.objects.filter(
            user=request.user,
            is_active=True
        ).values_list('group', flat=True)
        
        group_perms = GroupPermission.objects.filter(
            group__in=user_groups,
            resource_permission__resource_name=resource_name,
            resource_permission__permission_type=permission_type
        )
        
        has_permission = group_perms.exists()
    
    return JsonResponse({
        'has_permission': has_permission,
        'resource': resource_name,
        'permission_type': permission_type
    })


def get_client_ip(request):
    """
    Get client IP address from request.
    Safely handles X-Forwarded-For header to prevent IP spoofing.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the rightmost IP that isn't a loopback or private IP
        # This prevents users from spoofing their IP via X-Forwarded-For
        ips = [ip.strip() for ip in x_forwarded_for.split(',')]
        # Take the last IP before hitting our reverse proxy
        # In production, you may want to configure trusted proxies
        for ip in reversed(ips):
            if ip and not ip.startswith(('127.', '10.', '172.16.', '192.168.')):
                return ip
    return request.META.get('REMOTE_ADDR', '0.0.0.0')