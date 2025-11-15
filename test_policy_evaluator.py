#!/usr/bin/env python3
"""
Standalone test for policy evaluator (no Django required).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Remove Django imports from evaluator temporarily for testing
import re
import ipaddress

class PolicyEvaluator:
    """Policy DSL evaluator (standalone version for testing)."""

    def evaluate(self, condition: dict, event: dict) -> bool:
        """Evaluate condition against event."""
        # Handle logical operators
        if 'and' in condition:
            return all(self.evaluate(c, event) for c in condition['and'])
        if 'or' in condition:
            return any(self.evaluate(c, event) for c in condition['or'])
        if 'not' in condition:
            return not self.evaluate(condition['not'], event)

        # Handle field conditions
        if 'field' in condition and 'op' in condition:
            return self._evaluate_field(condition, event)

        raise ValueError(f"Invalid condition: {condition}")

    def _evaluate_field(self, condition: dict, event: dict) -> bool:
        field = condition['field']
        op = condition['op']
        expected = condition.get('value')

        # Get actual value
        actual = self._get_field_value(field, event)

        # Apply operator
        return self._apply_operator(op, actual, expected)

    def _get_field_value(self, field: str, event: dict):
        parts = field.split('.')
        value = event
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def _apply_operator(self, op: str, actual, expected) -> bool:
        if actual is None:
            return op == 'eq' and expected is None

        if op == 'eq': return actual == expected
        if op == 'ne': return actual != expected
        if op == 'in': return actual in (expected if isinstance(expected, list) else [expected])
        if op == 'contains': return str(expected).lower() in str(actual).lower()
        if op == 'startswith': return str(actual).startswith(str(expected))
        if op == 'regex': return bool(re.compile(expected).search(str(actual)))
        if op == 'gt': return float(actual) > float(expected)
        if op == 'gte': return float(actual) >= float(expected)
        if op == 'lt': return float(actual) < float(expected)
        if op == 'lte': return float(actual) <= float(expected)
        if op == 'in_cidr': return ipaddress.ip_address(actual) in ipaddress.ip_network(expected, strict=False)

        raise ValueError(f"Unknown operator: {op}")


# Run tests
def test_policy_evaluator():
    evaluator = PolicyEvaluator()

    event = {
        'method': 'POST',
        'path': '/api/admin/users',
        'client_ip': '192.168.1.100',
        'request_meta': {
            'headers': {'user_agent': 'Mozilla/5.0'}
        }
    }

    # Test 1: Simple equality
    assert evaluator.evaluate({'field': 'method', 'op': 'eq', 'value': 'POST'}, event)
    print("✓ Test 1: Simple equality")

    # Test 2: AND condition
    condition = {
        'and': [
            {'field': 'method', 'op': 'eq', 'value': 'POST'},
            {'field': 'path', 'op': 'startswith', 'value': '/api/admin'}
        ]
    }
    assert evaluator.evaluate(condition, event)
    print("✓ Test 2: AND condition")

    # Test 3: OR condition
    condition = {
        'or': [
            {'field': 'method', 'op': 'eq', 'value': 'GET'},
            {'field': 'method', 'op': 'eq', 'value': 'POST'}
        ]
    }
    assert evaluator.evaluate(condition, event)
    print("✓ Test 3: OR condition")

    # Test 4: NOT condition
    condition = {
        'not': {'field': 'method', 'op': 'eq', 'value': 'DELETE'}
    }
    assert evaluator.evaluate(condition, event)
    print("✓ Test 4: NOT condition")

    # Test 5: IP in CIDR
    condition = {'field': 'client_ip', 'op': 'in_cidr', 'value': '192.168.1.0/24'}
    assert evaluator.evaluate(condition, event)
    print("✓ Test 5: IP in CIDR")

    # Test 6: Nested field access
    condition = {'field': 'request_meta.headers.user_agent', 'op': 'contains', 'value': 'Mozilla'}
    assert evaluator.evaluate(condition, event)
    print("✓ Test 6: Nested field access")

    # Test 7: Complex nested condition
    condition = {
        'and': [
            {
                'or': [
                    {'field': 'method', 'op': 'eq', 'value': 'POST'},
                    {'field': 'method', 'op': 'eq', 'value': 'PUT'}
                ]
            },
            {'field': 'path', 'op': 'contains', 'value': 'admin'},
            {'field': 'client_ip', 'op': 'in_cidr', 'value': '192.168.0.0/16'}
        ]
    }
    assert evaluator.evaluate(condition, event)
    print("✓ Test 7: Complex nested condition")

    print("\n✅ All tests passed!")


if __name__ == '__main__':
    test_policy_evaluator()
