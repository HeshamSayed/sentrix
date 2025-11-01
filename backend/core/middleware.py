from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
import threading

_thread_locals = threading.local()

def get_current_user():
    """Get the currently authenticated user from thread local storage"""
    return getattr(_thread_locals, 'user', None)

def get_current_organization():
    """Get the current organization from thread local storage"""
    return getattr(_thread_locals, 'organization', None)

class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to set the current user and organization in thread-local storage
    for multi-tenancy support
    """
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and not isinstance(user, AnonymousUser):
            _thread_locals.user = user
            # Set organization from user if authenticated
            if hasattr(user, 'organization'):
                _thread_locals.organization = user.organization
        else:
            _thread_locals.user = None
            _thread_locals.organization = None
    
    def process_response(self, request, response):
        # Clean up thread locals
        if hasattr(_thread_locals, 'user'):
            del _thread_locals.user
        if hasattr(_thread_locals, 'organization'):
            del _thread_locals.organization
        return response

