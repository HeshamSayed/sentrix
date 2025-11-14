"""
Policy app configuration.
"""
from django.apps import AppConfig


class PolicyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'policy'
    verbose_name = 'Security Policies'
