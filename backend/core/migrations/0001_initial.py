"""
Initial migration for Sentrix core models.
"""
from django.db import migrations, models
import django.contrib.postgres.fields
import django.core.validators
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('org_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('default_config', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'db_table': 'organization',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('subscription_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('plan_tier', models.CharField(choices=[('free', 'Free'), ('pro', 'Professional'), ('enterprise', 'Enterprise')], default='free', max_length=20)),
                ('quota_max_applications', models.IntegerField(default=1, help_text='Maximum number of applications allowed', validators=[django.core.validators.MinValueValidator(1)])),
                ('quota_max_users', models.IntegerField(default=5, help_text='Maximum number of licensed user seats', validators=[django.core.validators.MinValueValidator(1)])),
                ('quota_requests_per_month', models.BigIntegerField(default=1000000, help_text='Maximum API requests per month across all apps', validators=[django.core.validators.MinValueValidator(1)])),
                ('features', models.JSONField(blank=True, default=dict)),
                ('valid_from', models.DateTimeField(auto_now_add=True)),
                ('valid_until', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='core.organization')),
            ],
            options={
                'db_table': 'subscription',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(db_index=True, max_length=254, unique=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('full_name', models.CharField(blank=True, max_length=255)),
                ('role', models.CharField(choices=[('admin', 'Administrator'), ('analyst', 'Security Analyst'), ('viewer', 'Viewer')], default='viewer', max_length=20)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='users', to='core.organization')),
            ],
            options={
                'db_table': 'sentrix_user',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('app_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(max_length=255)),
                ('domain', models.CharField(db_index=True, help_text='Customer domain (e.g., api.customer-payments.com)', max_length=255, unique=True)),
                ('origin_url', models.URLField(help_text='Backend origin URL (e.g., https://origin.customer.com)', max_length=500)),
                ('cname_target', models.CharField(help_text='Sentrix edge CNAME target (e.g., sentrix-edge-us-east.example.com)', max_length=255)),
                ('verification_token', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('dns_verified', models.BooleanField(db_index=True, default=False)),
                ('dns_verified_at', models.DateTimeField(blank=True, null=True)),
                ('custom_config', models.JSONField(blank=True, default=dict)),
                ('failover_mode', models.CharField(choices=[('fail_open', 'Fail Open (forward to origin on error)'), ('fail_closed', 'Fail Closed (block on error)')], default='fail_open', max_length=20)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='core.organization')),
            ],
            options={
                'db_table': 'application',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='APIEndpoint',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('endpoint_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('method', models.CharField(db_index=True, max_length=10)),
                ('path_pattern', models.CharField(db_index=True, help_text='Canonicalized path (e.g., /payments/charge/{id})', max_length=500)),
                ('request_schema', models.JSONField(blank=True, null=True)),
                ('response_schema', models.JSONField(blank=True, null=True)),
                ('owner', models.CharField(blank=True, max_length=255)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), blank=True, default=list, size=None)),
                ('risk_score', models.DecimalField(decimal_places=2, default=0.5, help_text='Risk score 0.0 to 1.0', max_digits=3)),
                ('first_seen', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(auto_now_add=True)),
                ('request_count', models.BigIntegerField(default=0)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.organization')),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='endpoints', to='core.application')),
            ],
            options={
                'db_table': 'api_endpoint',
                'ordering': ['-last_seen'],
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('audit_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(db_index=True, max_length=100)),
                ('resource_type', models.CharField(db_index=True, max_length=50)),
                ('resource_id', models.CharField(blank=True, max_length=100)),
                ('details', models.JSONField(default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.organization')),
                ('app', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.application')),
                ('actor_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.user')),
            ],
            options={
                'db_table': 'audit_log',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='UsageTracking',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('usage_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('period_start', models.DateTimeField(db_index=True)),
                ('period_end', models.DateTimeField(db_index=True)),
                ('request_count', models.BigIntegerField(default=0)),
                ('blocked_count', models.BigIntegerField(default=0)),
                ('r1_invocation_count', models.BigIntegerField(default=0)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.organization')),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.application')),
            ],
            options={
                'db_table': 'usage_tracking',
                'ordering': ['-period_start'],
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['org', 'is_active'], name='subscripti_org_id_active_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['org', 'valid_from', 'valid_until'], name='subscripti_org_id_valid_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['org', 'is_active'], name='user_org_id_active_idx'),
        ),
        migrations.AddIndex(
            model_name='application',
            index=models.Index(fields=['org', 'is_active'], name='app_org_id_active_idx'),
        ),
        migrations.AddIndex(
            model_name='apiendpoint',
            index=models.Index(fields=['org', 'app'], name='endpoint_org_app_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['org', 'timestamp'], name='audit_org_time_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['actor_user', 'timestamp'], name='audit_user_time_idx'),
        ),
        migrations.AddIndex(
            model_name='usagetracking',
            index=models.Index(fields=['org', 'period_start'], name='usage_org_period_idx'),
        ),
        # Constraints
        migrations.AddConstraint(
            model_name='application',
            constraint=models.UniqueConstraint(fields=('org', 'slug'), name='unique_org_slug'),
        ),
        migrations.AddConstraint(
            model_name='apiendpoint',
            constraint=models.UniqueConstraint(fields=('org', 'app', 'method', 'path_pattern'), name='unique_endpoint'),
        ),
        migrations.AddConstraint(
            model_name='usagetracking',
            constraint=models.UniqueConstraint(fields=('org', 'app', 'period_start'), name='unique_usage_period'),
        ),
    ]
