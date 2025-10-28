# Technical Documentation - Short Skirt Long Jacket

## Project Overview

A Django-based government policy decision support system for Brazilian cities data analysis. The system provides granular permission controls for government agents to access city information within their scope, with plans for an AI chatbot for high-level executives.

## Technology Stack

### Backend
- **Django 5.2.7** - Web framework
- **Python 3.12.3** - Runtime environment
- **PostgreSQL 15** - Primary database
- **Gunicorn 23.0.0** - WSGI server for production
- **psycopg2-binary 2.9.10** - PostgreSQL adapter

### Data Processing
- **pandas** - Data manipulation and analysis
- **openpyxl** - Excel file processing
- **xlrd** - Excel file reading

### Frontend
- **Django Templates** - Server-side rendering
- **Vanilla JavaScript** - Client-side interactions
- **CSS3** - Styling with modern features (gradients, animations, flexbox)
- **Font Awesome 6.0.0** - Icons

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Alpine Linux 3.19** - Base container image
- **Nginx** (via static volume) - Static file serving

## Architecture Patterns

### Project Structure
```
app/
├── apps/                    # Django apps organized in modules
│   ├── auth/               # Authentication & permissions
│   ├── cities/             # City data management
│   └── core/               # Core functionality & UI
├── config/                 # Django settings
├── data/                   # Static data files
└── static/                 # Global static files
```

### Database Design
- **Custom User Model** - Extended AbstractUser with additional fields
- **Geographic Hierarchy** - State → Intermediate Region → Immediate Region → Municipality
- **Granular Permissions** - Resource-based permission system
- **Audit Logging** - Permission change tracking

## Key Features Implementation

### 1. Authentication System (`apps/auth/`)

**Custom User Model:**
- Email-based authentication (`USERNAME_FIELD = 'email'`)
- Additional fields: phone, department, position, is_verified
- Custom admin interface with enhanced user management

**Granular Permission System:**
- `ResourcePermission` - Defines permissions for specific resources
- `UserPermission` - Direct user permission assignments
- `PermissionGroup` - Group-based permission management
- `UserGroup` - User-group associations
- `PermissionLog` - Audit trail for permission changes

**Permission Types:**
- view, add, change, delete, download, export, import

**Mixins & Decorators:**
- `PermissionRequiredMixin` - Class-based view permission checking
- `@permission_required` - Function-based view decorator
- `ViewPermissionMixin` - Specialized for view permissions

### 2. City Data Management (`apps/cities/`)

**Geographic Models:**
- `State` - Brazilian states with codes
- `IntermediateRegion` - Geographic intermediate regions
- `ImmediateRegion` - Geographic immediate regions  
- `Municipality` - Brazilian municipalities

**IBGE Data Integration:**
- Management commands for data import/export
- CSV processing with batch operations
- Data validation and error handling
- Dry-run capabilities for testing

**Management Commands:**
- `import_ibge_data` - Import from CSV with batch processing
- `clear_ibge_data` - Clear all geographic data with confirmation

### 3. Core Application (`apps/core/`)

**UI Components:**
- Responsive top bar with gradient background
- Interactive user menu dropdown
- Modern CSS with animations and transitions
- Mobile-friendly design

**JavaScript Features:**
- User menu toggle functionality
- Click-outside-to-close behavior
- Keyboard navigation (Escape key)
- Event delegation and cleanup

## Development Environment

### Docker Configuration
- **Multi-stage build** with development/production modes
- **Volume mounting** for live code reloading
- **Health checks** for both database and application
- **Environment variable** configuration
- **Non-root user** execution for security

### Database Setup
- **PostgreSQL** with health checks
- **Connection pooling** via psycopg2
- **Migration management** with Django ORM
- **Data seeding** via management commands

### Static File Management
- **Collectstatic** for production builds
- **Volume mounting** for development
- **CDN-ready** static file serving

## Security Features

### Authentication
- **Email-based** user identification
- **Password validation** with Django validators
- **Session management** with secure cookies
- **CSRF protection** enabled

### Authorization
- **Resource-based** permission system
- **Time-based** permission expiration
- **Audit logging** for all permission changes
- **Group-based** permission inheritance

### Infrastructure Security
- **Non-root container** execution
- **Environment variable** configuration
- **Health check** monitoring
- **Volume isolation** for data persistence

## API Patterns

### Permission Checking
```python
# Class-based views
class MyView(PermissionRequiredMixin, View):
    permission_required = 'cities.city'
    permission_type = 'view'

# Function-based views
@permission_required('cities.city', 'view')
def my_view(request):
    pass
```

### API Responses
- **JSON responses** for API endpoints
- **Permission-based** data filtering
- **Error handling** with appropriate HTTP status codes
- **Authentication** checks for protected endpoints

## Data Management

### Import Process
1. **CSV parsing** with pandas
2. **Batch processing** for large datasets
3. **Transaction management** for data integrity
4. **Error logging** and reporting
5. **Dry-run** capabilities for testing

### Geographic Data
- **Hierarchical structure** (State → Region → Municipality)
- **IBGE codes** for official identification
- **Indexed fields** for performance
- **Foreign key** relationships with CASCADE delete

## Frontend Patterns

### Template Structure
- **Base template** with common layout
- **Block inheritance** for content extension
- **Static file** loading with Django tags
- **URL namespacing** for app isolation

### CSS Architecture
- **Mobile-first** responsive design
- **CSS Grid/Flexbox** for layouts
- **CSS Custom Properties** for theming
- **Component-based** styling approach

### JavaScript Patterns
- **Event delegation** for dynamic content
- **Module pattern** for code organization
- **Progressive enhancement** approach
- **Accessibility** considerations (keyboard navigation)

## Testing Strategy

### Management Commands
- **Dry-run** options for safe testing
- **Batch processing** with configurable sizes
- **Error handling** and logging
- **Statistics reporting** for data validation

### Database Testing
- **Transaction rollback** for test isolation
- **Fixture loading** for test data
- **Migration testing** with real data
- **Performance testing** with large datasets

## Deployment Considerations

### Production Setup
- **Gunicorn** WSGI server
- **Static file** collection and serving
- **Database migration** automation
- **Health check** endpoints
- **Environment variable** configuration

### Development Setup
- **Django development** server
- **Live reloading** via volume mounting
- **Debug mode** with detailed error pages
- **Database seeding** via management commands

## Common Development Tasks

### Adding New Features
1. Create Django app in `apps/` directory
2. Register in `INSTALLED_APPS`
3. Create models with proper Meta classes
4. Register models in admin
5. Create views with permission decorators
6. Add URL patterns with namespacing
7. Create templates extending base template
8. Add static files (CSS/JS) if needed

### Permission Management
1. Create `ResourcePermission` for new resources
2. Use mixins or decorators in views
3. Test permission checking in views
4. Add admin interface for permission management
5. Create management commands for bulk operations

### Data Import/Export
1. Create management command class
2. Add argument parsing for options
3. Implement batch processing for large datasets
4. Add error handling and logging
5. Include dry-run capabilities
6. Test with sample data

## Environment Variables

### Required Variables
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `DB_HOST` - Database host
- `DB_PORT` - Database port
- `ALLOWED_HOSTS` - Comma-separated allowed hosts

### Optional Variables
- `STATIC_URL` - Static files URL (default: /static/)
- `STATIC_ROOT` - Static files root (default: /vol/web/static)
- `MEDIA_URL` - Media files URL (default: /media/)
- `MEDIA_ROOT` - Media files root (default: /vol/web/media)
- `DJANGO_SUPERUSER_*` - Superuser creation variables

## Performance Considerations

### Database
- **Indexed fields** on frequently queried columns
- **Select related** for foreign key optimization
- **Batch operations** for bulk data processing
- **Connection pooling** via psycopg2

### Frontend
- **Minified static files** for production
- **CDN integration** ready
- **Lazy loading** for large datasets
- **Caching** strategies for static content

### Container
- **Multi-stage builds** to reduce image size
- **Alpine Linux** for minimal base image
- **Layer caching** for faster builds
- **Health checks** for monitoring

This technical documentation provides a comprehensive overview of the system architecture, technologies, and patterns used. It serves as a reference for developing new features and understanding the existing codebase structure.
