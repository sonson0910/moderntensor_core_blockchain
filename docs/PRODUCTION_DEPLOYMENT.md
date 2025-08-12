# 🚀 ModernTensor Core - Production Deployment Guide

## 📋 Overview

This guide covers the complete production deployment of ModernTensor Core on Core blockchain infrastructure.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer (nginx/cloudflare)                           │
│  ├── API Gateway (8000)                                     │
│  ├── Monitoring Dashboard (9090)                            │
│  └── Health Check Endpoint (8080)                           │
├─────────────────────────────────────────────────────────────┤
│  Application Layer                                           │
│  ├── ModernTensor Core API                                  │
│  ├── Async Blockchain Client                                │
│  ├── Consensus Engine                                       │
│  └── Network Protocol Handler                               │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  ├── Redis (Cache/Session)                                  │
│  ├── PostgreSQL (Persistent Data)                           │
│  └── File Storage (Logs/Artifacts)                          │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                        │
│  ├── Docker Containers                                      │
│  ├── Kubernetes Orchestration                               │
│  ├── Monitoring Stack (Prometheus/Grafana)                  │
│  └── Security Scanning                                      │
├─────────────────────────────────────────────────────────────┤
│  External Dependencies                                       │
│  ├── Core Blockchain Network                                │
│  ├── Bitcoin Network (for staking)                          │
│  ├── IPFS (Distributed Storage)                             │
│  └── External APIs                                          │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Prerequisites

### System Requirements
- **CPU**: Minimum 4 cores, Recommended 8+ cores
- **Memory**: Minimum 8GB RAM, Recommended 16GB+
- **Storage**: Minimum 100GB SSD, Recommended 500GB+ NVMe
- **Network**: Reliable internet connection with low latency
- **OS**: Ubuntu 22.04 LTS or similar Linux distribution

### Required Services
- Docker Engine 24.0+
- Docker Compose 2.0+
- Kubernetes 1.25+ (for orchestration)
- nginx (load balancer)
- SSL certificates (Let's Encrypt recommended)

### External Dependencies
- Core blockchain RPC endpoint
- Redis instance (cluster recommended)
- PostgreSQL database (high availability setup)
- Monitoring infrastructure (Prometheus/Grafana)

## 🚀 Deployment Steps

### Step 1: Environment Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install kubectl (if using Kubernetes)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

### Step 2: Configuration Setup

```bash
# Clone repository
git clone <repository-url>
cd moderntensor_core

# Create environment file
cp moderntensor_aptos/mt_core/config/blockchain.yaml.example production.env
```

#### Environment Configuration (`production.env`)
```yaml
# Blockchain Configuration
BLOCKCHAIN_NETWORK=mainnet
CORE_RPC_URL=https://rpc.coredao.org
CORE_TOKEN_ADDRESS=0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f
CONTRACT_ADDRESS=<deployed_contract_address>

# Database Configuration
DATABASE_URL=postgresql://user:password@db-host:5432/moderntensor
REDIS_URL=redis://redis-host:6379

# Security Configuration
SECRET_KEY=<secure_random_key>
JWT_SECRET=<jwt_secret_key>
ENCRYPTION_KEY=<encryption_key>

# Monitoring Configuration
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000

# External Services
IPFS_GATEWAY=https://gateway.pinata.cloud
BITCOIN_RPC_URL=<bitcoin_rpc_endpoint>

# Application Configuration
LOG_LEVEL=INFO
MAX_WORKERS=8
ENABLE_MONITORING=true
ENABLE_SECURITY_SCANNING=true
```

### Step 3: Database Setup

```sql
-- PostgreSQL setup
CREATE DATABASE moderntensor;
CREATE USER moderntensor_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE moderntensor TO moderntensor_user;

-- Create required tables
\c moderntensor;

CREATE TABLE miners (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(256) UNIQUE NOT NULL,
    owner_address VARCHAR(42) NOT NULL,
    stake_amount BIGINT NOT NULL,
    subnet_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE validators (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(256) UNIQUE NOT NULL,
    owner_address VARCHAR(42) NOT NULL,
    stake_amount BIGINT NOT NULL,
    subnet_id INTEGER NOT NULL,
    trust_score DECIMAL(5,4) DEFAULT 0.5,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    from_address VARCHAR(42) NOT NULL,
    to_address VARCHAR(42) NOT NULL,
    amount BIGINT NOT NULL,
    gas_used INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_miners_subnet ON miners(subnet_id);
CREATE INDEX idx_validators_subnet ON validators(subnet_id);
CREATE INDEX idx_transactions_status ON transactions(status);
```

### Step 4: Docker Deployment

#### Option A: Docker Compose (Recommended for single-node)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  moderntensor-core:
    build: .
    container_name: moderntensor-core
    restart: unless-stopped
    environment:
      - MODERNTENSOR_ENV=production
    env_file:
      - production.env
    ports:
      - "8000:8000"
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./monitoring/results:/app/monitoring/results
    depends_on:
      - redis
      - postgres
    healthcheck:
      test: ["CMD", "python", "/app/healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: moderntensor-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    container_name: moderntensor-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: moderntensor
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  nginx:
    image: nginx:alpine
    container_name: moderntensor-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - moderntensor-core

  prometheus:
    image: prom/prometheus:latest
    container_name: moderntensor-prometheus
    restart: unless-stopped
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    container_name: moderntensor-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  redis_data:
  postgres_data:
  prometheus_data:
  grafana_data:
```

#### Deploy with Docker Compose
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f moderntensor-core
```

#### Option B: Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moderntensor-core
  labels:
    app: moderntensor-core
spec:
  replicas: 3
  selector:
    matchLabels:
      app: moderntensor-core
  template:
    metadata:
      labels:
        app: moderntensor-core
    spec:
      containers:
      - name: moderntensor-core
        image: moderntensor/core:latest
        ports:
        - containerPort: 8000
        - containerPort: 8080
        - containerPort: 9090
        env:
        - name: MODERNTENSOR_ENV
          value: "production"
        envFrom:
        - secretRef:
            name: moderntensor-secrets
        volumeMounts:
        - name: logs
          mountPath: /app/logs
        - name: data
          mountPath: /app/data
        livenessProbe:
          exec:
            command:
            - python
            - /app/healthcheck.py
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: logs
        persistentVolumeClaim:
          claimName: moderntensor-logs
      - name: data
        persistentVolumeClaim:
          claimName: moderntensor-data

---
apiVersion: v1
kind: Service
metadata:
  name: moderntensor-service
spec:
  selector:
    app: moderntensor-core
  ports:
  - name: api
    port: 8000
    targetPort: 8000
  - name: health
    port: 8080
    targetPort: 8080
  - name: monitoring
    port: 9090
    targetPort: 9090
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: moderntensor-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.moderntensor.io
    secretName: moderntensor-tls
  rules:
  - host: api.moderntensor.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: moderntensor-service
            port:
              number: 8000
```

### Step 5: SSL Configuration

#### nginx.conf
```nginx
upstream moderntensor_backend {
    server moderntensor-core:8000;
}

server {
    listen 80;
    server_name api.moderntensor.io;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.moderntensor.io;

    ssl_certificate /etc/ssl/certs/moderntensor.crt;
    ssl_certificate_key /etc/ssl/certs/moderntensor.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # API endpoints
    location / {
        proxy_pass http://moderntensor_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://moderntensor-core:8080/health;
        access_log off;
    }

    # Monitoring endpoint (restricted)
    location /monitoring {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        
        proxy_pass http://moderntensor-core:9090;
    }
}

# Rate limiting
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

### Step 6: Monitoring Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "moderntensor_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'moderntensor'
    static_configs:
      - targets: ['moderntensor-core:9090']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

### Step 7: Security Hardening

```bash
# Firewall configuration
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw deny 8000   # Block direct API access
sudo ufw deny 5432   # Block direct DB access
sudo ufw deny 6379   # Block direct Redis access

# System hardening
echo "net.ipv4.ip_forward=0" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.send_redirects=0" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.accept_redirects=0" >> /etc/sysctl.conf
sysctl -p

# Docker security
echo '{"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}}' > /etc/docker/daemon.json
systemctl restart docker

# Regular security updates
echo "0 2 * * * root apt update && apt upgrade -y" >> /etc/crontab
```

## 📊 Monitoring & Alerting

### Key Metrics to Monitor

1. **System Metrics**
   - CPU usage (alert > 80%)
   - Memory usage (alert > 85%)
   - Disk usage (alert > 90%)
   - Network I/O

2. **Application Metrics**
   - API response times
   - Request rates
   - Error rates
   - Database connection pool
   - Cache hit rates

3. **Blockchain Metrics**
   - RPC response times
   - Gas prices
   - Block heights
   - Transaction confirmation times

4. **Business Metrics**
   - Active miners/validators
   - Staking amounts
   - Subnet activity
   - Reward distributions

### Grafana Dashboards

Import the following dashboard configurations:

1. **System Overview**: CPU, Memory, Disk, Network
2. **Application Performance**: API metrics, response times
3. **Blockchain Health**: RPC status, gas prices, connectivity
4. **Business Intelligence**: Staking, rewards, participant activity

## 🔄 Backup & Recovery

### Database Backup
```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create backup
docker exec moderntensor-postgres pg_dump -U moderntensor_user moderntensor > $BACKUP_DIR/backup_$TIMESTAMP.sql

# Compress backup
gzip $BACKUP_DIR/backup_$TIMESTAMP.sql

# Remove backups older than 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# Upload to cloud storage (optional)
aws s3 sync $BACKUP_DIR s3://moderntensor-backups/postgres/
```

### Application Data Backup
```bash
# Backup logs and monitoring data
tar -czf /backups/app_data_$(date +%Y%m%d).tar.gz \
    /app/logs \
    /app/monitoring/results \
    /app/data

# Backup smart contract artifacts
tar -czf /backups/contracts_$(date +%Y%m%d).tar.gz \
    /app/moderntensor_aptos/mt_core/smartcontract/artifacts
```

## 🚨 Incident Response

### Automated Recovery Procedures

1. **Service Health Check Failure**
   - Restart container
   - Check resource availability
   - Verify external dependencies

2. **Database Connection Issues**
   - Check connection pool
   - Verify credentials
   - Restart database if needed

3. **Blockchain Connectivity Issues**
   - Switch to backup RPC endpoint
   - Check network connectivity
   - Alert operations team

### Manual Escalation Triggers

- Critical alerts unresolved for 15+ minutes
- Multiple service failures
- Security incidents
- Data corruption detected

## 📈 Scaling Considerations

### Horizontal Scaling
- Add more application replicas
- Implement load balancing
- Use Redis cluster for caching
- Database read replicas

### Vertical Scaling
- Increase container resources
- Optimize database queries
- Implement connection pooling
- Cache frequently accessed data

### Performance Optimization
- Enable HTTP/2 and compression
- Implement CDN for static assets
- Optimize database indexes
- Use async processing for heavy operations

## 🔒 Security Checklist

- [ ] SSL/TLS certificates installed and configured
- [ ] Firewall rules properly configured
- [ ] Regular security updates automated
- [ ] Database credentials secured
- [ ] API rate limiting implemented
- [ ] Security headers configured
- [ ] Intrusion detection system active
- [ ] Regular security scans scheduled
- [ ] Backup encryption enabled
- [ ] Access logs monitored

## 📞 Support & Maintenance

### Regular Maintenance Tasks

**Daily:**
- Check system health dashboards
- Review error logs
- Verify backup completion

**Weekly:**
- Review performance metrics
- Update dependencies (non-critical)
- Security scan results review

**Monthly:**
- Full system backup verification
- Performance optimization review
- Security audit
- Capacity planning review

### Emergency Contacts

- **Operations Team**: ops@moderntensor.io
- **Security Team**: security@moderntensor.io
- **Development Team**: dev@moderntensor.io
- **On-call Engineer**: +1-xxx-xxx-xxxx

## 🎯 Success Metrics

**Performance Targets:**
- API response time: < 200ms (95th percentile)
- Uptime: > 99.9%
- Error rate: < 0.1%
- Transaction processing: < 30s confirmation

**Business Targets:**
- Active miners: 1000+
- Total staked value: $10M+
- Daily transactions: 10,000+
- Network participation: 80%+

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-29 | Initial production deployment |
| 1.0.1 | TBD | Security updates and performance improvements |

**Deployment Status**: ✅ Production Ready

**Last Updated**: January 29, 2024
**Next Review**: February 29, 2024 