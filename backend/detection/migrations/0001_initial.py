"""
Initial migration for detection models.
"""
from django.db import migrations, models
import django.contrib.postgres.fields
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DetectionEvent',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('detection_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('trigger_event_ids', django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(), default=list, help_text='Event IDs that triggered this detection', size=None)),
                ('trace_ids', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), default=list, help_text='Trace IDs for investigation', size=None)),
                ('detector_type', models.CharField(choices=[('rule_based', 'Rule-based'), ('statistical', 'Statistical'), ('r1_realtime', 'R1 Real-time'), ('r1_batch', 'R1 Batch')], max_length=20)),
                ('detector_name', models.CharField(db_index=True, max_length=100)),
                ('severity', models.CharField(choices=[('info', 'Info'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], db_index=True, max_length=10)),
                ('confidence_score', models.DecimalField(decimal_places=2, help_text='Confidence score 0.0 to 1.0', max_digits=3)),
                ('r1_score', models.DecimalField(blank=True, decimal_places=2, help_text='Deepseek-R1 risk score 0.0 to 1.0', max_digits=3, null=True)),
                ('r1_explanation', models.JSONField(blank=True, null=True)),
                ('attack_type', models.CharField(blank=True, help_text='e.g., sqli, xss, credential_stuffing, data_exfil, business_logic_abuse', max_length=100)),
                ('client_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('investigating', 'Investigating'), ('confirmed', 'Confirmed'), ('false_positive', 'False Positive'), ('resolved', 'Resolved')], db_index=True, default='open', max_length=20)),
                ('detected_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.organization')),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detections', to='core.application')),
                ('endpoint', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.apiendpoint')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_detections', to='core.user')),
            ],
            options={
                'db_table': 'detection_event',
                'ordering': ['-detected_at'],
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name='detectionevent',
            index=models.Index(fields=['org', 'app', 'detected_at'], name='detection_org_app_time_idx'),
        ),
        migrations.AddIndex(
            model_name='detectionevent',
            index=models.Index(fields=['org', 'app', 'severity', 'status'], name='detection_org_app_sev_idx'),
        ),
        migrations.AddIndex(
            model_name='detectionevent',
            index=models.Index(fields=['status', 'detected_at'], name='detection_status_time_idx'),
        ),
    ]
