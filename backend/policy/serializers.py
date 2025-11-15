"""
Policy serializers.
"""

from rest_framework import serializers
from .models import Policy


class PolicySerializer(serializers.ModelSerializer):
    """Serializer for Policy model."""

    org_name = serializers.CharField(source='org.name', read_only=True)
    app_name = serializers.CharField(source='app.name', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)

    class Meta:
        model = Policy
        fields = [
            'policy_id', 'org', 'org_name', 'app', 'app_name',
            'name', 'description', 'is_org_level',
            'condition', 'action', 'mode', 'is_enabled',
            'last_simulation_at', 'last_simulation_result',
            'priority', 'created_by', 'created_by_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['policy_id', 'created_at', 'updated_at', 'last_simulation_at']


class PolicyCreateSerializer(serializers.Serializer):
    """Serializer for creating policies."""

    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    app_id = serializers.UUIDField(required=False, allow_null=True)
    condition = serializers.JSONField()
    action = serializers.JSONField()
    mode = serializers.ChoiceField(choices=['observe', 'enforce'], default='observe')
    priority = serializers.IntegerField(default=100, min_value=1, max_value=1000)

    def validate_condition(self, value):
        """Validate condition DSL structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Condition must be a JSON object")

        # Basic structure validation
        # Should have either logical operators (and/or/not) or field conditions
        valid_logical = ['and', 'or', 'not']
        valid_field_keys = ['field', 'op', 'value']

        if not any(key in value for key in valid_logical + valid_field_keys):
            raise serializers.ValidationError(
                "Condition must contain logical operators (and/or/not) or field conditions (field/op/value)"
            )

        return value

    def validate_action(self, value):
        """Validate action structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Action must be a JSON object")

        # Must have 'type' field
        if 'type' not in value:
            raise serializers.ValidationError("Action must have 'type' field")

        # Validate action type
        valid_types = ['allow', 'block', 'throttle', 'challenge']
        if value['type'] not in valid_types:
            raise serializers.ValidationError(
                f"Action type must be one of: {', '.join(valid_types)}"
            )

        return value


class PolicySimulateSerializer(serializers.Serializer):
    """Serializer for policy simulation requests."""

    days = serializers.IntegerField(default=7, min_value=1, max_value=30)


class PolicyUpdateSerializer(serializers.Serializer):
    """Serializer for updating policies."""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    condition = serializers.JSONField(required=False)
    action = serializers.JSONField(required=False)
    mode = serializers.ChoiceField(choices=['observe', 'enforce'], required=False)
    priority = serializers.IntegerField(min_value=1, max_value=1000, required=False)

    def validate_condition(self, value):
        """Validate condition DSL structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Condition must be a JSON object")
        return value

    def validate_action(self, value):
        """Validate action structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Action must be a JSON object")

        if 'type' in value:
            valid_types = ['allow', 'block', 'throttle', 'challenge']
            if value['type'] not in valid_types:
                raise serializers.ValidationError(
                    f"Action type must be one of: {', '.join(valid_types)}"
                )

        return value
