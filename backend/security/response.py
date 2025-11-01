"""
Automated threat response handler
"""
from django.utils import timezone
from datetime import timedelta
from .models import ThreatResponse, BlockedEntity, SecurityConfiguration


class ThreatResponseHandler:
    """Handles automated responses to detected threats"""
    
    def __init__(self):
        self.config = self.get_config()
    
    def get_config(self):
        """Get security configuration"""
        config, _ = SecurityConfiguration.objects.get_or_create(id=1)
        return config
    
    def handle_anomaly(self, anomaly):
        """Determine and execute appropriate response"""
        action = self.determine_action(anomaly)
        
        if action:
            self.execute_action(anomaly, action)
    
    def determine_action(self, anomaly):
        """Determine what action to take based on anomaly"""
        severity = anomaly.severity
        risk_score = anomaly.risk_score
        
        # Low severity - just log
        if severity == 'LOW':
            return 'LOG'
        
        # Medium severity - rate limit
        if severity == 'MEDIUM':
            if self.config.auto_rate_limit_enabled:
                return 'RATE_LIMIT'
            else:
                return 'ALERT'
        
        # High severity - throttle or challenge
        if severity == 'HIGH':
            if risk_score > 70:
                return 'BLOCK_TEMPORARY'
            else:
                return 'THROTTLE'
        
        # Critical severity - block
        if severity == 'CRITICAL':
            if self.config.auto_block_enabled:
                return 'BLOCK_TEMPORARY'
            else:
                return 'ALERT'
        
        return 'LOG'
    
    def execute_action(self, anomaly, action):
        """Execute the determined action"""
        try:
            if action == 'LOG':
                self.log_only(anomaly)
            
            elif action == 'ALERT':
                self.send_alert(anomaly)
            
            elif action == 'RATE_LIMIT':
                self.apply_rate_limit(anomaly)
            
            elif action == 'THROTTLE':
                self.throttle_requests(anomaly)
            
            elif action == 'BLOCK_TEMPORARY':
                self.block_temporary(anomaly)
            
            elif action == 'BLOCK_PERMANENT':
                self.block_permanent(anomaly)
            
            # Record the response
            ThreatResponse.objects.create(
                anomaly=anomaly,
                action_taken=action,
                duration_minutes=self.config.block_duration_minutes if 'BLOCK' in action else None,
                success=True
            )
            
        except Exception as e:
            # Record failed response
            ThreatResponse.objects.create(
                anomaly=anomaly,
                action_taken=action,
                success=False,
                error_message=str(e)
            )
    
    def log_only(self, anomaly):
        """Just log the anomaly, no action"""
        print(f"[SECURITY] Anomaly detected: {anomaly.title}")
    
    def send_alert(self, anomaly):
        """Send alert to security team"""
        # This could integrate with Slack, PagerDuty, etc.
        print(f"[ALERT] {anomaly.severity} threat: {anomaly.title}")
        
        # TODO: Implement actual alerting
        # - Send Slack message
        # - Send email
        # - Create PagerDuty incident
        # - Post to webhook
    
    def apply_rate_limit(self, anomaly):
        """Apply rate limiting to the user/IP"""
        # This would integrate with API gateway/load balancer
        print(f"[ACTION] Applying rate limit for {anomaly.ip_address}")
        
        # TODO: Implement rate limiting
        # - Update Redis cache with rate limit rules
        # - Configure Kong/NGINX rate limits
        # - Apply application-level throttling
    
    def throttle_requests(self, anomaly):
        """Slow down requests from this source"""
        print(f"[ACTION] Throttling requests from {anomaly.ip_address}")
        
        # Similar to rate limiting but more aggressive
        # TODO: Implement throttling mechanism
    
    def block_temporary(self, anomaly):
        """Temporarily block the user/IP"""
        blocked_until = timezone.now() + timedelta(
            minutes=self.config.block_duration_minutes
        )
        
        # Block IP address
        BlockedEntity.objects.create(
            entity_type='IP',
            entity_value=anomaly.ip_address,
            reason=anomaly.title,
            blocked_until=blocked_until,
            is_permanent=False,
            anomaly=anomaly
        )
        
        # Also block user if identified
        if anomaly.user:
            BlockedEntity.objects.create(
                entity_type='USER',
                entity_value=str(anomaly.user.id),
                reason=anomaly.title,
                blocked_until=blocked_until,
                is_permanent=False,
                anomaly=anomaly
            )
        
        print(f"[ACTION] Blocked {anomaly.ip_address} until {blocked_until}")
    
    def block_permanent(self, anomaly):
        """Permanently block the user/IP"""
        # Block IP address
        BlockedEntity.objects.create(
            entity_type='IP',
            entity_value=anomaly.ip_address,
            reason=anomaly.title,
            is_permanent=True,
            anomaly=anomaly
        )
        
        # Also block user if identified
        if anomaly.user:
            BlockedEntity.objects.create(
                entity_type='USER',
                entity_value=str(anomaly.user.id),
                reason=anomaly.title,
                is_permanent=True,
                anomaly=anomaly
            )
        
        print(f"[ACTION] Permanently blocked {anomaly.ip_address}")

