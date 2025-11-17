# Kubernetes Manifests for Sentrix

This directory contains Kubernetes deployment manifests for Sentrix production deployment.

## Structure

```
k8s/
├── README.md                    - This file
├── namespace.yaml               - Namespace definition
├── configmap.yaml               - Application configuration
├── secrets-template.yaml        - Secrets template (fill before applying)
├── postgresql.yaml              - PostgreSQL StatefulSet
├── redis.yaml                   - Redis cluster
├── kafka.yaml                   - Kafka cluster (basic)
├── control-plane.yaml           - Django control plane
├── enrichment-consumer.yaml     - Enrichment Kafka consumer
├── detector-consumer.yaml       - Detector Kafka consumer
├── model-server.yaml            - Deepseek-R1 model server
├── ingress.yaml                 - Ingress configuration
└── monitoring/                  - Monitoring configs
    ├── prometheus-rules.yaml    - Alert rules
    └── grafana-dashboards.yaml  - Grafana dashboards
```

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
kubectl config set-context --current --namespace=sentrix
```

### 2. Create Secrets

```bash
# Copy template and fill in values
cp secrets-template.yaml secrets.yaml
# Edit secrets.yaml with your values
kubectl apply -f secrets.yaml
```

### 3. Create ConfigMap

```bash
kubectl apply -f configmap.yaml
```

### 4. Deploy Infrastructure

```bash
# PostgreSQL
kubectl apply -f postgresql.yaml

# Redis
kubectl apply -f redis.yaml

# Kafka (or use Helm chart instead)
kubectl apply -f kafka.yaml
```

### 5. Run Migrations

```bash
# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgresql --timeout=300s

# Run migrations (manual or via job)
kubectl run migration --image=sentrix/control-plane:latest \
  --rm -it --restart=Never \
  -- python manage.py migrate
```

### 6. Deploy Application

```bash
# Control plane
kubectl apply -f control-plane.yaml

# Consumers
kubectl apply -f enrichment-consumer.yaml
kubectl apply -f detector-consumer.yaml

# Model server (requires GPU nodes)
kubectl apply -f model-server.yaml
```

### 7. Deploy Ingress

```bash
# Install ingress controller first (if not already present)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Deploy ingress
kubectl apply -f ingress.yaml
```

### 8. Verify Deployment

```bash
# Check all pods
kubectl get pods

# Check services
kubectl get svc

# Check ingress
kubectl get ingress

# Test health
EXTERNAL_IP=$(kubectl get ingress sentrix-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP/health/
```

## Scaling

### Horizontal Scaling

```bash
# Scale control plane
kubectl scale deployment control-plane --replicas=4

# Scale consumers
kubectl scale deployment enrichment-consumer --replicas=4
kubectl scale deployment detector-consumer --replicas=4
```

### Vertical Scaling

Edit resource requests/limits in YAML files and reapply.

## Monitoring

```bash
# Deploy monitoring stack
kubectl apply -f monitoring/prometheus-rules.yaml
kubectl apply -f monitoring/grafana-dashboards.yaml
```

## Troubleshooting

### View Logs

```bash
# Control plane
kubectl logs -l app=control-plane --tail=100

# Consumers
kubectl logs -l app=enrichment-consumer --tail=100
kubectl logs -l app=detector-consumer --tail=100

# All pods with label
kubectl logs -l tier=backend --all-containers --tail=100
```

### Debug Pod

```bash
# Exec into pod
kubectl exec -it <pod-name> -- /bin/bash

# Run management command
kubectl exec -it <pod-name> -- python manage.py shell
```

### Check Events

```bash
kubectl get events --sort-by='.lastTimestamp'
```

## Notes

- **Storage:** Uses default StorageClass. Adjust `storageClassName` if needed.
- **GPU:** Model server requires GPU nodes with NVIDIA drivers.
- **Ingress:** Assumes nginx-ingress controller. Adjust for other controllers.
- **Secrets:** Never commit `secrets.yaml` to git. Use gitignore.
- **Helm:** For complex deployments, consider Helm charts for PostgreSQL, Redis, Kafka.

## Production Recommendations

1. **Use Helm charts** for PostgreSQL, Redis, Kafka (bitnami charts recommended)
2. **Configure PodDisruptionBudgets** for high availability
3. **Set resource requests/limits** appropriately
4. **Enable autoscaling** (HPA) for control plane and consumers
5. **Configure backups** for PostgreSQL (see backup-cronjob.yaml)
6. **Use cert-manager** for automatic SSL certificate management
7. **Monitor resource usage** and adjust as needed

## See Also

- [DEPLOYMENT.md](../DEPLOYMENT.md) - Complete deployment guide
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) - Project overview
- [TOOLS.md](../TOOLS.md) - Management commands
