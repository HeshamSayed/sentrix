import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .models import APIBehaviorLog
from .tasks import analyze_request_behavior
import uuid


class BehavioralSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to capture API traffic data for behavioral analysis
    """
    
    EXCLUDED_PATHS = [
        '/admin/',
        '/static/',
        '/media/',
        '/__debug__/',
        '/api/schema/',
        '/api/docs/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def should_log_request(self, request):
        """Determine if request should be logged for analysis"""
        path = request.path
        
        # Skip excluded paths
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return False
        
        # Only log API endpoints
        if not path.startswith('/api/'):
            return False
        
        return True
    
    def process_request(self, request):
        """Mark request start time"""
        request._behavioral_start_time = time.time()
        
        # Generate or retrieve session ID
        if not hasattr(request, 'session') or not request.session.session_key:
            request._behavioral_session_id = str(uuid.uuid4())
        else:
            request._behavioral_session_id = request.session.session_key
        
        return None
    
    def process_response(self, request, response):
        """Log request details after response"""
        
        if not self.should_log_request(request):
            return response
        
        try:
            # Calculate response time
            if hasattr(request, '_behavioral_start_time'):
                response_time_ms = (time.time() - request._behavioral_start_time) * 1000
            else:
                response_time_ms = 0
            
            # Extract user
            user = request.user if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) else None
            
            # Get IP address
            ip_address = self.get_client_ip(request)
            
            # Get request/response sizes
            request_size = len(request.body) if hasattr(request, 'body') else 0
            response_size = len(response.content) if hasattr(response, 'content') else 0
            
            # Extract query parameters
            query_params = dict(request.GET) if request.GET else {}
            
            # Create behavior log
            behavior_log = APIBehaviorLog.objects.create(
                user=user,
                session_id=getattr(request, '_behavioral_session_id', ''),
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                method=request.method,
                endpoint=self.normalize_endpoint(request.path),
                full_path=request.get_full_path()[:500],
                query_params=query_params,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                request_size_bytes=request_size,
                response_size_bytes=response_size,
                auth_method=self.detect_auth_method(request),
            )
            
            # Trigger async analysis
            analyze_request_behavior.delay(behavior_log.id)
            
        except Exception as e:
            # Don't break the request if logging fails
            print(f"Behavioral logging error: {e}")
        
        return response
    
    def get_client_ip(self, request):
        """Extract real client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def normalize_endpoint(self, path):
        """Normalize endpoint by replacing IDs with placeholders"""
        import re
        # Replace UUIDs
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )
        # Replace numeric IDs
        path = re.sub(r'/\d+/', '/{id}/', path)
        return path
    
    def detect_auth_method(self, request):
        """Detect authentication method used"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            return 'JWT'
        elif auth_header.startswith('Token '):
            return 'Token'
        elif auth_header.startswith('Basic '):
            return 'Basic'
        elif hasattr(request, 'session') and request.session.session_key:
            return 'Session'
        
        return 'None'


class BlockedEntityMiddleware(MiddlewareMixin):
    """
    Middleware to block requests from blocked entities
    """
    
    def process_request(self, request):
        """Check if request should be blocked"""
        from django.http import JsonResponse
        from django.utils import timezone
        from django.db import models as django_models
        from .models import BlockedEntity
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        
        # Check if IP is blocked
        now = timezone.now()
        blocked = BlockedEntity.objects.filter(
            entity_type='IP',
            entity_value=ip,
        ).filter(
            django_models.Q(is_permanent=True) | 
            django_models.Q(blocked_until__gt=now, blocked_until__isnull=False)
        ).first()
        
        if blocked:
            return JsonResponse({
                'error': 'Access Denied',
                'message': 'Your access has been temporarily restricted due to suspicious activity.',
                'reason': 'Security policy violation',
                'contact': 'support@sentrix.com'
            }, status=403)
        
        # Check if user is blocked (if authenticated)
        if hasattr(request, 'user') and request.user.is_authenticated:
            blocked = BlockedEntity.objects.filter(
                entity_type='USER',
                entity_value=str(request.user.id),
            ).filter(
                django_models.Q(is_permanent=True) | 
                django_models.Q(blocked_until__gt=now, blocked_until__isnull=False)
            ).first()
            
            if blocked:
                return JsonResponse({
                    'error': 'Access Denied',
                    'message': 'Your account has been suspended due to suspicious activity.',
                    'reason': blocked.reason,
                    'contact': 'support@sentrix.com'
                }, status=403)
        
        return None

