"""
Initial migration for policy models.
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Policy',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('policy_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('is_org_level', models.BooleanField(default=False, help_text='If true, applies to all apps in organization')),
                ('condition', models.JSONField()),
                ('action', models.JSONField()),
                ('mode', models.CharField(choices=[('observe', 'Observe (log only)'), ('enforce', 'Enforce (take action)')], default='observe', max_length=10)),
                ('is_enabled', models.BooleanField(db_index=True, default=False)),
                ('last_simulation_at', models.DateTimeField(blank=True, null=True)),
                ('last_simulation_result', models.JSONField(blank=True, null=True)),
                ('priority', models.IntegerField(db_index=True, default=100)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.organization')),
                ('app', models.ForeignKey(blank=True, help_text='NULL = org-level policy (applies to all apps)', null=True, on_delete=django.db.models.deletion.CASCADE, to='core.application')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_policies', to='core.user')),
            ],
            options={
                'verbose_name_plural': 'policies',
                'db_table': 'policy',
                'ordering': ['priority', '-created_at'],
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name='policy',
            index=models.Index(fields=['org', 'app', 'is_enabled'], name='policy_org_app_enabled_idx'),
        ),
        migrations.AddIndex(
            model_name='policy',
            index=models.Index(fields=['org', 'app', 'priority'], name='policy_org_app_priority_idx'),
        ),
    ]
