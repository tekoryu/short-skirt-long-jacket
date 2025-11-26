"""
This middleware is responsible for enforcing authentication across the entire application.
Only whitelisted URLs are accessible without authentication.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings


class LoginRequiredMiddleware:
    """
    Middleware that requires users to be authenticated for all views
    except those explicitly whitelisted.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that can be accessed without authentication
        self.whitelist = [
            '/auth/login/',
            '/auth/register/',  # Only superusers can access (checked in view)
            '/health/',
            '/admin/login/',  # Django admin login
        ]
    
    def __call__(self, request):
        # Allow whitelisted URLs
        if request.path in self.whitelist:
            return self.get_response(request)
        
        # Allow static and media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        # If user is authenticated, allow access
        if request.user.is_authenticated:
            return self.get_response(request)
        
        # Redirect to login page with next parameter
        login_url = '/auth/login/'
        
        # Avoid redirect loops
        if request.path == login_url:
            return self.get_response(request)
        
        # Redirect with next parameter to return after login
        return redirect(f'{login_url}?next={request.path}')

