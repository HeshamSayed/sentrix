"""
Policy DSL Evaluator.
Evaluates policy conditions against request events.
"""

import re
import ipaddress
from typing import Any, Dict, List, Optional
from django.utils import timezone


class PolicyEvaluator:
    """
    Evaluates policy conditions using DSL.

    DSL Format:
    {
      "and": [
        {"field": "path_pattern", "op": "eq", "value": "/api/admin"},
        {"field": "client_ip", "op": "in_cidr", "value": "10.0.0.0/8"}
      ]
    }

    Supported operators:
    - eq: equals
    - ne: not equals
    - in: value in list
    - not_in: value not in list
    - contains: string contains
    - regex: regex match
    - gt, gte, lt, lte: numeric comparisons
    - in_cidr: IP in CIDR range
    """

    def evaluate(self, condition: Dict[str, Any], event: Dict[str, Any]) -> bool:
        """
        Evaluate a condition against an event.

        Args:
            condition: Policy condition DSL
            event: Request event data

        Returns:
            True if condition matches, False otherwise
        """
        # Handle logical operators (and, or, not)
        if 'and' in condition:
            return all(self.evaluate(c, event) for c in condition['and'])

        if 'or' in condition:
            return any(self.evaluate(c, event) for c in condition['or'])

        if 'not' in condition:
            return not self.evaluate(condition['not'], event)

        # Handle field conditions
        if 'field' in condition and 'op' in condition:
            return self._evaluate_field(condition, event)

        # Invalid condition format
        raise ValueError(f"Invalid condition format: {condition}")

    def _evaluate_field(self, condition: Dict[str, Any], event: Dict[str, Any]) -> bool:
        """Evaluate a single field condition."""
        field = condition['field']
        op = condition['op']
        expected_value = condition.get('value')

        # Get actual value from event
        actual_value = self._get_field_value(field, event)

        # Evaluate operator
        return self._apply_operator(op, actual_value, expected_value)

    def _get_field_value(self, field: str, event: Dict[str, Any]) -> Any:
        """
        Get field value from event.
        Supports nested fields with dot notation: request_meta.headers.user_agent
        """
        # Handle dot notation for nested fields
        parts = field.split('.')
        value = event

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

            if value is None:
                return None

        return value

    def _apply_operator(self, op: str, actual: Any, expected: Any) -> bool:
        """Apply comparison operator."""

        # Handle None values
        if actual is None:
            return op == 'eq' and expected is None

        # Equality operators
        if op == 'eq':
            return actual == expected

        if op == 'ne':
            return actual != expected

        # List membership
        if op == 'in':
            return actual in (expected if isinstance(expected, list) else [expected])

        if op == 'not_in':
            return actual not in (expected if isinstance(expected, list) else [expected])

        # String operations
        if op == 'contains':
            return str(expected).lower() in str(actual).lower()

        if op == 'startswith':
            return str(actual).startswith(str(expected))

        if op == 'endswith':
            return str(actual).endswith(str(expected))

        if op == 'regex':
            try:
                pattern = re.compile(expected)
                return bool(pattern.search(str(actual)))
            except re.error:
                return False

        # Numeric comparisons
        if op == 'gt':
            return float(actual) > float(expected)

        if op == 'gte':
            return float(actual) >= float(expected)

        if op == 'lt':
            return float(actual) < float(expected)

        if op == 'lte':
            return float(actual) <= float(expected)

        # IP address operations
        if op == 'in_cidr':
            return self._ip_in_cidr(actual, expected)

        # Unknown operator
        raise ValueError(f"Unknown operator: {op}")

    def _ip_in_cidr(self, ip_str: str, cidr: str) -> bool:
        """Check if IP address is in CIDR range."""
        try:
            ip = ipaddress.ip_address(ip_str)
            network = ipaddress.ip_network(cidr, strict=False)
            return ip in network
        except (ValueError, TypeError):
            return False


class PolicyMatcher:
    """
    Matches policies against events and returns actions.
    """

    def __init__(self):
        self.evaluator = PolicyEvaluator()

    def match_policies(
        self,
        event: Dict[str, Any],
        policies: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find first matching policy and return its action.

        Policies are evaluated in priority order (lower priority number = higher priority).

        Args:
            event: Request event
            policies: List of policy dicts (sorted by priority)

        Returns:
            Policy action dict if match found, None otherwise
        """
        for policy in policies:
            # Skip disabled policies
            if not policy.get('is_enabled', False):
                continue

            # Skip observe-mode policies in enforce context
            # (observe policies are logged but don't affect decisions)
            mode = policy.get('mode', 'observe')

            # Evaluate condition
            try:
                condition = policy['condition']
                if self.evaluator.evaluate(condition, event):
                    # Match found
                    action = policy['action'].copy()
                    action['policy_id'] = policy.get('policy_id')
                    action['policy_name'] = policy.get('name')
                    action['policy_mode'] = mode
                    return action
            except Exception as e:
                # Log evaluation error but continue
                print(f"Policy evaluation error for {policy.get('name')}: {e}")
                continue

        # No match
        return None

    def get_all_matches(
        self,
        event: Dict[str, Any],
        policies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get all matching policies (for logging/simulation).

        Args:
            event: Request event
            policies: List of policy dicts

        Returns:
            List of matching policies
        """
        matches = []

        for policy in policies:
            if not policy.get('is_enabled', False):
                continue

            try:
                condition = policy['condition']
                if self.evaluator.evaluate(condition, event):
                    matches.append(policy)
            except Exception:
                continue

        return matches


def build_example_policy() -> Dict[str, Any]:
    """Build example policy for testing."""
    return {
        'policy_id': 'test-policy-1',
        'name': 'Block bad IPs on payment endpoint',
        'is_enabled': True,
        'mode': 'enforce',
        'priority': 10,
        'condition': {
            'and': [
                {
                    'field': 'path_pattern',
                    'op': 'eq',
                    'value': '/payments/charge/{id}'
                },
                {
                    'field': 'client_ip',
                    'op': 'in_cidr',
                    'value': '192.168.1.0/24'
                }
            ]
        },
        'action': {
            'type': 'block',
            'response_code': 403,
            'message': 'Access denied by security policy'
        }
    }


# Example usage
if __name__ == '__main__':
    # Test evaluator
    evaluator = PolicyEvaluator()

    # Test event
    event = {
        'method': 'POST',
        'path': '/payments/charge/123',
        'path_pattern': '/payments/charge/{id}',
        'client_ip': '192.168.1.100',
        'request_meta': {
            'headers': {
                'user_agent': 'Mozilla/5.0'
            }
        }
    }

    # Test simple condition
    condition1 = {
        'field': 'path_pattern',
        'op': 'eq',
        'value': '/payments/charge/{id}'
    }
    print(f"Condition 1: {evaluator.evaluate(condition1, event)}")  # True

    # Test AND condition
    condition2 = {
        'and': [
            {'field': 'method', 'op': 'eq', 'value': 'POST'},
            {'field': 'client_ip', 'op': 'in_cidr', 'value': '192.168.1.0/24'}
        ]
    }
    print(f"Condition 2: {evaluator.evaluate(condition2, event)}")  # True

    # Test policy matcher
    matcher = PolicyMatcher()
    policy = build_example_policy()

    action = matcher.match_policies(event, [policy])
    print(f"Action: {action}")
