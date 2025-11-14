"""
JWT Authentication for Sentrix.
"""
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User

logger = logging.getLogger(__name__)


class JWTAuthentication(BaseAuthentication):
    """
    JWT token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Bearer ".  For example:

        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        try:
            parts = auth_header.split()

            if len(parts) != 2 or parts[0] != self.keyword:
                return None

            token = parts[1]
        except Exception:
            raise AuthenticationFailed('Invalid Authorization header format')

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token: str) -> Tuple[User, dict]:
        """
        Decode JWT token and return user.
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')

        user_id = payload.get('user_id')
        if not user_id:
            raise AuthenticationFailed('Token contains no user_id')

        try:
            user = User.objects.get(user_id=user_id, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found or inactive')

        return (user, payload)

    def authenticate_header(self, request):
        """
        Return WWW-Authenticate header for 401 responses.
        """
        return self.keyword


def create_access_token(user: User) -> str:
    """
    Create JWT access token for user.

    Args:
        user: User instance

    Returns:
        JWT token string
    """
    now = datetime.utcnow()
    expiration = now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME_SECONDS)

    payload = {
        'user_id': str(user.user_id),
        'email': user.email,
        'org_id': str(user.org_id),
        'role': user.role,
        'iat': now,
        'exp': expiration,
        'type': 'access'
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # PyJWT >= 2.0 returns str directly
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return token


def create_refresh_token(user: User) -> str:
    """
    Create JWT refresh token for user.

    Args:
        user: User instance

    Returns:
        JWT refresh token string
    """
    now = datetime.utcnow()
    expiration = now + timedelta(seconds=settings.JWT_REFRESH_TOKEN_LIFETIME_SECONDS)

    payload = {
        'user_id': str(user.user_id),
        'iat': now,
        'exp': expiration,
        'type': 'refresh'
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return token


def verify_token(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload.

    Args:
        token: JWT token string

    Returns:
        Payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        return None
