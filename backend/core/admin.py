"""
Django admin configuration for core models
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import SubscriptionPlan, Subscription, OnboardingSession


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """Admin interface for Subscription Plans"""
    
    list_display = [
        'name',
        'plan_type',
        'monthly_price_display',
        'annual_price_display',
        'discount_display',
        'max_requests_display',
        'max_applications',
        'is_active',
        'is_public'
    ]
    
    list_filter = ['is_active', 'is_public', 'plan_type']
    
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'plan_type', 'description')
        }),
        ('Pricing', {
            'fields': (
                'monthly_price',
                'annual_discount_percentage',
                'annual_price',
            ),
            'description': 'Annual price is auto-calculated based on monthly price and discount percentage. Set discount to 0 to disable annual discount.'
        }),
        ('Quotas & Limits', {
            'fields': (
                'max_requests_per_month',
                'max_applications',
                'max_users',
                'max_environments'
            )
        }),
        ('Features', {
            'fields': (
                'behavioral_analysis',
                'real_time_blocking',
                'advanced_analytics',
                'custom_rules',
                'priority_support',
                'dedicated_resources',
                'sla_guarantee'
            ),
            'classes': ('collapse',)
        }),
        ('Availability', {
            'fields': ('is_active', 'is_public')
        }),
    )
    
    readonly_fields = []
    
    def monthly_price_display(self, obj):
        return f"${obj.monthly_price}/mo"
    monthly_price_display.short_description = 'Monthly Price'
    
    def annual_price_display(self, obj):
        calculated = obj.calculate_annual_price()
        savings = obj.get_annual_savings()
        if savings > 0:
            return format_html(
                '<strong>${}</strong>/yr <span style="color: green;">(Save ${})</span>',
                calculated,
                savings
            )
        return f"${calculated}/yr"
    annual_price_display.short_description = 'Annual Price'
    
    def discount_display(self, obj):
        if obj.annual_discount_percentage > 0:
            months_free = (obj.annual_discount_percentage / 100) * 12
            return format_html(
                '<strong style="color: green;">{:.1f}%</strong> ({:.1f} months free)',
                obj.annual_discount_percentage,
                months_free
            )
        return format_html('<span style="color: gray;">No discount</span>')
    discount_display.short_description = 'Annual Discount'
    
    def max_requests_display(self, obj):
        requests = obj.max_requests_per_month
        if requests >= 1_000_000:
            return f"{requests / 1_000_000:.0f}M"
        elif requests >= 1_000:
            return f"{requests / 1_000:.0f}K"
        return str(requests)
    max_requests_display.short_description = 'Max Requests/mo'
    
    def save_model(self, request, obj, form, change):
        """Auto-calculate annual price on save"""
        if obj.annual_discount_percentage > 0:
            obj.annual_price = obj.calculate_annual_price()
        super().save_model(request, obj, form, change)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin interface for Subscriptions"""
    
    list_display = [
        'organization',
        'plan',
        'status',
        'billing_cycle',
        'start_date',
        'auto_renew',
        'usage_display'
    ]
    
    list_filter = ['status', 'billing_cycle', 'auto_renew', 'plan']
    
    search_fields = ['organization__name', 'stripe_customer_id']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Subscription Info', {
            'fields': ('organization', 'plan', 'status', 'billing_cycle', 'auto_renew')
        }),
        ('Trial Period', {
            'fields': ('trial_start_date', 'trial_end_date'),
            'classes': ('collapse',)
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'end_date', 'current_period_start', 'current_period_end')
        }),
        ('Usage Tracking', {
            'fields': ('current_period_requests',)
        }),
        ('Billing', {
            'fields': (
                'stripe_customer_id',
                'stripe_subscription_id',
                'last_payment_date',
                'next_payment_date'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def usage_display(self, obj):
        percentage = (obj.current_period_requests / obj.plan.max_requests_per_month) * 100
        color = 'green' if percentage < 70 else 'orange' if percentage < 90 else 'red'
        return format_html(
            '<span style="color: {};">{:,} / {:,} ({:.1f}%)</span>',
            color,
            obj.current_period_requests,
            obj.plan.max_requests_per_month,
            percentage
        )
    usage_display.short_description = 'Usage'


@admin.register(OnboardingSession)
class OnboardingSessionAdmin(admin.ModelAdmin):
    """Admin interface for Onboarding Sessions"""
    
    list_display = [
        'user',
        'organization',
        'status',
        'company_name',
        'created_at',
        'completed_at'
    ]
    
    list_filter = ['status', 'created_at']
    
    search_fields = ['user__email', 'company_name', 'organization__name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User & Organization', {
            'fields': ('user', 'organization')
        }),
        ('Status', {
            'fields': ('status', 'completed_at')
        }),
        ('Company Info', {
            'fields': ('company_name', 'company_size', 'use_case')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

