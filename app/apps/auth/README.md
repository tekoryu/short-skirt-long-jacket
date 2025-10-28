# Auth App - Granular Permission System

This Django app extends Django's built-in authentication system with granular permission controls for what users can see, edit, or download.

## Features

### 1. Custom User Model
- Extends `AbstractUser` with additional fields
- Email-based authentication
- Department and position tracking
- User verification status

### 2. Granular Permission System
- **Resource Permissions**: Define permissions for specific resources (models/views)
- **Permission Types**: view, add, change, delete, download, export, import
- **User Permissions**: Direct permission assignment to users
- **Group Permissions**: Organize permissions into groups
- **Time-based Expiration**: Permissions can have expiration dates

### 3. Permission Management
- **Admin Interface**: Full CRUD operations for all permission models
- **Permission Logging**: Audit trail for all permission-related actions
- **API Endpoints**: Check permissions programmatically

## Models

### User
Custom user model with additional fields:
- `email`: Primary identifier
- `phone`: Contact information
- `department`: Organizational unit
- `position`: Job title
- `is_verified`: Email verification status

### ResourcePermission
Defines what actions can be performed on specific resources:
- `name`: Human-readable name
- `codename`: Unique identifier
- `permission_type`: Type of permission (view, add, change, delete, download, export, import)
- `resource_name`: Target resource (e.g., 'cities.city', 'core.settings')

### UserPermission
Links users to specific resource permissions:
- `user`: Target user
- `resource_permission`: Permission being granted
- `granted_by`: Who granted the permission
- `expires_at`: Optional expiration date

### PermissionGroup
Organizes permissions into logical groups:
- `name`: Group name
- `description`: Group description
- `is_active`: Whether group is active

### UserGroup
Links users to permission groups:
- `user`: Target user
- `group`: Permission group
- `added_by`: Who added the user to the group

### PermissionLog
Audit trail for permission-related actions:
- `user`: User involved
- `action`: Action performed
- `resource`: Resource affected
- `ip_address`: Client IP
- `user_agent`: Browser information

## Usage

### 1. Using Mixins

```python
from apps.auth.mixins import ViewPermissionMixin, DownloadPermissionMixin, EditPermissionMixin

class CityListView(LoginRequiredMixin, ViewPermissionMixin, ListView):
    model = City
    resource_name = 'cities.city'
    permission_type = 'view'
```

### 2. Using Decorators

```python
from apps.auth.decorators import view_permission_required, download_permission_required

@view_permission_required('cities.city')
def city_detail(request, city_id):
    # View logic here
    pass

@download_permission_required('cities.city')
def download_cities(request):
    # Download logic here
    pass
```

### 3. Checking Permissions Programmatically

```python
from apps.auth.models import UserPermission, GroupPermission, UserGroup

# Check if user has specific permission
user_perms = request.user.custom_permissions.filter(
    resource_permission__resource_name='cities.city',
    resource_permission__permission_type='view',
    is_active=True
)

if user_perms.exists():
    # User has permission
    pass
```

### 4. API Permission Check

```python
# GET /auth/api/check-permission/?resource=cities.city&type=view
# Returns: {"has_permission": true, "resource": "cities.city", "permission_type": "view"}
```

## Admin Interface

Access the admin interface at `/admin/` to manage:
- Users and their permissions
- Permission groups
- Resource permissions
- Permission logs
- User group assignments

## URL Patterns

- `/auth/login/` - User login
- `/auth/logout/` - User logout
- `/auth/register/` - User registration
- `/auth/profile/` - User profile with permission summary
- `/auth/permissions/` - List all permissions (admin only)
- `/auth/user-permissions/` - List user permissions (admin only)
- `/auth/assign-permission/` - Assign permission to user (admin only)
- `/auth/assign-group/` - Assign user to group (admin only)
- `/auth/api/check-permission/` - API permission check

## Examples

### Creating a Resource Permission

```python
from apps.auth.models import ResourcePermission

ResourcePermission.objects.create(
    name='View Cities',
    codename='view_cities',
    permission_type='view',
    resource_name='cities.city',
    description='Can view city data'
)
```

### Assigning Permission to User

```python
from apps.auth.models import UserPermission, User, ResourcePermission

user = User.objects.get(email='user@example.com')
permission = ResourcePermission.objects.get(codename='view_cities')

UserPermission.objects.create(
    user=user,
    resource_permission=permission,
    granted_by=request.user
)
```

### Creating a Permission Group

```python
from apps.auth.models import PermissionGroup, GroupPermission

group = PermissionGroup.objects.create(
    name='City Managers',
    description='Users who can manage city data'
)

# Add permission to group
GroupPermission.objects.create(
    group=group,
    resource_permission=permission
)
```

## Security Features

1. **Permission Expiration**: Permissions can have expiration dates
2. **Audit Logging**: All permission actions are logged
3. **IP Tracking**: Client IP addresses are recorded
4. **Group-based Permissions**: Efficient permission management through groups
5. **Time-based Access**: Permissions can be temporary

## Best Practices

1. **Use Groups**: Organize permissions into logical groups rather than assigning individual permissions
2. **Regular Audits**: Review permission logs regularly
3. **Principle of Least Privilege**: Grant only necessary permissions
4. **Time-based Access**: Use expiration dates for temporary access
5. **Resource Naming**: Use consistent naming for resources (app.model format)
