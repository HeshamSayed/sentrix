"""
Django admin configuration for detection models.
"""
from django.contrib import admin
from .models import DetectionEvent


@admin.register(DetectionEvent)
class DetectionEventAdmin(admin.ModelAdmin):
    list_display = ('severity', 'detector_name', 'app', 'org', 'status', 'detected_at')
    list_filter = ('severity', 'detector_type', 'status', 'detected_at')
    search_fields = ('detector_name', 'attack_type', 'app__name', 'org__name')
    readonly_fields = ('detection_id', 'detected_at', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('org', 'app', 'endpoint')
        }),
        ('Detection', {
            'fields': (
                'detector_type',
                'detector_name',
                'severity',
                'attack_type',
            )
        }),
        ('Scores', {
            'fields': ('confidence_score', 'r1_score')
        }),
        ('R1 Explanation', {
            'fields': ('r1_explanation',),
            'classes': ('collapse',)
        }),
        ('Evidence', {
            'fields': ('trigger_event_ids', 'trace_ids', 'client_ip'),
            'classes': ('collapse',)
        }),
        ('Lifecycle', {
            'fields': ('status', 'assigned_to')
        }),
        ('Metadata', {
            'fields': ('detection_id', 'detected_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
