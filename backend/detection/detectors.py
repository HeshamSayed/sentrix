"""
Threat detectors for Sentrix.
Each detector analyzes events and returns detection results.
"""
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class DetectorResult:
    """Result from a detector"""

    def __init__(
        self,
        is_threat: bool,
        confidence_score: float,
        detector_type: str,
        detector_name: str,
        severity: str,
        attack_type: Optional[str] = None,
        explanation: str = "",
        evidence: Optional[List] = None
    ):
        self.is_threat = is_threat
        self.confidence_score = confidence_score
        self.detector_type = detector_type
        self.detector_name = detector_name
        self.severity = severity
        self.attack_type = attack_type
        self.explanation = explanation
        self.evidence = evidence or []


class SQLInjectionDetector:
    """
    Detects SQL injection attempts in request parameters.
    Rule-based detector using pattern matching.
    """

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|UNION|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b.*\b(FROM|INTO|WHERE|TABLE|DATABASE)\b)",
        r"(--|#|/\*|\*/)",  # SQL comments
        r"('\s*(OR|AND)\s*'?\d+)",  # OR 1=1, AND 1=1
        r"('\s*OR\s*'[^']*'\s*=\s*')",  # OR 'x'='x'
        r"(;.*\b(DROP|DELETE|UPDATE|INSERT)\b)",  # Statement chaining
        r"(\bUNION\b.*\bSELECT\b)",  # UNION SELECT
        r"(\bOR\b.*\bSLEEP\b)",  # Time-based blind SQLi
    ]

    def __init__(self):
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_PATTERNS]

    def detect(self, event: Dict) -> Optional[DetectorResult]:
        """
        Analyze event for SQL injection attempts.

        Args:
            event: Enriched event dict with request_meta

        Returns:
            DetectorResult if SQL injection detected, None otherwise
        """
        request_meta = event.get('request_meta', {})

        # Check query parameters
        query_params = request_meta.get('query_params', {})
        body = request_meta.get('body', {})

        # Combine all input values
        all_values = []

        if isinstance(query_params, dict):
            all_values.extend(str(v) for v in query_params.values())

        if isinstance(body, dict):
            all_values.extend(str(v) for v in body.values())

        # Check each value against patterns
        matches = []
        for value in all_values:
            for pattern in self.patterns:
                if pattern.search(value):
                    matches.append({
                        'value': value[:100],  # Truncate for logging
                        'pattern': pattern.pattern
                    })

        if matches:
            confidence = min(0.95, 0.6 + (len(matches) * 0.1))

            return DetectorResult(
                is_threat=True,
                confidence_score=confidence,
                detector_type='rule_based',
                detector_name='SQL Injection Detector',
                severity='high',
                attack_type='sqli',
                explanation=f"Detected {len(matches)} SQL injection pattern(s) in request parameters",
                evidence=matches
            )

        return None


class XSSDetector:
    """
    Detects Cross-Site Scripting (XSS) attempts.
    Rule-based detector using pattern matching.
    """

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"onerror\s*=",  # Event handlers
        r"onload\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"<iframe[^>]*>",  # Iframe injection
        r"<img[^>]*onerror",  # Image with onerror
        r"eval\s*\(",  # eval() calls
        r"alert\s*\(",  # alert() calls
        r"document\.cookie",  # Cookie stealing
    ]

    def __init__(self):
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.XSS_PATTERNS]

    def detect(self, event: Dict) -> Optional[DetectorResult]:
        """
        Analyze event for XSS attempts.

        Args:
            event: Enriched event dict

        Returns:
            DetectorResult if XSS detected, None otherwise
        """
        request_meta = event.get('request_meta', {})

        # Check query parameters and body
        query_params = request_meta.get('query_params', {})
        body = request_meta.get('body', {})
        headers = request_meta.get('headers', {})

        # Combine all input values
        all_values = []

        if isinstance(query_params, dict):
            all_values.extend(str(v) for v in query_params.values())

        if isinstance(body, dict):
            all_values.extend(str(v) for v in body.values())

        # Also check certain headers (like Referer, User-Agent)
        for header in ['referer', 'user-agent']:
            if header in headers:
                all_values.append(str(headers[header]))

        # Check each value against patterns
        matches = []
        for value in all_values:
            for pattern in self.patterns:
                if pattern.search(value):
                    matches.append({
                        'value': value[:100],
                        'pattern': pattern.pattern
                    })

        if matches:
            confidence = min(0.90, 0.6 + (len(matches) * 0.1))

            return DetectorResult(
                is_threat=True,
                confidence_score=confidence,
                detector_type='rule_based',
                detector_name='XSS Detector',
                severity='medium',
                attack_type='xss',
                explanation=f"Detected {len(matches)} XSS pattern(s) in request",
                evidence=matches
            )

        return None


class RateAnomalyDetector:
    """
    Detects unusual request rate spikes from a single IP.
    Statistical detector using in-memory rate tracking.

    NOTE: This is a simplified in-memory implementation.
    Production would use Redis with sliding windows.
    """

    def __init__(self, window_seconds: int = 60, threshold_multiplier: float = 3.0):
        self.window_seconds = window_seconds
        self.threshold_multiplier = threshold_multiplier
        # In-memory tracking: {ip: [timestamps]}
        self.ip_requests = {}

    def detect(self, event: Dict) -> Optional[DetectorResult]:
        """
        Analyze event for rate anomalies.

        Args:
            event: Enriched event dict

        Returns:
            DetectorResult if rate anomaly detected, None otherwise
        """
        client_ip = event.get('client_ip')
        if not client_ip:
            return None

        now = timezone.now()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Initialize if first request from this IP
        if client_ip not in self.ip_requests:
            self.ip_requests[client_ip] = []

        # Add current request
        self.ip_requests[client_ip].append(now)

        # Clean old requests outside window
        self.ip_requests[client_ip] = [
            ts for ts in self.ip_requests[client_ip]
            if ts >= window_start
        ]

        # Count requests in window
        request_count = len(self.ip_requests[client_ip])

        # Define baseline (e.g., 100 requests per minute is normal)
        baseline = 100
        threshold = baseline * self.threshold_multiplier

        if request_count > threshold:
            severity = 'high' if request_count > threshold * 2 else 'medium'
            confidence = min(0.85, 0.5 + ((request_count - threshold) / threshold * 0.3))

            return DetectorResult(
                is_threat=True,
                confidence_score=confidence,
                detector_type='statistical',
                detector_name='Rate Anomaly Detector',
                severity=severity,
                attack_type='rate_abuse',
                explanation=f"Request rate from {client_ip}: {request_count} req/{self.window_seconds}s (threshold: {threshold})",
                evidence=[{
                    'ip': client_ip,
                    'request_count': request_count,
                    'window_seconds': self.window_seconds,
                    'threshold': threshold
                }]
            )

        return None


class SuspiciousPathDetector:
    """
    Detects requests to suspicious or admin paths.
    Rule-based detector.
    """

    SUSPICIOUS_PATHS = [
        r'/admin',
        r'/phpmyadmin',
        r'/wp-admin',
        r'/\.env',
        r'/\.git',
        r'/config\.php',
        r'/backup',
        r'/debug',
        r'/phpinfo\.php',
        r'/shell\.php',
        r'/\.aws',
        r'/\.ssh',
    ]

    def __init__(self):
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATHS]

    def detect(self, event: Dict) -> Optional[DetectorResult]:
        """
        Analyze event for suspicious path access.

        Args:
            event: Enriched event dict

        Returns:
            DetectorResult if suspicious path detected, None otherwise
        """
        path = event.get('path', '')

        for pattern in self.patterns:
            if pattern.search(path):
                return DetectorResult(
                    is_threat=True,
                    confidence_score=0.75,
                    detector_type='rule_based',
                    detector_name='Suspicious Path Detector',
                    severity='medium',
                    attack_type='path_traversal',
                    explanation=f"Suspicious path access: {path}",
                    evidence=[{'path': path, 'pattern': pattern.pattern}]
                )

        return None


# Detector registry
DETECTORS = {
    'sqli': SQLInjectionDetector(),
    'xss': XSSDetector(),
    'rate_anomaly': RateAnomalyDetector(),
    'suspicious_path': SuspiciousPathDetector(),
}


def run_all_detectors(event: Dict) -> List[DetectorResult]:
    """
    Run all detectors on an event.

    Args:
        event: Enriched event dict

    Returns:
        List of DetectorResult objects for detected threats
    """
    results = []

    for detector_name, detector in DETECTORS.items():
        try:
            result = detector.detect(event)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Error running {detector_name}: {e}", exc_info=True)

    return results
