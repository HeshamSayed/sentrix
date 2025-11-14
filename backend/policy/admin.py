"""
Django admin configuration for policy models.
"""
from django.contrib import admin
from .models import Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'org', 'app', 'mode', 'is_enabled', 'priority', 'created_at')
    list_filter = ('mode', 'is_enabled', 'is_org_level')
    search_fields = ('name', 'description', 'org__name', 'app__name')
    readonly_fields = ('policy_id', 'created_at', 'updated_at', 'last_simulation_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Scope', {
            'fields': ('org', 'app', 'is_org_level')
        }),
        ('Condition', {
            'fields': ('condition',),
            'description': 'Policy condition as JSON DSL'
        }),
        ('Action', {
            'fields': ('action',),
            'description': 'Action to take when condition matches'
        }),
        ('State', {
            'fields': ('mode', 'is_enabled', 'priority')
        }),
        ('Simulation', {
            'fields': ('last_simulation_at', 'last_simulation_result'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('policy_id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
