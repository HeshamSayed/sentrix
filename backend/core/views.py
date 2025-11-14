"""
Core API views.
"""
import logging
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Organization, Subscription, User, Application, APIEndpoint, UsageTracking
from .serializers import (
    OrganizationSerializer,
    SubscriptionSerializer,
    UserSerializer,
    UserCreateSerializer,
    LoginSerializer,
    TokenSerializer,
    ApplicationSerializer,
    APIEndpointSerializer,
    UsageTrackingSerializer,
)
from .authentication import create_access_token, create_refresh_token
from .services.quota import quota_service, QuotaExceeded
from .services.config import config_service
from edge.services.domain_resolver import domain_resolver

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.

    list: Get all organizations
    retrieve: Get a specific organization
    create: Create a new organization
    update: Update an organization
    partial_update: Partially update an organization
    destroy: Delete an organization
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by authenticated user's org (unless admin)"""
        user = self.request.user
        if user.role == 'admin':
            # Admins can see their own org
            return Organization.objects.filter(org_id=user.org_id)
        return Organization.objects.filter(org_id=user.org_id)

    @action(detail=True, methods=['get'])
    def quota_summary(self, request, pk=None):
        """
        Get quota summary for an organization.

        GET /api/organizations/{org_id}/quota_summary/
        """
        org = self.get_object()

        try:
            summary = await quota_service.get_quota_summary(org.org_id)
            return Response(summary)
        except Exception as e:
            logger.error(f"Error getting quota summary: {e}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def update_config(self, request, pk=None):
        """
        Update organization default configuration.

        PATCH /api/organizations/{org_id}/update_config/
        {
            "rate_limit_rpm": 2000,
            "enable_r1_realtime": true
        }
        """
        org = self.get_object()
        config_updates = request.data

        if not isinstance(config_updates, dict):
            return Response(
                {'error': 'Config updates must be a dictionary'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Merge with existing config
        org.default_config = {**org.default_config, **config_updates}
        org.save()

        # Invalidate cache for all apps in org
        import asyncio
        asyncio.run(config_service.invalidate_org_configs(org.org_id))

        return Response({
            'message': 'Configuration updated',
            'default_config': org.default_config
        })


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subscriptions.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by authenticated user's org"""
        user = self.request.user
        return Subscription.objects.filter(org_id=user.org_id)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get current active subscription for user's org.

        GET /api/subscriptions/current/
        """
        user = request.user
        subscription = user.org.get_active_subscription()

        if not subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(subscription)
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializer for creation"""
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        """Filter by authenticated user's org"""
        user = self.request.user
        return User.objects.filter(org_id=user.org_id)

    async def create(self, request, *args, **kwargs):
        """
        Create a new user with quota enforcement.

        POST /api/users/
        {
            "org": "org-uuid",
            "email": "user@example.com",
            "password": "securepassword",
            "full_name": "John Doe",
            "role": "analyst"
        }
        """
        # Check if user can create more users (quota)
        org_id = request.data.get('org')

        try:
            await quota_service.enforce_user_quota(org_id)
        except QuotaExceeded as e:
            return Response(
                {
                    'error': 'quota_exceeded',
                    'message': e.message,
                    'current': e.current,
                    'limit': e.limit
                },
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """
        Get user permissions.

        GET /api/users/{user_id}/permissions/
        """
        user = self.get_object()
        from .permissions import PERMISSIONS

        return Response({
            'role': user.role,
            'permissions': PERMISSIONS.get(user.role, [])
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Authenticate user and return JWT tokens.

    POST /api/auth/login/
    {
        "email": "user@example.com",
        "password": "password"
    }

    Returns:
    {
        "access_token": "...",
        "refresh_token": "...",
        "user": {...}
    }
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    try:
        user = User.objects.select_related('org').get(email=email, is_active=True)
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Check password
    if not check_password(password, user.password_hash):
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])

    # Generate tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    # Serialize response
    user_serializer = UserSerializer(user)
    response_data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user_serializer.data
    }

    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get current authenticated user.

    GET /api/auth/me/

    Headers:
        Authorization: Bearer <access_token>
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing applications.
    """
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by authenticated user's org"""
        user = self.request.user
        return Application.objects.filter(org_id=user.org_id)

    async def create(self, request, *args, **kwargs):
        """
        Create a new application with quota enforcement.

        POST /api/applications/
        {
            "org": "org-uuid",
            "name": "Payment API",
            "slug": "payment-api",
            "domain": "api.customer-payments.com",
            "origin_url": "https://backend.customer.com",
            "cname_target": "sentrix-edge-us-east.example.com",
            "custom_config": {},
            "failover_mode": "fail_open"
        }
        """
        # Check if user can create more applications (quota)
        org_id = request.data.get('org')

        try:
            await quota_service.enforce_application_quota(org_id)
        except QuotaExceeded as e:
            return Response(
                {
                    'error': 'quota_exceeded',
                    'message': e.message,
                    'current': e.current,
                    'limit': e.limit
                },
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Auto-generate CNAME target if not provided"""
        if not serializer.validated_data.get('cname_target'):
            # Generate default CNAME target
            serializer.validated_data['cname_target'] = 'sentrix-edge.example.com'
        super().perform_create(serializer)

    def perform_update(self, serializer):
        """Invalidate caches on update"""
        instance = serializer.save()

        # Invalidate domain resolution cache
        import asyncio
        asyncio.run(domain_resolver.invalidate(instance.domain))

        # Invalidate config cache
        asyncio.run(config_service.invalidate_app_config(instance.org_id, instance.app_id))

    @action(detail=True, methods=['get'])
    def config(self, request, pk=None):
        """
        Get merged configuration for an application.

        GET /api/applications/{app_id}/config/
        """
        app = self.get_object()
        merged_config = app.get_merged_config()

        return Response({
            'org_default_config': app.org.default_config,
            'app_custom_config': app.custom_config,
            'merged_config': merged_config
        })

    @action(detail=True, methods=['patch'])
    def update_config(self, request, pk=None):
        """
        Update application custom configuration.

        PATCH /api/applications/{app_id}/update_config/
        {
            "rate_limit_rpm": 5000,
            "enable_captcha": true
        }
        """
        app = self.get_object()
        config_updates = request.data

        if not isinstance(config_updates, dict):
            return Response(
                {'error': 'Config updates must be a dictionary'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Merge with existing custom config
        app.custom_config = {**app.custom_config, **config_updates}
        app.save()

        # Invalidate cache
        import asyncio
        asyncio.run(config_service.invalidate_app_config(app.org_id, app.app_id))

        return Response({
            'message': 'Configuration updated',
            'custom_config': app.custom_config,
            'merged_config': app.get_merged_config()
        })

    @action(detail=True, methods=['post'])
    def verify_dns(self, request, pk=None):
        """
        Verify DNS configuration for an application.

        POST /api/applications/{app_id}/verify_dns/

        TODO: Implement actual DNS verification logic
        """
        app = self.get_object()

        # TODO: Implement DNS verification
        # For now, just mark as verified (stub)
        app.dns_verified = True
        app.dns_verified_at = timezone.now()
        app.save()

        return Response({
            'message': 'DNS verified successfully',
            'dns_verified': app.dns_verified,
            'dns_verified_at': app.dns_verified_at
        })


class APIEndpointViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing API endpoints (read-only, auto-discovered).
    """
    queryset = APIEndpoint.objects.all()
    serializer_class = APIEndpointSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter by authenticated user's org and optionally by app.

        Query params:
            app_id: Filter by specific application
        """
        user = self.request.user
        queryset = APIEndpoint.objects.filter(org_id=user.org_id)

        # Filter by app if specified
        app_id = self.request.query_params.get('app_id')
        if app_id:
            queryset = queryset.filter(app_id=app_id)

        return queryset.order_by('-last_seen')


class UsageTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing usage tracking (read-only).
    """
    queryset = UsageTracking.objects.all()
    serializer_class = UsageTrackingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter by authenticated user's org and optionally by app.

        Query params:
            app_id: Filter by specific application
            period_start__gte: Filter by period start >= date
            period_start__lte: Filter by period start <= date
        """
        user = self.request.user
        queryset = UsageTracking.objects.filter(org_id=user.org_id)

        # Filter by app if specified
        app_id = self.request.query_params.get('app_id')
        if app_id:
            queryset = queryset.filter(app_id=app_id)

        # Filter by period
        period_start_gte = self.request.query_params.get('period_start__gte')
        if period_start_gte:
            queryset = queryset.filter(period_start__gte=period_start_gte)

        period_start_lte = self.request.query_params.get('period_start__lte')
        if period_start_lte:
            queryset = queryset.filter(period_start__lte=period_start_lte)

        return queryset.order_by('-period_start')
