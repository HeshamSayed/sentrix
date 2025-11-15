"""
Policy API views.
"""

import logging
from typing import Optional
from asgiref.sync import sync_to_async
from django.db import models
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.authentication import JWTAuthentication
from core.permissions import check_permission
from .models import Policy
from .services import PolicyManagementService
from .serializers import PolicySerializer, PolicyCreateSerializer, PolicySimulateSerializer

logger = logging.getLogger(__name__)


class PolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Policy management.

    Endpoints:
    - GET /v1/policies/ - List policies
    - POST /v1/policies/ - Create policy
    - GET /v1/policies/{id}/ - Get policy
    - PATCH /v1/policies/{id}/ - Update policy
    - DELETE /v1/policies/{id}/ - Delete policy
    - POST /v1/policies/{id}/enable/ - Enable policy
    - POST /v1/policies/{id}/disable/ - Disable policy
    - POST /v1/policies/{id}/simulate/ - Simulate policy
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PolicySerializer
    lookup_field = 'policy_id'

    def get_queryset(self):
        """
        Get policies filtered by user's organization.
        Optionally filter by app_id.
        """
        user = self.request.user

        # Base filter: user's org
        queryset = Policy.objects.filter(org=user.org)

        # Filter by app if specified
        app_id = self.request.query_params.get('app_id')
        if app_id:
            # Include org-level policies OR app-specific policies
            queryset = queryset.filter(
                models.Q(app_id=app_id) | models.Q(is_org_level=True, app=None)
            )

        # Filter by status
        is_enabled = self.request.query_params.get('is_enabled')
        if is_enabled is not None:
            queryset = queryset.filter(is_enabled=is_enabled.lower() == 'true')

        # Filter by mode
        mode = self.request.query_params.get('mode')
        if mode:
            queryset = queryset.filter(mode=mode)

        return queryset.order_by('priority', '-created_at')

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return PolicyCreateSerializer
        if self.action == 'simulate':
            return PolicySimulateSerializer
        return PolicySerializer

    async def create(self, request, *args, **kwargs):
        """
        Create a new policy.
        Requires 'create_policy' permission.
        """
        # Check permission
        if not check_permission(request.user, 'create_policy'):
            return Response(
                {'detail': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create policy using service
        service = PolicyManagementService()

        try:
            policy = await service.create_policy(
                org_id=str(request.user.org_id),
                user_id=str(request.user.user_id),
                name=serializer.validated_data['name'],
                condition=serializer.validated_data['condition'],
                action=serializer.validated_data['action'],
                app_id=serializer.validated_data.get('app_id'),
                description=serializer.validated_data.get('description', ''),
                mode=serializer.validated_data.get('mode', 'observe'),
                priority=serializer.validated_data.get('priority', 100)
            )

            # Serialize and return
            result_serializer = PolicySerializer(policy)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to create policy: {e}")
            return Response(
                {'detail': f'Failed to create policy: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    async def enable(self, request, policy_id=None):
        """
        Enable a policy.
        Requires 'update_policy' permission.
        """
        if not check_permission(request.user, 'update_policy'):
            return Response(
                {'detail': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Verify policy belongs to user's org
            policy = await sync_to_async(Policy.objects.get)(
                policy_id=policy_id,
                org=request.user.org
            )

            # Enable policy
            service = PolicyManagementService()
            await service.enable_policy(policy_id)

            return Response({
                'message': 'Policy enabled',
                'policy_id': str(policy_id)
            })

        except Policy.DoesNotExist:
            return Response(
                {'detail': 'Policy not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to enable policy: {e}")
            return Response(
                {'detail': f'Failed to enable policy: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    async def disable(self, request, policy_id=None):
        """
        Disable a policy.
        Requires 'update_policy' permission.
        """
        if not check_permission(request.user, 'update_policy'):
            return Response(
                {'detail': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Verify policy belongs to user's org
            policy = await sync_to_async(Policy.objects.get)(
                policy_id=policy_id,
                org=request.user.org
            )

            # Disable policy
            service = PolicyManagementService()
            await service.disable_policy(policy_id)

            return Response({
                'message': 'Policy disabled',
                'policy_id': str(policy_id)
            })

        except Policy.DoesNotExist:
            return Response(
                {'detail': 'Policy not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to disable policy: {e}")
            return Response(
                {'detail': f'Failed to disable policy: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    async def simulate(self, request, policy_id=None):
        """
        Simulate policy impact on historical data.
        Requires 'simulate_policy' permission.
        """
        if not check_permission(request.user, 'simulate_policy'):
            return Response(
                {'detail': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PolicySimulateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days = serializer.validated_data.get('days', 7)

        try:
            # Verify policy belongs to user's org
            policy = await sync_to_async(Policy.objects.get)(
                policy_id=policy_id,
                org=request.user.org
            )

            # Run simulation
            service = PolicyManagementService()
            results = await service.simulate_policy(policy_id, days)

            return Response({
                'policy_id': str(policy_id),
                'policy_name': policy.name,
                'simulation': results
            })

        except Policy.DoesNotExist:
            return Response(
                {'detail': 'Policy not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to simulate policy: {e}")
            return Response(
                {'detail': f'Failed to simulate policy: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class PolicyTestView(View):
    """
    Test policy evaluation against sample events.
    Useful for validating policy conditions before enabling.

    POST /v1/policy/test/
    {
      "condition": {...},
      "events": [...]
    }
    """

    async def post(self, request):
        """Test policy condition against sample events."""
        try:
            import json
            data = json.loads(request.body)

            condition = data.get('condition')
            events = data.get('events', [])

            if not condition or not events:
                return JsonResponse(
                    {'error': 'condition and events are required'},
                    status=400
                )

            # Test evaluation
            from .evaluator import PolicyEvaluator

            evaluator = PolicyEvaluator()
            results = []

            for event in events:
                try:
                    matches = evaluator.evaluate(condition, event)
                    results.append({
                        'event': event,
                        'matches': matches
                    })
                except Exception as e:
                    results.append({
                        'event': event,
                        'error': str(e)
                    })

            return JsonResponse({
                'condition': condition,
                'results': results,
                'total_events': len(events),
                'matched': sum(1 for r in results if r.get('matches'))
            })

        except Exception as e:
            logger.error(f"Policy test error: {e}")
            return JsonResponse(
                {'error': str(e)},
                status=500
            )
