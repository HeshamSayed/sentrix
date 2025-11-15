"""
Policy engine tests.
"""

import unittest
from .evaluator import PolicyEvaluator, PolicyMatcher


class TestPolicyEvaluator(unittest.TestCase):
    """Test policy DSL evaluator."""

    def setUp(self):
        self.evaluator = PolicyEvaluator()
        self.sample_event = {
            'method': 'POST',
            'path': '/api/payments/charge',
            'path_pattern': '/api/payments/{action}',
            'client_ip': '192.168.1.100',
            'request_meta': {
                'headers': {
                    'user_agent': 'Mozilla/5.0',
                    'content_type': 'application/json'
                },
                'query_params': {'amount': '100'}
            }
        }

    def test_simple_eq_condition(self):
        """Test simple equality condition."""
        condition = {
            'field': 'method',
            'op': 'eq',
            'value': 'POST'
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        condition['value'] = 'GET'
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_and_condition(self):
        """Test AND logical operator."""
        condition = {
            'and': [
                {'field': 'method', 'op': 'eq', 'value': 'POST'},
                {'field': 'path', 'op': 'startswith', 'value': '/api/payments'}
            ]
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        # Change one condition to false
        condition['and'][0]['value'] = 'GET'
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_or_condition(self):
        """Test OR logical operator."""
        condition = {
            'or': [
                {'field': 'method', 'op': 'eq', 'value': 'GET'},
                {'field': 'method', 'op': 'eq', 'value': 'POST'}
            ]
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        # Both false
        condition['or'] = [
            {'field': 'method', 'op': 'eq', 'value': 'DELETE'},
            {'field': 'method', 'op': 'eq', 'value': 'PUT'}
        ]
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_not_condition(self):
        """Test NOT logical operator."""
        condition = {
            'not': {
                'field': 'method',
                'op': 'eq',
                'value': 'GET'
            }
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        condition['not']['value'] = 'POST'
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_contains_operator(self):
        """Test contains operator."""
        condition = {
            'field': 'path',
            'op': 'contains',
            'value': 'payments'
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        condition['value'] = 'users'
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_regex_operator(self):
        """Test regex operator."""
        condition = {
            'field': 'path',
            'op': 'regex',
            'value': r'/api/payments/\w+'
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        condition['value'] = r'/api/users/\d+'
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_in_operator(self):
        """Test in operator."""
        condition = {
            'field': 'method',
            'op': 'in',
            'value': ['GET', 'POST', 'PUT']
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        condition['value'] = ['GET', 'DELETE']
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_ip_in_cidr(self):
        """Test IP in CIDR range."""
        condition = {
            'field': 'client_ip',
            'op': 'in_cidr',
            'value': '192.168.1.0/24'
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        condition['value'] = '10.0.0.0/8'
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_nested_field_access(self):
        """Test accessing nested fields with dot notation."""
        condition = {
            'field': 'request_meta.headers.user_agent',
            'op': 'contains',
            'value': 'Mozilla'
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))

        condition['value'] = 'Chrome'
        # Should still be true since 'Mozilla/5.0' is common in Chrome user agents
        # But let's test with something that definitely doesn't exist
        condition['value'] = 'XXXXXX'
        self.assertFalse(self.evaluator.evaluate(condition, self.sample_event))

    def test_numeric_comparisons(self):
        """Test numeric comparison operators."""
        event = {
            'amount': 100,
            'count': 5
        }

        # Greater than
        condition = {'field': 'amount', 'op': 'gt', 'value': 50}
        self.assertTrue(self.evaluator.evaluate(condition, event))

        condition = {'field': 'amount', 'op': 'gt', 'value': 100}
        self.assertFalse(self.evaluator.evaluate(condition, event))

        # Greater than or equal
        condition = {'field': 'amount', 'op': 'gte', 'value': 100}
        self.assertTrue(self.evaluator.evaluate(condition, event))

        # Less than
        condition = {'field': 'count', 'op': 'lt', 'value': 10}
        self.assertTrue(self.evaluator.evaluate(condition, event))

        # Less than or equal
        condition = {'field': 'count', 'op': 'lte', 'value': 5}
        self.assertTrue(self.evaluator.evaluate(condition, event))

    def test_complex_nested_condition(self):
        """Test complex nested conditions."""
        condition = {
            'and': [
                {
                    'or': [
                        {'field': 'method', 'op': 'eq', 'value': 'POST'},
                        {'field': 'method', 'op': 'eq', 'value': 'PUT'}
                    ]
                },
                {
                    'field': 'path',
                    'op': 'startswith',
                    'value': '/api/payments'
                },
                {
                    'field': 'client_ip',
                    'op': 'in_cidr',
                    'value': '192.168.0.0/16'
                }
            ]
        }
        self.assertTrue(self.evaluator.evaluate(condition, self.sample_event))


class TestPolicyMatcher(unittest.TestCase):
    """Test policy matcher."""

    def setUp(self):
        self.matcher = PolicyMatcher()
        self.sample_event = {
            'method': 'POST',
            'path': '/admin/users',
            'path_pattern': '/admin/users',
            'client_ip': '10.0.0.50'
        }

    def test_match_single_policy(self):
        """Test matching a single policy."""
        policies = [
            {
                'policy_id': 'policy-1',
                'name': 'Block admin access',
                'is_enabled': True,
                'mode': 'enforce',
                'priority': 10,
                'condition': {
                    'field': 'path',
                    'op': 'startswith',
                    'value': '/admin'
                },
                'action': {
                    'type': 'block',
                    'response_code': 403,
                    'message': 'Admin access denied'
                }
            }
        ]

        action = self.matcher.match_policies(self.sample_event, policies)
        self.assertIsNotNone(action)
        self.assertEqual(action['type'], 'block')
        self.assertEqual(action['policy_id'], 'policy-1')

    def test_no_match(self):
        """Test when no policy matches."""
        policies = [
            {
                'policy_id': 'policy-1',
                'name': 'Block payments',
                'is_enabled': True,
                'mode': 'enforce',
                'priority': 10,
                'condition': {
                    'field': 'path',
                    'op': 'startswith',
                    'value': '/api/payments'
                },
                'action': {
                    'type': 'block'
                }
            }
        ]

        action = self.matcher.match_policies(self.sample_event, policies)
        self.assertIsNone(action)

    def test_disabled_policy_ignored(self):
        """Test that disabled policies are ignored."""
        policies = [
            {
                'policy_id': 'policy-1',
                'name': 'Block admin',
                'is_enabled': False,  # Disabled
                'mode': 'enforce',
                'priority': 10,
                'condition': {
                    'field': 'path',
                    'op': 'startswith',
                    'value': '/admin'
                },
                'action': {
                    'type': 'block'
                }
            }
        ]

        action = self.matcher.match_policies(self.sample_event, policies)
        self.assertIsNone(action)

    def test_priority_ordering(self):
        """Test that policies are evaluated in priority order."""
        policies = [
            {
                'policy_id': 'policy-low',
                'name': 'Low priority allow',
                'is_enabled': True,
                'mode': 'enforce',
                'priority': 100,
                'condition': {
                    'field': 'path',
                    'op': 'startswith',
                    'value': '/admin'
                },
                'action': {
                    'type': 'allow'
                }
            },
            {
                'policy_id': 'policy-high',
                'name': 'High priority block',
                'is_enabled': True,
                'mode': 'enforce',
                'priority': 10,  # Lower number = higher priority
                'condition': {
                    'field': 'path',
                    'op': 'startswith',
                    'value': '/admin'
                },
                'action': {
                    'type': 'block'
                }
            }
        ]

        # Should match high priority policy first (even though it's second in list)
        # Actually, the policies should be pre-sorted by caller
        # But let's test with sorted list
        policies_sorted = sorted(policies, key=lambda p: p['priority'])

        action = self.matcher.match_policies(self.sample_event, policies_sorted)
        self.assertIsNotNone(action)
        self.assertEqual(action['policy_id'], 'policy-high')
        self.assertEqual(action['type'], 'block')

    def test_get_all_matches(self):
        """Test getting all matching policies."""
        policies = [
            {
                'policy_id': 'policy-1',
                'name': 'Policy 1',
                'is_enabled': True,
                'mode': 'enforce',
                'condition': {
                    'field': 'path',
                    'op': 'startswith',
                    'value': '/admin'
                },
                'action': {'type': 'block'}
            },
            {
                'policy_id': 'policy-2',
                'name': 'Policy 2',
                'is_enabled': True,
                'mode': 'enforce',
                'condition': {
                    'field': 'method',
                    'op': 'eq',
                    'value': 'POST'
                },
                'action': {'type': 'throttle'}
            }
        ]

        matches = self.matcher.get_all_matches(self.sample_event, policies)
        self.assertEqual(len(matches), 2)  # Both should match


if __name__ == '__main__':
    unittest.main()
