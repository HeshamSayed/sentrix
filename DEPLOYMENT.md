# Sentrix - Production Deployment Guide

Complete guide for deploying Sentrix to production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Deployment Options](#deployment-options)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Docker Swarm Deployment](#docker-swarm-deployment)
6. [Manual VM Deployment](#manual-vm-deployment)
7. [Configuration](#configuration)
8. [Database Setup](#database-setup)
9. [Kafka Setup](#kafka-setup)
10. [Redis Setup](#redis-setup)
11. [SSL/TLS Setup](#ssltls-setup)
12. [Monitoring Setup](#monitoring-setup)
13. [Backup Strategy](#backup-strategy)
14. [Scaling Guide](#scaling-guide)
15. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Skills
- Kubernetes OR Docker Swarm OR Linux system administration
- PostgreSQL administration
- Kafka administration
- Redis administration
- SSL/TLS certificate management
- DNS management

### Required Tools
- `kubectl` (for Kubernetes)
- `docker` and `docker compose` (for Docker Swarm)
- `psql` (PostgreSQL client)
- `redis-cli` (Redis client)
- `curl` and `jq` (for testing)

---

## Infrastructure Requirements

### Minimum Production Setup

| Component | Min Resources | Recommended | Notes |
|-----------|---------------|-------------|-------|
| Control Plane | 2 CPU, 4GB RAM | 4 CPU, 8GB RAM | Django ASGI app |
| PostgreSQL | 2 CPU, 8GB RAM | 4 CPU, 16GB RAM | Primary + 1 replica |
| Redis | 1 CPU, 2GB RAM | 2 CPU, 4GB RAM | 3-node cluster |
| Kafka | 2 CPU, 4GB RAM (×3) | 4 CPU, 8GB RAM (×3) | 3-broker cluster |
| Model Server | 1 GPU, 8GB VRAM | 2 GPU, 16GB VRAM | A10 or T4 |
| Consumers | 2 CPU, 2GB RAM (each) | 4 CPU, 4GB RAM | 2 enrichment, 2 detector |

**Total Minimum:** ~20 CPUs, ~40GB RAM, 1 GPU

### Network Requirements
- **Ingress:** HTTPS (443), HTTP (80)
- **Internal:** PostgreSQL (5432), Redis (6379), Kafka (9092)
- **Egress:** Internet access for model downloads (initial setup)

### Storage Requirements
- **PostgreSQL:** 100GB SSD (minimum), scales with traffic
  - Estimate: ~1GB per million requests
  - Daily partitions, retain 30-90 days
- **Kafka:** 50GB SSD per broker
  - Retention: 7 days
- **Redis:** 4GB RAM (in-memory)

---

## Deployment Options

### Option 1: Kubernetes (Recommended)

**Pros:**
- Auto-scaling
- Self-healing
- Easy rolling updates
- Resource management

**Cons:**
- Complex setup
- Requires K8s knowledge

**Best for:** Production, high-traffic

### Option 2: Docker Swarm

**Pros:**
- Simpler than K8s
- Native Docker integration
- Good scaling

**Cons:**
- Less mature ecosystem
- Fewer features than K8s

**Best for:** Medium-traffic, simpler ops

### Option 3: Manual VMs

**Pros:**
- Full control
- No orchestration overhead

**Cons:**
- Manual scaling
- No auto-healing
- More ops work

**Best for:** Small deployments, specific requirements

---

## Kubernetes Deployment

### 1. Prerequisites

```bash
# Kubernetes cluster (1.24+)
kubectl version

# Helm (optional, but recommended)
helm version

# Storage class for persistent volumes
kubectl get storageclass
```

### 2. Create Namespace

```bash
kubectl create namespace sentrix
kubectl config set-context --current --namespace=sentrix
```

### 3. Create Secrets

```bash
# PostgreSQL credentials
kubectl create secret generic postgres-credentials \
  --from-literal=username=sentrix \
  --from-literal=password=$(openssl rand -base64 32) \
  --from-literal=database=sentrix

# Django secret key
kubectl create secret generic django-secret \
  --from-literal=secret-key=$(openssl rand -base64 50)

# JWT secret
kubectl create secret generic jwt-secret \
  --from-literal=secret=$(openssl rand -base64 32)
```

### 4. Deploy PostgreSQL

Using Bitnami PostgreSQL Helm chart:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami

helm install postgresql bitnami/postgresql \
  --set auth.username=sentrix \
  --set auth.password=$(kubectl get secret postgres-credentials -o jsonpath='{.data.password}' | base64 -d) \
  --set auth.database=sentrix \
  --set primary.persistence.size=100Gi \
  --set readReplicas.replicaCount=1 \
  --set readReplicas.persistence.size=100Gi
```

Or use the provided `k8s/postgresql.yaml`:

```bash
kubectl apply -f k8s/postgresql.yaml
```

### 5. Deploy Redis

```bash
helm install redis bitnami/redis \
  --set architecture=replication \
  --set auth.enabled=false \
  --set master.persistence.size=10Gi \
  --set replica.replicaCount=2
```

### 6. Deploy Kafka

```bash
helm install kafka bitnami/kafka \
  --set replicaCount=3 \
  --set persistence.size=50Gi \
  --set zookeeper.enabled=true
```

### 7. Run Database Migrations

```bash
# Create a temporary job to run migrations
kubectl apply -f k8s/migration-job.yaml

# Wait for completion
kubectl wait --for=condition=complete job/django-migrate --timeout=300s

# Check logs
kubectl logs job/django-migrate
```

### 8. Deploy Control Plane

```bash
kubectl apply -f k8s/control-plane.yaml

# Wait for deployment
kubectl rollout status deployment/control-plane

# Verify pods
kubectl get pods -l app=control-plane
```

### 9. Deploy Consumers

```bash
# Enrichment consumer
kubectl apply -f k8s/enrichment-consumer.yaml

# Detector consumer
kubectl apply -f k8s/detector-consumer.yaml

# Storage consumer (optional, can use enrichment)
kubectl apply -f k8s/storage-consumer.yaml
```

### 10. Deploy Model Server

```bash
# Requires GPU nodes
kubectl apply -f k8s/model-server.yaml

# Verify GPU allocation
kubectl get pods -l app=model-server -o wide
```

### 11. Create Ingress

```bash
# Install ingress controller (if not present)
helm install ingress-nginx ingress-nginx/ingress-nginx

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Get external IP
kubectl get ingress sentrix-ingress
```

### 12. Verify Deployment

```bash
# Check all pods are running
kubectl get pods

# Check services
kubectl get svc

# Test health endpoint
EXTERNAL_IP=$(kubectl get ingress sentrix-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP/health/
```

---

## Configuration

### Environment Variables

Create `k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentrix-config
data:
  # Django settings
  DJANGO_SETTINGS_MODULE: "sentrix.settings"
  DJANGO_DEBUG: "False"
  DJANGO_ALLOWED_HOSTS: "api.yourdomain.com,sentrix.yourdomain.com"

  # Database
  DB_HOST: "postgresql"
  DB_PORT: "5432"
  DB_NAME: "sentrix"

  # Redis
  REDIS_URL: "redis://redis-master:6379/0"

  # Kafka
  KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"

  # Model Server
  R1_MODEL_SERVER_URL: "http://model-server:8001"

  # Feature flags
  ENABLE_R1_REALTIME: "true"
  ENABLE_R1_BATCH: "false"

  # Monitoring
  PROMETHEUS_MULTIPROC_DIR: "/tmp/prometheus"
```

Apply:
```bash
kubectl apply -f k8s/configmap.yaml
```

---

## Database Setup

### Initial Schema

```bash
# Connect to PostgreSQL pod
kubectl exec -it postgresql-0 -- psql -U sentrix -d sentrix

# Verify tables
\dt

# Expected tables:
# - organization
# - subscription
# - sentrix_user
# - application
# - api_endpoint
# - api_request_event (+ partitions)
# - detection_event
# - policy
# - audit_log
# - usage_tracking
```

### Create Partitions

The application auto-creates daily partitions, but you can pre-create:

```sql
-- Create partitions for next 30 days
DO $$
DECLARE
  day_date DATE;
  partition_name TEXT;
  start_date TEXT;
  end_date TEXT;
BEGIN
  FOR i IN 0..29 LOOP
    day_date := CURRENT_DATE + i;
    partition_name := 'api_request_event_' || to_char(day_date, 'YYYY_MM_DD');
    start_date := day_date::TEXT;
    end_date := (day_date + 1)::TEXT;

    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I PARTITION OF api_request_event
       FOR VALUES FROM (%L) TO (%L)',
      partition_name, start_date, end_date
    );
  END LOOP;
END $$;
```

### Backup Configuration

```bash
# Full backup
kubectl exec postgresql-0 -- pg_dump -U sentrix sentrix > backup.sql

# Backup with cron (create CronJob)
kubectl apply -f k8s/backup-cronjob.yaml
```

---

## Kafka Setup

### Create Topics

```bash
# Get Kafka pod
KAFKA_POD=$(kubectl get pods -l app.kubernetes.io/name=kafka -o name | head -1)

# Create topics
kubectl exec -it $KAFKA_POD -- kafka-topics --create \
  --topic ingest.events \
  --bootstrap-server localhost:9092 \
  --partitions 6 \
  --replication-factor 3

kubectl exec -it $KAFKA_POD -- kafka-topics --create \
  --topic enriched.events \
  --bootstrap-server localhost:9092 \
  --partitions 6 \
  --replication-factor 3

kubectl exec -it $KAFKA_POD -- kafka-topics --create \
  --topic detection.events \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 3

kubectl exec -it $KAFKA_POD -- kafka-topics --create \
  --topic policy.updates \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 3
```

### Configure Retention

```bash
# 7-day retention (default)
kubectl exec -it $KAFKA_POD -- kafka-configs --alter \
  --entity-type topics \
  --entity-name ingest.events \
  --add-config retention.ms=604800000 \
  --bootstrap-server localhost:9092
```

---

## SSL/TLS Setup

### Option 1: Let's Encrypt (Recommended)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f k8s/letsencrypt-issuer.yaml

# Update ingress with TLS
kubectl apply -f k8s/ingress-tls.yaml
```

### Option 2: Custom Certificates

```bash
# Create TLS secret
kubectl create secret tls sentrix-tls \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem

# Reference in ingress
# spec.tls:
#   - hosts:
#     - api.yourdomain.com
#     secretName: sentrix-tls
```

---

## Monitoring Setup

### Prometheus & Grafana

```bash
# Install kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack

# Import Sentrix dashboards
kubectl apply -f k8s/grafana-dashboards.yaml
```

### Key Metrics to Monitor

- **Decision API:** `decision_api_latency_seconds{quantile="0.95"}`
- **Kafka Lag:** `kafka_consumer_lag{topic, group}`
- **Detection Rate:** `detections_total{severity}`
- **Request Rate:** `requests_total{org_id, app_id}`
- **Error Rate:** `http_requests_total{status=~"5.."}`

### Alerting Rules

Create `k8s/prometheus-rules.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: sentrix-alerts
spec:
  groups:
    - name: sentrix
      interval: 30s
      rules:
        - alert: HighDecisionLatency
          expr: histogram_quantile(0.95, decision_api_latency_seconds) > 0.050
          for: 5m
          annotations:
            summary: "Decision API P95 latency > 50ms"

        - alert: HighKafkaLag
          expr: kafka_consumer_lag > 10000
          for: 5m
          annotations:
            summary: "Kafka consumer lag > 10k messages"
```

---

## Backup Strategy

### Database Backups

**Daily Full Backup:**
```bash
# Create backup CronJob
kubectl apply -f k8s/backup-cronjob.yaml

# Backup script uploads to S3/GCS
# Retention: 7 daily, 4 weekly, 12 monthly
```

**Continuous WAL Archiving:**
```sql
-- Configure in postgresql.conf
archive_mode = on
archive_command = 'aws s3 cp %p s3://bucket/wal/%f'
```

### Kafka Backups

Kafka data is transient (7-day retention). Critical events are in PostgreSQL.

For disaster recovery:
- Export consumer offsets
- Backup topic configurations
- No need to backup messages (already in DB)

---

## Scaling Guide

### Horizontal Scaling

**Control Plane:**
```bash
kubectl scale deployment control-plane --replicas=4
```

**Consumers:**
```bash
kubectl scale deployment enrichment-consumer --replicas=4
kubectl scale deployment detector-consumer --replicas=4
```

**Kafka:**
```bash
# Add brokers
helm upgrade kafka bitnami/kafka --set replicaCount=5
```

### Vertical Scaling

Update resource requests/limits in deployment YAML:

```yaml
resources:
  requests:
    cpu: 4000m
    memory: 8Gi
  limits:
    cpu: 8000m
    memory: 16Gi
```

### Auto-Scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: control-plane-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: control-plane
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods

# Describe pod
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

#### 2. Database Connection Errors

```bash
# Test connection
kubectl exec -it postgresql-0 -- psql -U sentrix -d sentrix -c "SELECT 1"

# Check service
kubectl get svc postgresql

# Check credentials
kubectl get secret postgres-credentials -o yaml
```

#### 3. Kafka Consumer Lag

```bash
# Check consumer group status
kubectl exec -it kafka-0 -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group enrichment-group \
  --describe

# Scale up consumers
kubectl scale deployment enrichment-consumer --replicas=6
```

#### 4. High Latency

```bash
# Check decision API latency
kubectl logs -l app=control-plane | grep "decision_api_latency"

# Check Redis performance
kubectl exec -it redis-master-0 -- redis-cli INFO stats

# Check PostgreSQL slow queries
kubectl exec -it postgresql-0 -- psql -U sentrix -d sentrix -c \
  "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10"
```

---

## Production Checklist

### Pre-Deployment

- [ ] Infrastructure provisioned (K8s cluster, VMs, etc.)
- [ ] DNS records configured
- [ ] SSL certificates obtained
- [ ] Secrets created (DB, JWT, etc.)
- [ ] Backup strategy defined
- [ ] Monitoring configured
- [ ] Alerting configured
- [ ] Runbook created

### Deployment

- [ ] PostgreSQL deployed and verified
- [ ] Redis deployed and verified
- [ ] Kafka deployed and verified
- [ ] Database migrations run
- [ ] Kafka topics created
- [ ] Control plane deployed
- [ ] Consumers deployed
- [ ] Model server deployed
- [ ] Ingress configured
- [ ] SSL/TLS verified

### Post-Deployment

- [ ] Health checks passing
- [ ] Test data created
- [ ] Integration tests passing
- [ ] Load testing completed
- [ ] Monitoring dashboards configured
- [ ] Alerts tested
- [ ] Backup tested (restore drill)
- [ ] Documentation updated
- [ ] Team trained

### Go-Live

- [ ] DNS cutover planned
- [ ] Rollback plan documented
- [ ] On-call schedule set
- [ ] Stakeholders notified
- [ ] First customer onboarded
- [ ] 48-hour monitoring
- [ ] Performance baseline captured

---

## Support

For deployment issues:
1. Check logs: `kubectl logs -l app=control-plane`
2. Review events: `kubectl get events`
3. Check monitoring dashboards
4. Review TROUBLESHOOTING.md (if exists)
5. Contact support team

---

**Deployment Guide Version:** 1.0
**Last Updated:** 2025-11-16
**Next Review:** Before Phase 8 (Production Deployment)
