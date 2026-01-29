# IRONMIND Deployment Guide

## Production Deployment

**Live Instance:** https://ironmind.chat
**API Endpoint:** https://api.ironmind.chat
**Server IP:** 65.108.249.67
**SSH Key:** `~/.ssh/ironmind_hetzner`
**Deploy User:** deploy
**Deploy Path:** `/home/deploy/ironmind`

### Accessing Production Server

```bash
# SSH into production server
ssh -i ~/.ssh/ironmind_hetzner root@65.108.249.67

# Switch to deploy user
su - deploy
cd ~/ironmind

# Check service status
docker compose -f infra/docker-compose.prod.yml ps

# View logs
docker compose -f infra/docker-compose.prod.yml logs -f backend
docker compose -f infra/docker-compose.prod.yml logs -f frontend
```

## Local Development

### Prerequisites

- Docker Desktop 4.x+
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd ironmind

# Copy environment template
cp .env.example .env

# Edit .env with your API keys:
# - OPENAI_API_KEY
# - DEEPINFRA_API_KEY
# - AUTH_SECRET (generate with: openssl rand -hex 32)

# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

### Development Mode

For hot-reload during development:

```bash
# Terminal 1: Backend with auto-reload
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend with hot-reload
cd frontend
npm install
npm run dev

# Terminal 3: Supporting services
docker-compose up falkordb docling
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for embeddings and generation |
| `DEEPINFRA_API_KEY` | Yes | DeepInfra key for Qwen reranker |
| `AUTH_SECRET` | Yes | JWT secret (32+ hex chars) |
| `CORS_ORIGINS` | No | Allowed origins (default: localhost:3000) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

## Production Deployment (Hetzner VPS)

### Server Requirements

- Hetzner CX21 or CX31 (2 vCPU, 4-8GB RAM)
- Ubuntu 22.04 LTS
- Docker & Docker Compose installed
- Domain with DNS configured

### Initial Setup

```bash
# SSH into server
ssh root@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin

# Create deployment user
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# Clone repository
su - deploy
git clone <repository-url>
cd ironmind
```

### Configuration

```bash
# Copy production environment template
cp infra/.env.production.example infra/.env.production

# Edit production config
nano infra/.env.production
```

Required settings:
- `DOMAIN`: Your domain (e.g., ironmind.example.com)
- `NEXT_PUBLIC_APP_URL`: https://ironmind.example.com
- `NEXT_PUBLIC_API_URL`: https://api.ironmind.example.com
- `CORS_ORIGINS`: https://ironmind.example.com
- API keys for OpenAI and DeepInfra

### Deploy

```bash
# Build and start production stack
cd infra
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Verify services
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

### SSL Certificates

Caddy automatically obtains Let's Encrypt certificates. Ensure:
- Port 80 and 443 are open in firewall
- DNS A records point to server IP
- `caddy_data` volume persists (never delete)

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Zero-downtime: new containers start before old ones stop
```

### Monitoring

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Check resource usage
docker stats

# Health check
curl https://your-domain.com/health
```

### Backup

```bash
# Backup volumes
docker run --rm -v ironmind_backend-data:/data -v $(pwd):/backup alpine tar cvf /backup/backend-data.tar /data
docker run --rm -v ironmind_falkordb-data:/data -v $(pwd):/backup alpine tar cvf /backup/falkordb-data.tar /data
```

## Troubleshooting

### Common Issues

**Frontend can't reach backend**
- Check CORS_ORIGINS includes frontend domain
- Verify Caddyfile routes correctly
- Check backend health: `curl http://localhost:8000/health`

**SSL certificate issues**
- Ensure ports 80/443 are open
- Check DNS propagation: `dig your-domain.com`
- View Caddy logs: `docker logs ironmind-caddy-1`

**Document processing stuck**
- Check Docling health: `curl http://localhost:5001/health`
- Increase Docling memory if OOM
- View processing logs in backend

**Out of memory**
- Docling uses ~2GB for large PDFs
- Consider CX31 (8GB RAM) for production
- Limit concurrent document processing
