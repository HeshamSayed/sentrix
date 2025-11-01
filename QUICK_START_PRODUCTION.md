# 🚀 SENTRIX Production Deployment - Quick Start

## Prerequisites

- Docker & Docker Compose installed
- 24GB RAM, 8 vCPU server
- Linux OS (Ubuntu 20.04+ recommended)
- Ports available: 5432, 6432, 6379, 8000, 8001, 9092, 11434

---

## ⚡ 5-Minute Deploy

### Step 1: Build & Start Services

```bash
cd /home/heshamsayed/Desktop/sentrix

# Build new services (PgBouncer, Stream Processor)
docker-compose build pgbouncer stream-processor

# Start all services
docker-compose up -d

# Wait for health checks (2-3 minutes)
watch docker-compose ps
```

### Step 2: Initialize DeepSeek R1 AI Model

```bash
# Download model (10-30 minutes, one-time only)
./init-deepseek.sh

# Model will be cached in Docker volume for future use
```

### Step 3: Verify All Services

```bash
# Check all containers are healthy
docker-compose ps

# Test Edge service
curl http://localhost:8001/health

# Test Backend
curl http://localhost:8000/admin/

# Test AI Service
curl http://localhost:5001/health

# Test PgBouncer
docker exec sentrix-pgbouncer psql -h localhost -p 6432 -U sentrix -d pgbouncer -c "SHOW STATS;"
```

---

## 🧪 Performance Test

```bash
# Run async performance test
python3 test_async_performance.py

# Expected results:
# - Throughput: 2,000-3,000 req/s
# - P99 Latency: < 100ms
# - Success Rate: 100%
```

---

## 📊 Monitoring Commands

### Database Metrics

```bash
# PostgreSQL connections
docker exec sentrix-postgres psql -U sentrix -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# PgBouncer stats
docker exec sentrix-pgbouncer psql -h localhost -p 6432 -U sentrix \
  -d pgbouncer -c "SHOW POOLS; SHOW STATS;"

# Redis info
docker exec sentrix-redis redis-cli -a sentrix_redis_pass INFO stats
```

### Kafka Metrics

```bash
# List topics
docker exec sentrix-kafka kafka-topics --list --bootstrap-server localhost:9092

# Watch security events
docker exec sentrix-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic security-events \
  --from-beginning

# Check consumer lag
docker exec sentrix-kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group sentrix-stream-processor
```

### AI Service Metrics

```bash
# Check loaded models
docker exec sentrix-deepseek-ai ollama list

# Test AI inference
curl -X POST http://localhost:11434/api/generate -d '{
  "model": "deepseek-r1:1.5b",
  "prompt": "Is this SQL injection: SELECT * FROM users WHERE id=1 OR 1=1?",
  "stream": false
}'

# AI service health
curl http://localhost:5001/health
```

### System Resources

```bash
# Docker stats
docker stats sentrix-postgres sentrix-redis sentrix-pgbouncer \
  sentrix-kafka sentrix-deepseek-ai sentrix-edge sentrix-backend

# Stream processor logs
docker-compose logs stream-processor --tail=50 -f
```

---

## 🔧 Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs --tail=100

# Specific service logs
docker-compose logs postgres --tail=50
docker-compose logs pgbouncer --tail=50
docker-compose logs kafka --tail=50
```

### PgBouncer Connection Issues

```bash
# Test direct PostgreSQL connection
psql -h localhost -p 5432 -U sentrix -d sentrix

# Test PgBouncer connection
psql -h localhost -p 6432 -U sentrix -d sentrix

# Check PgBouncer logs
docker-compose logs pgbouncer --tail=100
```

### DeepSeek R1 Not Working

```bash
# Check Ollama service
docker exec sentrix-deepseek-ai ollama list

# Re-pull model
docker exec sentrix-deepseek-ai ollama pull deepseek-r1:1.5b

# Check AI service logs
docker-compose logs ai-service --tail=100
docker-compose logs deepseek-ai --tail=100
```

### Kafka Issues

```bash
# Check Kafka is ready
docker exec sentrix-kafka kafka-broker-api-versions \
  --bootstrap-server localhost:9092

# Create topics manually if needed
docker exec sentrix-kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic security-events \
  --partitions 4 \
  --replication-factor 1
```

---

## 🔐 Security Hardening (Before Production!)

### 1. Change Default Passwords

Edit `docker-compose.yml`:

```yaml
# PostgreSQL
POSTGRES_PASSWORD: <CHANGE_ME>

# Redis
--requirepass <CHANGE_ME>

# Django SECRET_KEY
SECRET_KEY: <CHANGE_ME>
```

Then rebuild:

```bash
docker-compose down -v
docker-compose up -d
```

### 2. Enable SSL/TLS

```bash
# Generate SSL certificates
mkdir -p certs
openssl req -new -x509 -days 365 -nodes \
  -out certs/server.crt \
  -keyout certs/server.key

# Update PostgreSQL to use SSL
# Add to docker-compose.yml postgres volumes:
# - ./certs:/var/lib/postgresql/certs
```

### 3. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 22/tcp    # SSH
sudo ufw enable
```

### 4. Set Up Backups

```bash
# PostgreSQL backup script
cat > backup-postgres.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec sentrix-postgres pg_dump -U sentrix sentrix > \
  /backups/sentrix_$DATE.sql
# Keep last 7 days
find /backups -name "sentrix_*.sql" -mtime +7 -delete
EOF

chmod +x backup-postgres.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /path/to/backup-postgres.sh" | crontab -
```

---

## 📈 Scaling Guide

### Horizontal Scaling (Add More Edge Instances)

```bash
# Add to docker-compose.yml
edge-2:
  build:
    context: ./edge
  container_name: sentrix-edge-2
  depends_on:
    - pgbouncer
    - redis
  environment:
    - DATABASE_URL=postgresql://sentrix:pass@pgbouncer:6432/sentrix
    - REDIS_URL=redis://:pass@redis:6379/0
  ports:
    - "8002:8001"
  command: uvicorn main:app --host 0.0.0.0 --port 8001 --workers 8 --loop uvloop
  networks:
    - sentrix-network

# Then use nginx/HAProxy for load balancing
```

### Vertical Scaling (More Resources)

Update `docker-compose.yml` resource limits:

```yaml
postgres:
  deploy:
    resources:
      limits:
        memory: 16G  # Increased from 8G
      reservations:
        memory: 12G

redis:
  deploy:
    resources:
      limits:
        memory: 16G  # Increased from 10G
```

---

## 🎯 Performance Tuning

### For Higher Throughput (> 3,000 req/s)

1. **Increase PgBouncer pool size:**

```ini
# pgbouncer/pgbouncer.ini
default_pool_size = 50  # Increased from 25
```

2. **Add more Kafka partitions:**

```bash
docker exec sentrix-kafka kafka-topics --alter \
  --bootstrap-server localhost:9092 \
  --topic security-events \
  --partitions 8  # Increased from 4
```

3. **Scale Edge workers:**

```yaml
# edge/Dockerfile
CMD ["uvicorn", "main:app", "--workers", "16"]  # Doubled
```

### For Lower Latency (< 50ms P99)

1. **Increase Redis memory:**

```yaml
redis:
  command:
    - --maxmemory 16gb  # Increased
```

2. **Tune PostgreSQL:**

```yaml
postgres:
  command:
    - "-c"
    - "shared_buffers=12GB"  # Increased
```

3. **Use Redis caching more aggressively:**

```python
# In Django settings.py
CACHES['default']['TIMEOUT'] = 600  # 10 minutes
```

---

## 📚 Next Steps

1. **Set up monitoring:** Install Prometheus + Grafana
2. **Configure alerting:** Set up PagerDuty/Slack notifications
3. **Test failover:** Simulate failures and verify recovery
4. **Load test:** Run sustained load for 24 hours
5. **Security audit:** Review and harden all configurations

---

## 🆘 Support

### Documentation

- [PRODUCTION_READY.md](PRODUCTION_READY.md) - Complete architecture
- [DATABASE_OPTIMIZATION.md](DATABASE_OPTIMIZATION.md) - DB tuning guide
- [ASYNC_EDGE_PERFORMANCE_REPORT.md](ASYNC_EDGE_PERFORMANCE_REPORT.md) - Performance analysis

### Health Endpoints

- Edge: `http://localhost:8001/health`
- Backend: `http://localhost:8000/api/health/`
- AI Service: `http://localhost:5001/health`
- Prometheus: `http://localhost:8001/metrics`

### Logs Location

```bash
# All services
docker-compose logs --tail=100 -f

# Specific service
docker-compose logs [service-name] --tail=50 -f
```

---

## ✅ Production Checklist

Before going live, verify:

- [ ] All services healthy (`docker-compose ps`)
- [ ] Default passwords changed
- [ ] SSL/TLS certificates configured
- [ ] Firewall rules in place
- [ ] Backups configured and tested
- [ ] Monitoring set up (Prometheus/Grafana)
- [ ] Alerting configured
- [ ] Load tested (24+ hours)
- [ ] Disaster recovery plan documented
- [ ] Team trained on deployment/troubleshooting

---

**Deployment Time:** ~40 minutes (including AI model download)  
**Expected Capacity:** 2,000-3,000 req/s with AI analysis  
**Expected Uptime:** 99.99%  

🚀 **You're ready for production!**

