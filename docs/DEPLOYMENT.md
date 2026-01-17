# Deployment Guide

This guide covers deploying Optifiner in production environments.

## Table of Contents

1. [Docker Setup](#docker-setup)
2. [Docker Compose](#docker-compose)
3. [Kubernetes](#kubernetes)
4. [Cloud Deployment](#cloud-deployment)
5. [Performance Tuning](#performance-tuning)
6. [Monitoring](#monitoring)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

## Docker Setup

### Building Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build worker
docker-compose build web
docker-compose build api
```

### Docker Images

#### Worker Image

Contains the LangGraph evolution engine.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY services/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/worker .
ENTRYPOINT ["python", "cli.py"]
```

Build and run:
```bash
docker build -f services/worker/Dockerfile -t optifiner-worker .
docker run -e GOOGLE_API_KEY=xxx optifiner-worker /path/to/repo --evaluator evaluate.py
```

#### Web UI Image

React frontend.

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json .
RUN npm ci
COPY apps/web .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

#### API Image

FastAPI backend.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

## Docker Compose

### Complete Stack

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: optifiner
      POSTGRES_USER: optifiner
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U optifiner"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache & Task Queue
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Evolution Worker
  worker:
    build:
      context: .
      dockerfile: services/worker/Dockerfile
    environment:
      MODEL_PROVIDER: google
      MODEL_NAME: gemini-2.5-flash
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
      DATABASE_URL: postgresql://optifiner:secure_password@postgres/optifiner
      REDIS_URL: redis://redis:6379
      AGENTS: 10
      GENERATIONS: 3
      PARALLEL: 4
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - /var/optifiner/workspace:/tmp/optifiner  # Workspace directory
    restart: on-failure
    networks:
      - optifiner

  # FastAPI Backend
  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    environment:
      DATABASE_URL: postgresql://optifiner:secure_password@postgres/optifiner
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: always
    networks:
      - optifiner

  # React Frontend
  web:
    build:
      context: .
      dockerfile: apps/web/Dockerfile
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://api:8000
    depends_on:
      - api
    restart: always
    networks:
      - optifiner

volumes:
  postgres_data:
  redis_data:

networks:
  optifiner:
    driver: bridge
```

### Running Stack

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f worker
docker-compose logs -f api
docker-compose logs -f web

# Stop all services
docker-compose down

# Clean up volumes (WARNING: deletes data)
docker-compose down -v
```

### Environment File

Create `.env`:

```bash
# LLM Configuration
MODEL_PROVIDER=google
MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your-key-here

# Database
POSTGRES_USER=optifiner
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://optifiner:your-secure-password@postgres/optifiner

# Redis
REDIS_URL=redis://redis:6379

# Evolution Parameters
AGENTS=10
GENERATIONS=3
PARALLEL=4
```

## Kubernetes

### Helm Chart

```yaml
# helm/values.yaml
replicaCount: 3

image:
  repository: your-registry/optifiner-worker
  tag: latest

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

postgres:
  enabled: true
  auth:
    password: secure_password

redis:
  enabled: true
```

### Deployment Manifest

```yaml
# kubernetes/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: optifiner-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: optifiner-worker
  template:
    metadata:
      labels:
        app: optifiner-worker
    spec:
      containers:
      - name: worker
        image: your-registry/optifiner-worker:latest
        env:
        - name: MODEL_PROVIDER
          value: "google"
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: optifiner-secrets
              key: google-api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: optifiner-secrets
              key: database-url
        resources:
          limits:
            cpu: 2000m
            memory: 4Gi
          requests:
            cpu: 1000m
            memory: 2Gi
```

### Deploying

```bash
# Create namespace
kubectl create namespace optifiner

# Create secrets
kubectl create secret generic optifiner-secrets \
  --from-literal=google-api-key=xxx \
  --from-literal=database-url=postgres://... \
  -n optifiner

# Deploy using Helm
helm install optifiner ./helm -n optifiner

# Or using kubectl
kubectl apply -f kubernetes/ -n optifiner

# Check status
kubectl get pods -n optifiner
kubectl logs -f deployment/optifiner-worker -n optifiner
```

## Cloud Deployment

### AWS

#### ECS

```yaml
# ecs-task-definition.json
{
  "family": "optifiner-worker",
  "containerDefinitions": [
    {
      "name": "worker",
      "image": "your-repo.dkr.ecr.us-east-1.amazonaws.com/optifiner-worker:latest",
      "memory": 4096,
      "cpu": 1024,
      "environment": [
        {
          "name": "MODEL_PROVIDER",
          "value": "anthropic"
        }
      ],
      "secrets": [
        {
          "name": "ANTHROPIC_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:optifiner/api-key"
        }
      ]
    }
  ]
}
```

#### RDS & ElastiCache

```bash
# Create RDS PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier optifiner-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password secure_password \
  --allocated-storage 20

# Create ElastiCache Redis
aws elasticache create-cache-cluster \
  --cache-cluster-id optifiner-redis \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --engine-version 7.0
```

### Google Cloud

#### Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/optifiner-worker

# Deploy to Cloud Run
gcloud run deploy optifiner-worker \
  --image gcr.io/PROJECT_ID/optifiner-worker \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars GOOGLE_API_KEY=xxx
```

#### Cloud SQL & Memorystore

```bash
# Create PostgreSQL instance
gcloud sql instances create optifiner-postgres \
  --database-version POSTGRES_15 \
  --tier db-g1-small

# Create Redis instance
gcloud redis instances create optifiner-redis \
  --size 1 \
  --region us-central1
```

### Azure

#### Container Instances

```bash
az container create \
  --resource-group optifiner \
  --name optifiner-worker \
  --image your-registry.azurecr.io/optifiner-worker:latest \
  --memory 4 \
  --cpu 2 \
  --environment-variables GOOGLE_API_KEY=xxx
```

#### Database & Cache

```bash
# Create PostgreSQL
az postgres server create \
  --resource-group optifiner \
  --name optifiner-db \
  --sku-name B_Gen5_1

# Create Redis
az redis create \
  --resource-group optifiner \
  --name optifiner-cache \
  --location eastus \
  --sku basic \
  --vm-size small
```

## Performance Tuning

### Worker Configuration

```python
# Optimize for throughput vs latency
WORKER_CONFIG = {
    'agents': 20,              # More agents = higher throughput
    'parallel': 8,             # More parallelism
    'max_iterations': 20,      # Deeper search per agent
    'evaluator_timeout': 120,  # Longer benchmarks allowed
}

# Optimize for cost
WORKER_CONFIG = {
    'agents': 5,               # Fewer agents
    'parallel': 2,             # Lower parallelism
    'max_iterations': 10,      # Faster iteration
    'evaluator_timeout': 30,   # Faster benchmarks
}
```

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_evolution_nodes_project ON evolution_nodes(project_id);
CREATE INDEX idx_agents_project ON agents(project_id);

-- Connection pooling
max_connections = 200
```

### Resource Limits

```yaml
# kubernetes/resource-quotas.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: optifiner-quota
  namespace: optifiner
spec:
  hard:
    requests.cpu: "40"
    requests.memory: "80Gi"
    limits.cpu: "100"
    limits.memory: "200Gi"
```

### Caching

```bash
# Redis configuration
maxmemory 2gb
maxmemory-policy allkeys-lru
save ""  # Disable persistence for speed
```

## Monitoring

### Prometheus Metrics

```python
# In worker service
from prometheus_client import Counter, Histogram, Gauge

agents_completed = Counter('agents_completed_total', 'Total agents completed')
agent_duration = Histogram('agent_duration_seconds', 'Agent execution time')
fitness_improvement = Gauge('fitness_improvement', 'Fitness improvement')
```

### Grafana Dashboard

Create dashboard with:
- Agent success rate over time
- Average fitness per generation
- API response latency
- Database connection pool usage
- LLM API cost per day

### Logs

```bash
# Using ELK Stack
docker run -d \
  --name elasticsearch \
  -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.0.0

# Send logs
docker-compose logs | logstash | elasticsearch
```

### Alerts

```yaml
# Prometheus alert rules
groups:
- name: optifiner
  rules:
  - alert: HighErrorRate
    expr: rate(errors_total[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High error rate"

  - alert: LowFitnessImprovement
    expr: fitness_improvement < 1.01
    for: 1h
    annotations:
      summary: "Fitness not improving"

  - alert: HighCost
    expr: daily_cost_usd > 100
    for: 1h
    annotations:
      summary: "API costs exceeding budget"
```

## Security

### API Keys

```bash
# Store in secure vault
export GOOGLE_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id optifiner/google-api-key \
  --query SecretString --output text)
```

### Network Security

```yaml
# Network Policy - restrict traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: optifiner-network-policy
spec:
  podSelector:
    matchLabels:
      app: optifiner-worker
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: optifiner-api
```

### TLS/SSL

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/optifiner.crt;
    ssl_certificate_key /etc/ssl/optifiner.key;

    location /api {
        proxy_pass http://api:8000;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

### Access Control

```python
# In API backend
from fastapi_users import FastAPIUsers

@app.post("/projects")
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user)
):
    # Only authenticated users can create projects
    return await db.projects.create(current_user.id, project)
```

## Troubleshooting

### Worker Not Starting

```bash
# Check logs
docker-compose logs worker

# Common issues:
# 1. API key not set
export GOOGLE_API_KEY=xxx

# 2. Database not ready
docker-compose restart postgres
docker-compose restart worker

# 3. Out of memory
docker update --memory 8gb optifiner-worker
```

### High Latency

```bash
# Check resource usage
docker stats optifiner-worker

# If CPU bound: increase workers
# If memory bound: optimize code
# If I/O bound: optimize database queries
```

### Database Connections Exhausted

```bash
# Check connection count
SELECT count(*) FROM pg_stat_activity;

# Increase connection limit
# In postgresql.conf
max_connections = 500

# Or use connection pooling
docker run -d -p 5433:5432 \
  -e PGPOOL_NUM_INIT_CHILDREN=32 \
  pgpool2
```

### API Timeouts

```bash
# Increase timeout in load balancer
# nginx.conf
proxy_connect_timeout 30s;
proxy_read_timeout 60s;
proxy_send_timeout 30s;
```

## Scaling Guide

### Horizontal Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment optifiner-worker --replicas=5

# Or with Docker
docker-compose up -d --scale worker=5
```

### Vertical Scaling

```bash
# Increase resources per replica
kubectl set resources deployment optifiner-worker \
  --limits=cpu=4,memory=8Gi \
  --requests=cpu=2,memory=4Gi
```

### Auto-scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: optifiner-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: optifiner-worker
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Maintenance

### Database Backups

```bash
# Automated backup
docker exec optifiner-postgres pg_dump -U optifiner optifiner > backup_$(date +%Y%m%d).sql

# Or with AWS
aws s3 sync /var/optifiner/backups s3://my-bucket/optifiner-backups/
```

### Log Rotation

```bash
# logrotate configuration
/var/log/optifiner/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
}
```

### Updates

```bash
# Update to latest version
git pull origin main
docker-compose build
docker-compose up -d

# Rollback
git checkout previous-tag
docker-compose up -d
```
