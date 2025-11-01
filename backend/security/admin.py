from django.contrib import admin
from .models import (
    APIBehaviorLog,
    UserBehaviorBaseline,
    AnomalyDetection,
    ThreatResponse,
    SecurityConfiguration,
    BlockedEntity
)


@admin.register(APIBehaviorLog)
class APIBehaviorLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'endpoint', 'method', 'status_code', 'response_time_ms', 'timestamp']
    list_filter = ['method', 'status_code', 'timestamp']
    search_fields = ['user__email', 'endpoint', 'ip_address']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False


@admin.register(UserBehaviorBaseline)
class UserBehaviorBaselineAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'endpoint', 'avg_requests_per_hour', 'samples_count', 'last_calculated']
    list_filter = ['last_calculated']
    search_fields = ['user__email', 'endpoint']
    readonly_fields = ['created_at', 'updated_at', 'last_calculated']


@admin.register(AnomalyDetection)
class AnomalyDetectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'anomaly_type', 'severity', 'risk_score', 'status', 'timestamp']
    list_filter = ['anomaly_type', 'severity', 'status', 'timestamp']
    search_fields = ['title', 'description', 'ip_address', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Detection Details', {
            'fields': ('anomaly_type', 'severity', 'confidence_score', 'risk_score')
        }),
        ('Description', {
            'fields': ('title', 'description', 'indicators')
        }),
        ('Context', {
            'fields': ('user', 'behavior_log', 'ip_address', 'endpoint', 'timestamp')
        }),
        ('Investigation', {
            'fields': ('status', 'investigated_by', 'investigated_at', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ThreatResponse)
class ThreatResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'anomaly', 'action_taken', 'success', 'executed_at']
    list_filter = ['action_taken', 'success', 'executed_at']
    readonly_fields = ['created_at', 'updated_at', 'executed_at']
    
    def has_add_permission(self, request):
        return False


@admin.register(SecurityConfiguration)
class SecurityConfigurationAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_active', 'auto_block_enabled', 'auto_rate_limit_enabled', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Detection Thresholds', {
            'fields': (
                'velocity_threshold_multiplier',
                'anomaly_score_threshold',
                'min_requests_for_baseline',
                'baseline_window_days'
            )
        }),
        ('Response Configuration', {
            'fields': (
                'auto_block_enabled',
                'auto_rate_limit_enabled',
                'block_duration_minutes'
            )
        }),
        ('Alert Configuration', {
            'fields': (
                'alert_on_severity',
                'alert_channels'
            )
        }),
        ('ML Configuration', {
            'fields': (
                'model_update_frequency_minutes',
                'feature_importance_threshold',
                'false_positive_tolerance'
            )
        }),
        ('System', {
            'fields': ('is_active', 'last_updated_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(BlockedEntity)
class BlockedEntityAdmin(admin.ModelAdmin):
    list_display = ['id', 'entity_type', 'entity_value', 'is_permanent', 'blocked_at', 'blocked_until']
    list_filter = ['entity_type', 'is_permanent', 'blocked_at']
    search_fields = ['entity_value', 'reason']
    readonly_fields = ['created_at', 'updated_at', 'blocked_at', 'unblocked_at']
    date_hierarchy = 'blocked_at'
    
    fieldsets = (
        ('Entity Details', {
            'fields': ('entity_type', 'entity_value', 'reason')
        }),
        ('Block Details', {
            'fields': (
                'blocked_at',
                'blocked_until',
                'is_permanent',
                'blocked_by'
            )
        }),
        ('Unblock Details', {
            'fields': ('unblocked_at', 'unblocked_by')
        }),
        ('Related', {
            'fields': ('anomaly',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )

