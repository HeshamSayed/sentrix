"""
Behavioral Anomaly Detection Engine
"""
from django.utils import timezone
from django.db.models import Count, Avg, StdDev, Q
from datetime import timedelta
import math
from .models import (
    APIBehaviorLog,
    UserBehaviorBaseline,
    AnomalyDetection,
    SecurityConfiguration
)


class BehavioralDetector:
    """Main class for detecting behavioral anomalies"""
    
    def __init__(self):
        self.config = self.get_config()
    
    def get_config(self):
        """Get or create security configuration"""
        config, _ = SecurityConfiguration.objects.get_or_create(
            id=1,
            defaults={
                'velocity_threshold_multiplier': 3.0,
                'anomaly_score_threshold': 0.75,
                'min_requests_for_baseline': 100,
                'baseline_window_days': 7,
            }
        )
        return config
    
    def analyze_request(self, behavior_log):
        """Analyze a single request for anomalies"""
        anomalies = []
        
        if not behavior_log.user:
            # Can't analyze without user context for now
            return anomalies
        
        # Get or create baseline
        baseline = self.get_or_create_baseline(behavior_log.user, behavior_log.endpoint)
        
        if baseline.samples_count < self.config.min_requests_for_baseline:
            # Not enough data for baseline yet
            self.update_baseline(baseline, behavior_log)
            return anomalies
        
        # Run detection checks
        anomalies.extend(self.detect_velocity_anomalies(behavior_log, baseline))
        anomalies.extend(self.detect_timing_anomalies(behavior_log, baseline))
        anomalies.extend(self.detect_geographic_anomalies(behavior_log, baseline))
        anomalies.extend(self.detect_sequence_anomalies(behavior_log, baseline))
        anomalies.extend(self.detect_enumeration_attacks(behavior_log))
        
        # Update baseline with new data
        self.update_baseline(baseline, behavior_log)
        
        return anomalies
    
    def get_or_create_baseline(self, user, endpoint):
        """Get or create behavior baseline for user/endpoint"""
        baseline, created = UserBehaviorBaseline.objects.get_or_create(
            user=user,
            endpoint=endpoint,
            defaults={
                'baseline_window_days': self.config.baseline_window_days
            }
        )
        return baseline
    
    def detect_velocity_anomalies(self, behavior_log, baseline):
        """Detect unusual request velocity"""
        anomalies = []
        now = timezone.now()
        
        # Check requests in last hour
        hour_ago = now - timedelta(hours=1)
        recent_requests = APIBehaviorLog.objects.filter(
            user=behavior_log.user,
            endpoint=behavior_log.endpoint,
            timestamp__gte=hour_ago
        ).count()
        
        # Compare to baseline
        threshold = baseline.avg_requests_per_hour * self.config.velocity_threshold_multiplier
        
        if recent_requests > threshold and threshold > 0:
            confidence = min((recent_requests / threshold - 1.0), 1.0)
            risk_score = confidence * 70  # High risk
            
            anomalies.append({
                'type': 'VELOCITY',
                'severity': self.calculate_severity(risk_score),
                'confidence': confidence,
                'risk_score': risk_score,
                'title': f'Unusual Request Velocity Detected',
                'description': f'User made {recent_requests} requests in last hour (normal: {baseline.avg_requests_per_hour:.1f})',
                'indicators': {
                    'current_requests': recent_requests,
                    'baseline_requests': baseline.avg_requests_per_hour,
                    'threshold': threshold,
                    'multiplier': self.config.velocity_threshold_multiplier
                }
            })
        
        return anomalies
    
    def detect_timing_anomalies(self, behavior_log, baseline):
        """Detect unusual timing patterns"""
        anomalies = []
        
        if not baseline.typical_hours:
            return anomalies
        
        current_hour = behavior_log.timestamp.hour
        
        if current_hour not in baseline.typical_hours:
            # Activity outside typical hours
            confidence = 0.6
            risk_score = 40
            
            anomalies.append({
                'type': 'TIMING',
                'severity': 'MEDIUM',
                'confidence': confidence,
                'risk_score': risk_score,
                'title': 'Unusual Activity Time',
                'description': f'API access at {current_hour}:00 (typical hours: {baseline.typical_hours})',
                'indicators': {
                    'current_hour': current_hour,
                    'typical_hours': baseline.typical_hours
                }
            })
        
        return anomalies
    
    def detect_geographic_anomalies(self, behavior_log, baseline):
        """Detect impossible geographic patterns"""
        anomalies = []
        
        if not behavior_log.geo_country or not baseline.common_countries:
            return anomalies
        
        if behavior_log.geo_country not in baseline.common_countries:
            # Check recent locations
            recent = APIBehaviorLog.objects.filter(
                user=behavior_log.user,
                timestamp__gte=timezone.now() - timedelta(hours=1)
            ).exclude(
                geo_country=''
            ).values_list('geo_country', flat=True).distinct()
            
            if len(recent) > 3:
                # Multiple countries in short time - impossible travel
                confidence = 0.9
                risk_score = 85
                
                anomalies.append({
                    'type': 'GEOGRAPHIC',
                    'severity': 'CRITICAL',
                    'confidence': confidence,
                    'risk_score': risk_score,
                    'title': 'Impossible Geographic Pattern',
                    'description': f'Access from {len(recent)} countries in 1 hour',
                    'indicators': {
                        'countries': list(recent),
                        'current_country': behavior_log.geo_country,
                        'typical_countries': baseline.common_countries
                    }
                })
        
        return anomalies
    
    def detect_sequence_anomalies(self, behavior_log, baseline):
        """Detect unusual API call sequences"""
        anomalies = []
        
        # Get recent sequence of endpoints
        recent_sequence = list(APIBehaviorLog.objects.filter(
            user=behavior_log.user,
            session_id=behavior_log.session_id,
            timestamp__gte=timezone.now() - timedelta(minutes=10)
        ).order_by('timestamp').values_list('endpoint', flat=True))
        
        if len(recent_sequence) > 20:
            # Very rapid sequential calls - potential scraping
            confidence = 0.8
            risk_score = 75
            
            anomalies.append({
                'type': 'SEQUENCE',
                'severity': 'HIGH',
                'confidence': confidence,
                'risk_score': risk_score,
                'title': 'Potential Data Scraping',
                'description': f'{len(recent_sequence)} sequential API calls in 10 minutes',
                'indicators': {
                    'sequence_length': len(recent_sequence),
                    'unique_endpoints': len(set(recent_sequence)),
                    'recent_endpoints': recent_sequence[-10:]
                }
            })
        
        return anomalies
    
    def detect_enumeration_attacks(self, behavior_log):
        """Detect BOLA/IDOR enumeration patterns"""
        anomalies = []
        
        # Check for sequential ID patterns in recent requests
        if '/{id}' in behavior_log.endpoint:
            recent_similar = APIBehaviorLog.objects.filter(
                user=behavior_log.user,
                endpoint=behavior_log.endpoint,
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            ).count()
            
            if recent_similar > 50:
                # Rapid access to same endpoint with different IDs
                confidence = 0.85
                risk_score = 80
                
                anomalies.append({
                    'type': 'ENUMERATION',
                    'severity': 'HIGH',
                    'confidence': confidence,
                    'risk_score': risk_score,
                    'title': 'Potential BOLA/IDOR Attack',
                    'description': f'{recent_similar} requests to {behavior_log.endpoint} in 5 minutes',
                    'indicators': {
                        'request_count': recent_similar,
                        'endpoint': behavior_log.endpoint,
                        'time_window': '5 minutes'
                    }
                })
        
        return anomalies
    
    def update_baseline(self, baseline, behavior_log):
        """Update baseline with new behavior data"""
        window_start = timezone.now() - timedelta(days=baseline.baseline_window_days)
        
        # Calculate statistics from recent data
        recent_logs = APIBehaviorLog.objects.filter(
            user=baseline.user,
            endpoint=baseline.endpoint,
            timestamp__gte=window_start
        )
        
        stats = recent_logs.aggregate(
            count=Count('id'),
            avg_response_time=Avg('response_time_ms'),
            std_response_time=StdDev('response_time_ms'),
            avg_request_size=Avg('request_size_bytes'),
            avg_response_size=Avg('response_size_bytes'),
        )
        
        # Calculate hourly/daily averages
        days_in_window = (timezone.now() - window_start).days or 1
        total_requests = stats['count'] or 0
        
        baseline.avg_requests_per_day = total_requests / days_in_window
        baseline.avg_requests_per_hour = total_requests / (days_in_window * 24)
        baseline.avg_response_time_ms = stats['avg_response_time'] or 0
        baseline.std_response_time_ms = stats['std_response_time'] or 0
        baseline.avg_request_size_bytes = stats['avg_request_size'] or 0
        baseline.avg_response_size_bytes = stats['avg_response_size'] or 0
        baseline.samples_count = total_requests
        
        # Extract common patterns
        baseline.common_endpoints = list(
            recent_logs.values('endpoint')
            .annotate(count=Count('id'))
            .order_by('-count')
            .values_list('endpoint', flat=True)[:10]
        )
        
        baseline.typical_hours = list(
            recent_logs.values_list('timestamp__hour', flat=True)
            .distinct()
        )
        
        if recent_logs.exclude(geo_country='').exists():
            baseline.common_countries = list(
                recent_logs.exclude(geo_country='')
                .values_list('geo_country', flat=True)
                .distinct()[:5]
            )
        
        baseline.save()
    
    def calculate_severity(self, risk_score):
        """Calculate severity level from risk score"""
        if risk_score >= 80:
            return 'CRITICAL'
        elif risk_score >= 60:
            return 'HIGH'
        elif risk_score >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def create_anomaly_record(self, behavior_log, anomaly_data):
        """Create anomaly detection record"""
        anomaly = AnomalyDetection.objects.create(
            user=behavior_log.user,
            behavior_log=behavior_log,
            anomaly_type=anomaly_data['type'],
            severity=anomaly_data['severity'],
            confidence_score=anomaly_data['confidence'],
            risk_score=anomaly_data['risk_score'],
            title=anomaly_data['title'],
            description=anomaly_data['description'],
            indicators=anomaly_data['indicators'],
            ip_address=behavior_log.ip_address,
            endpoint=behavior_log.endpoint,
            timestamp=behavior_log.timestamp,
        )
        return anomaly

