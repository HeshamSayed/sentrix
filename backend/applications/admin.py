from django.contrib import admin
from .models import Application, Environment


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'environment', 'traffic_mode', 'protected_domain', 'dns_status',
        'edge_hostname', 'is_active', 'is_traffic_enabled'
    )
    list_filter = ('traffic_mode', 'dns_status', 'is_active', 'is_traffic_enabled')
    search_fields = ('name', 'protected_domain', 'edge_hostname', 'api_key')
    readonly_fields = ('api_key', 'dns_verification_token', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic', {
            'fields': ('environment', 'name', 'slug', 'description')
        }),
        ('Routing', {
            'fields': ('base_url', 'target_url', 'traffic_mode')
        }),
        ('DNS Onboarding (Zero Deploy)', {
            'fields': (
                'protected_domain', 'edge_hostname',
                'dns_verification_token', 'dns_status',
            )
        }),
        ('Security & Limits', {
            'fields': (
                'is_active', 'is_traffic_enabled', 'allocated_quota', 'used_quota',
                'rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day',
                'blocked_ips', 'allowed_ips', 'blocked_countries', 'allowed_countries',
                'custom_headers', 'webhook_url'
            )
        }),
        ('Metadata', {
            'fields': ('api_key', 'created_at', 'updated_at')
        })
    )


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active')
    search_fields = ('name', 'organization__name')

