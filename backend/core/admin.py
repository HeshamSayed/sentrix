"""
Django admin configuration for core models.
"""
from django.contrib import admin
from .models import (
    Organization,
    Subscription,
    User,
    Application,
    APIEndpoint,
    AuditLog,
    UsageTracking,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('org_id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug')
        }),
        ('Configuration', {
            'fields': ('default_config',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('org_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('org', 'plan_tier', 'is_active', 'valid_from', 'valid_until')
    list_filter = ('plan_tier', 'is_active')
    search_fields = ('org__name',)
    readonly_fields = ('subscription_id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('org', 'plan_tier', 'is_active')
        }),
        ('Quotas', {
            'fields': (
                'quota_max_applications',
                'quota_max_users',
                'quota_requests_per_month',
            )
        }),
        ('Features', {
            'fields': ('features',),
            'classes': ('collapse',)
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Metadata', {
            'fields': ('subscription_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'org', 'role', 'is_active', 'last_login')
    list_filter = ('role', 'is_active')
    search_fields = ('email', 'full_name', 'org__name')
    readonly_fields = ('user_id', 'created_at', 'updated_at', 'last_login')
    fieldsets = (
        (None, {
            'fields': ('org', 'email', 'full_name')
        }),
        ('Authentication', {
            'fields': ('password_hash', 'role', 'is_active')
        }),
        ('Metadata', {
            'fields': ('user_id', 'last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'org', 'domain', 'dns_verified', 'is_active', 'created_at')
    list_filter = ('dns_verified', 'is_active', 'failover_mode')
    search_fields = ('name', 'slug', 'domain', 'org__name')
    readonly_fields = ('app_id', 'verification_token', 'dns_verified_at', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('org', 'name', 'slug')
        }),
        ('DNS & Origin', {
            'fields': ('domain', 'origin_url', 'cname_target', 'failover_mode')
        }),
        ('Verification', {
            'fields': ('verification_token', 'dns_verified', 'dns_verified_at')
        }),
        ('Configuration', {
            'fields': ('custom_config',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('app_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(APIEndpoint)
class APIEndpointAdmin(admin.ModelAdmin):
    list_display = ('method', 'path_pattern', 'app', 'org', 'request_count', 'last_seen')
    list_filter = ('method', 'org')
    search_fields = ('path_pattern', 'app__name', 'org__name')
    readonly_fields = ('endpoint_id', 'first_seen', 'last_seen', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('org', 'app', 'method', 'path_pattern')
        }),
        ('Schemas', {
            'fields': ('request_schema', 'response_schema'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('owner', 'tags', 'risk_score')
        }),
        ('Stats', {
            'fields': ('request_count', 'first_seen', 'last_seen')
        }),
        ('Metadata', {
            'fields': ('endpoint_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'resource_type', 'org', 'app', 'actor_user', 'timestamp')
    list_filter = ('action', 'resource_type', 'timestamp')
    search_fields = ('action', 'resource_type', 'org__name', 'app__name')
    readonly_fields = ('audit_id', 'timestamp')
    fieldsets = (
        (None, {
            'fields': ('org', 'app', 'actor_user')
        }),
        ('Action', {
            'fields': ('action', 'resource_type', 'resource_id')
        }),
        ('Details', {
            'fields': ('details', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('audit_id', 'timestamp'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Audit logs are immutable, no manual additions
        return False

    def has_delete_permission(self, request, obj=None):
        # Audit logs are immutable
        return False


@admin.register(UsageTracking)
class UsageTrackingAdmin(admin.ModelAdmin):
    list_display = ('org', 'app', 'period_start', 'period_end', 'request_count', 'blocked_count')
    list_filter = ('period_start',)
    search_fields = ('org__name', 'app__name')
    readonly_fields = ('usage_id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('org', 'app')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end')
        }),
        ('Counts', {
            'fields': ('request_count', 'blocked_count', 'r1_invocation_count')
        }),
        ('Metadata', {
            'fields': ('usage_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
