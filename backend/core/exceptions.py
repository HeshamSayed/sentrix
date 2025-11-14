"""
Custom exception handling for Sentrix.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from core.services.quota import QuotaExceeded


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.
    Handles Sentrix-specific exceptions.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Handle QuotaExceeded
    if isinstance(exc, QuotaExceeded):
        return Response(
            {
                'error': 'quota_exceeded',
                'message': exc.message,
                'quota_type': exc.quota_type,
                'current': exc.current,
                'limit': exc.limit
            },
            status=status.HTTP_403_FORBIDDEN
        )

    return response
