"""
Onboarding API endpoints for self-service customer registration
Implements: Organization → Environment → Application hierarchy
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import secrets

from organizations.models import Organization
from applications.models import Environment, Application
from core.models import SubscriptionPlan, Subscription, OnboardingSession
from core.serializers.onboarding import (
    SignUpSerializer,
    SubscriptionPlanSerializer,
    OnboardingSerializer,
    QuickStartSerializer,
    EnvironmentDetailSerializer,
    ApplicationDetailSerializer
)

User = get_user_model()


class OnboardingViewSet(viewsets.ViewSet):
    """
    Onboarding API for self-service customer registration
    
    Complete flow:
    1. Sign up (create account)
    2. View available plans
    3. Quick start (create organization, environments, and applications)
    4. Get API keys and integration guide
    5. Test integration
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def signup(self, request):
        """
        Step 1: User registration
        
        POST /api/onboarding/signup/
        {
            "email": "user@example.com",
            "password": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
            "company_name": "Acme Inc"
        }
        """
        serializer = SignUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password'],
                    first_name=serializer.validated_data.get('first_name', ''),
                    last_name=serializer.validated_data.get('last_name', ''),
                    role='ADMIN'
                )
                
                # Create onboarding session
                onboarding = OnboardingSession.objects.create(
                    user=user,
                    status='started',
                    company_name=serializer.validated_data.get('company_name', ''),
                    company_size=serializer.validated_data.get('company_size', ''),
                    use_case=serializer.validated_data.get('use_case', '')
                )
                
                # Generate authentication token
                from rest_framework.authtoken.models import Token
                token, _ = Token.objects.get_or_create(user=user)
                
                return Response({
                    'message': 'Account created successfully',
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    },
                    'token': token.key,
                    'onboarding_session_id': str(onboarding.id)
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'error': 'registration_failed',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def plans(self, request):
        """
        Get available subscription plans
        
        GET /api/onboarding/plans/
        """
        plans = SubscriptionPlan.objects.filter(is_active=True, is_public=True)
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response({'plans': serializer.data})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def quick_start(self, request):
        """
        Step 2: Quick start setup (all in one)
        Creates organization, subscription, environments, and applications
        
        POST /api/onboarding/quick_start/
        {
            "organization_name": "TODO App Inc",
            "plan_type": "starter",
            "environments": [
                {
                    "name": "Production",
                    "environment_type": "production",
                    "description": "Production environment",
                    "applications": [
                        {
                            "name": "TODO App API",
                            "description": "Main TODO application backend",
                            "base_url": "https://todo.com",
                            "target_url": "https://api.todo.com",
                            "framework": "Flask",
                            "language": "Python"
                        }
                    ]
                },
                {
                    "name": "Staging",
                    "environment_type": "staging",
                    "applications": [
                        {
                            "name": "TODO App API Staging",
                            "base_url": "https://staging.todo.com",
                            "target_url": "https://api-staging.todo.com"
                        }
                    ]
                }
            ]
        }
        """
        serializer = QuickStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                user = request.user
                
                # 1. Create Organization
                org_name = serializer.validated_data['organization_name']
                organization = Organization.objects.create(
                    name=org_name,
                    slug=slugify(org_name),
                    settings={'onboarded_via': 'quick_start'}
                )
                
                # Link user to organization
                organization.users.add(user)
                organization.save()
                
                # 2. Get subscription plan
                plan_type = serializer.validated_data['plan_type']
                plan = SubscriptionPlan.objects.get(plan_type=plan_type, is_active=True)
                
                # 3. Create subscription with trial
                now = timezone.now()
                trial_end = now + timedelta(days=14)
                
                subscription = Subscription.objects.create(
                    organization=organization,
                    plan=plan,
                    status='trial',
                    trial_start_date=now,
                    trial_end_date=trial_end,
                    start_date=now,
                    current_period_start=now,
                    current_period_end=trial_end,
                )
                
                # 4. Create Environments and Applications
                created_environments = []
                created_applications = []
                
                for env_data in serializer.validated_data['environments']:
                    # Determine environment quota
                    # If user provides quota, use it. Otherwise, auto-allocate or leave for dashboard configuration
                    env_quota = env_data.get('allocated_quota')
                    if env_quota is None:
                        # Auto-allocate equally if not specified
                        env_quota = plan.max_requests_per_month // len(serializer.validated_data['environments'])
                    
                    # Create environment
                    environment = Environment.objects.create(
                        organization=organization,
                        name=env_data['name'],
                        environment_type=env_data['environment_type'],
                        slug=slugify(f"{org_name}-{env_data['name']}"),
                        description=env_data.get('description', ''),
                        max_applications=plan.max_applications,
                        allocated_quota=env_quota
                    )
                    created_environments.append(environment)
                    
                    # Create applications under this environment
                    for app_data in env_data['applications']:
                        # Determine application quota
                        # If user provides quota, use it. Otherwise, auto-allocate or leave for dashboard configuration
                        app_quota = app_data.get('allocated_quota')
                        if app_quota is None and environment.allocated_quota:
                            # Auto-allocate equally among apps if not specified
                            app_quota = environment.allocated_quota // len(env_data['applications'])
                        elif app_quota is None:
                            # No quota specified at all - user will configure in dashboard
                            app_quota = 0
                        
                        # Get rate limits (optional)
                        rate_per_min = app_data.get('rate_limit_per_minute', 1000)
                        rate_per_hour = app_data.get('rate_limit_per_hour', 10000)
                        rate_per_day = app_data.get('rate_limit_per_day', 100000)
                        
                        application = Application.objects.create(
                            environment=environment,
                            name=app_data['name'],
                            slug=slugify(app_data['name']),
                            description=app_data.get('description', ''),
                            base_url=app_data['base_url'],
                            target_url=app_data['target_url'],
                            framework=app_data.get('framework', ''),
                            language=app_data.get('language', ''),
                            allocated_quota=app_quota,
                            rate_limit_per_minute=rate_per_min,
                            rate_limit_per_hour=rate_per_hour,
                            rate_limit_per_day=rate_per_day,
                            is_active=True,
                            is_traffic_enabled=True
                        )
                        created_applications.append(application)
                
                # 5. Update onboarding session
                onboarding = OnboardingSession.objects.filter(user=user).order_by('-created_at').first()
                if onboarding:
                    onboarding.organization = organization
                    onboarding.status = 'completed'
                    onboarding.completed_at = timezone.now()
                    onboarding.save()
                
                # 6. Prepare response
                return Response({
                    'message': 'Organization setup completed successfully!',
                    'organization': {
                        'id': str(organization.id),
                        'name': organization.name,
                        'slug': organization.slug,
                    },
                    'subscription': {
                        'plan_type': plan.plan_type,
                        'plan_name': plan.name,
                        'status': subscription.status,
                        'trial_end_date': subscription.trial_end_date.isoformat(),
                        'max_requests': plan.max_requests_per_month,
                    },
                    'environments': EnvironmentDetailSerializer(created_environments, many=True).data,
                    'applications': ApplicationDetailSerializer(created_applications, many=True).data,
                    'next_steps': [
                        '1. Save your API keys securely',
                        f'2. Update your application to use SENTRIX Edge: http://your-sentrix-domain:8001',
                        '3. Add X-SENTRIX-Key header with your API key',
                        '4. Test your integration',
                        '5. Monitor your dashboard for security insights'
                    ]
                }, status=status.HTTP_201_CREATED)
                
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'error': 'invalid_plan',
                'message': f'Subscription plan "{serializer.validated_data["plan_type"]}" not found'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'setup_failed',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def test_integration(self, request):
        """
        Test API key integration
        
        POST /api/onboarding/test_integration/
        {
            "api_key": "sentrix_live_xxxxx",
            "test_url": "/api/test"
        }
        """
        api_key = request.data.get('api_key')
        
        if not api_key:
            return Response({
                'error': 'missing_api_key',
                'message': 'API key is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            application = Application.objects.get(api_key=api_key)
            
            return Response({
                'success': True,
                'message': 'API key is valid',
                'application': {
                    'name': application.name,
                    'environment': application.environment.name,
                    'organization': application.organization.name,
                    'is_active': application.is_active,
                    'remaining_quota': application.remaining_quota
                }
            })
        except Application.DoesNotExist:
            return Response({
                'error': 'invalid_api_key',
                'message': 'API key not found or invalid'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request):
        """
        Mark onboarding as complete
        
        POST /api/onboarding/complete/
        """
        onboarding = OnboardingSession.objects.filter(
            user=request.user
        ).order_by('-created_at').first()
        
        if not onboarding:
            return Response({
                'error': 'no_onboarding_session',
                'message': 'No onboarding session found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        onboarding.status = 'completed'
        onboarding.completed_at = timezone.now()
        onboarding.save()
        
        return Response({
            'message': 'Onboarding completed successfully',
            'onboarding': OnboardingSerializer(onboarding).data
        })
