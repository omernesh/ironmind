---
phase: 06-frontend-integration-deployment
plan: 04
subsystem: infra
tags: [docker, caddy, https, production, deployment, gunicorn, multi-stage-build]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: Docker Compose development setup, Dockerfiles for frontend and backend
  - phase: 06-frontend-integration-deployment
    provides: Frontend and backend applications ready for production deployment
provides:
  - Production Docker Compose with Caddy reverse proxy for HTTPS
  - Optimized multi-stage Dockerfiles for frontend and backend
  - Production environment configuration template
  - Automatic SSL certificate management
affects: [deployment, production-operations, ssl-setup, hetzner-vps]

# Tech tracking
tech-stack:
  added: [caddy:2-alpine, gunicorn]
  patterns: [multi-stage docker builds, reverse proxy with automatic HTTPS, production optimized images]

key-files:
  created:
    - infra/docker-compose.prod.yml
    - infra/Caddyfile
    - infra/.env.production.example
    - backend/.dockerignore
  modified:
    - frontend/Dockerfile
    - backend/Dockerfile
    - frontend/.dockerignore

key-decisions:
  - "Caddy for automatic HTTPS instead of nginx with certbot (simpler configuration)"
  - "Subdomain routing (api.domain.com) instead of path-based (/api/*) for API"
  - "4 Gunicorn workers with Uvicorn worker class (2x CPU cores for I/O bound)"
  - "120s timeout for document processing operations"
  - "Build-time NEXT_PUBLIC_* environment variables for frontend"

patterns-established:
  - "Multi-stage builds with separate deps, builder, runner stages"
  - "Non-root users (nextjs:nodejs, appuser) for security"
  - "Health checks with service dependencies for startup ordering"
  - "Persistent volumes for SSL certs (caddy_data) and application data"

# Metrics
duration: 6min
completed: 2026-01-29
---

# Phase 6 Plan 4: Production Docker Deployment Summary

**Production-ready Docker deployment with Caddy automatic HTTPS, optimized multi-stage images, and 4-worker Gunicorn backend**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-29T16:14:05Z
- **Completed:** 2026-01-29T16:19:43Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Production Docker Compose with Caddy reverse proxy for automatic HTTPS
- Optimized frontend Dockerfile with standalone output and build-time environment variables
- Production backend Dockerfile with Gunicorn (4 workers) and 120s timeout
- Caddyfile with subdomain routing, security headers, and CORS configuration
- Environment template for production deployment with domain configuration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create infra directory with production Docker Compose** - `f729f5d` (feat)
2. **Task 2: Create Caddyfile for reverse proxy** - `ca6a8dd` (feat)
3. **Task 3: Optimize Dockerfiles for production** - `4a59368` (feat)

## Files Created/Modified

**Created:**
- `infra/docker-compose.prod.yml` - Production orchestration with Caddy, frontend, backend, FalkorDB, Docling
- `infra/Caddyfile` - HTTPS routing configuration with automatic SSL certificate management
- `infra/.env.production.example` - Production environment template with domain, URLs, API keys
- `backend/.dockerignore` - Excludes tests, logs, planning files from Docker build context

**Modified:**
- `frontend/Dockerfile` - Multi-stage build with build args for NEXT_PUBLIC_* variables, standalone output
- `backend/Dockerfile` - Gunicorn with 4 Uvicorn workers, 120s timeout, graceful shutdown
- `frontend/.dockerignore` - Updated to exclude .env*, logs, planning files

## Decisions Made

**Caddy over nginx:** Selected Caddy for automatic HTTPS instead of nginx with certbot for simpler configuration and automatic certificate renewal

**Subdomain routing:** API served at api.domain.com instead of path-based /api/* routing for cleaner separation and easier CORS management

**4 Gunicorn workers:** Configured 4 workers (2x typical CPU cores) with Uvicorn worker class for I/O bound document processing

**120s timeout:** Set Gunicorn timeout to 120s to accommodate document processing (docling parsing can take 30-60s for large PDFs with OCR)

**Build-time environment variables:** NEXT_PUBLIC_* variables passed as Docker build args (baked into JS at build time) for proper Next.js standalone builds

**No port exposure:** Frontend and backend ports not exposed externally - Caddy handles all external traffic on 80/443

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - Docker configurations validated successfully with `docker-compose config`.

## User Setup Required

**Production deployment requires manual configuration.** Before deploying:

1. Copy `infra/.env.production.example` to `infra/.env.production`
2. Configure required environment variables:
   - `DOMAIN`: Your domain (e.g., ironmind.yourdomain.com)
   - `NEXT_PUBLIC_APP_URL`: Frontend URL (https://ironmind.yourdomain.com)
   - `NEXT_PUBLIC_API_URL`: Backend URL (https://api.ironmind.yourdomain.com)
   - `CORS_ORIGINS`: Frontend URL for CORS (https://ironmind.yourdomain.com)
   - `AUTH_SECRET`: Generate with `openssl rand -hex 32`
   - `OPENAI_API_KEY`: OpenAI API key for embeddings and generation
   - `DEEPINFRA_API_KEY`: DeepInfra API key for reranking
3. Configure DNS:
   - Point `ironmind.yourdomain.com` to server IP (A record)
   - Point `api.ironmind.yourdomain.com` to server IP (A record)
4. Deploy on Hetzner VPS:
   ```bash
   # Clone repository
   git clone <repo-url> ironmind
   cd ironmind/infra

   # Create .env.production from template
   cp .env.production.example .env.production
   # Edit .env.production with your values

   # Build and start services
   docker-compose -f docker-compose.prod.yml up -d

   # Check logs
   docker-compose -f docker-compose.prod.yml logs -f
   ```
5. Verify deployment:
   - Frontend: https://ironmind.yourdomain.com
   - Backend: https://api.ironmind.yourdomain.com/health
   - SSL certificates: Check Caddy logs for automatic certificate acquisition

## Next Phase Readiness

**Production deployment infrastructure complete:**
- Docker Compose production configuration ready for Hetzner VPS
- Automatic HTTPS with Caddy (no manual certificate management)
- Optimized images with multi-stage builds (smaller size, faster startup)
- Security: non-root users, health checks, restart policies
- Persistent volumes for SSL certs and application data

**Ready for:**
- Deployment to Hetzner VPS
- SSL certificate acquisition (automatic via Caddy)
- Production traffic

**Remaining Phase 6 tasks:**
- Plan 06-05: Deployment guide and monitoring setup (if needed)
- System testing and verification on production environment

---
*Phase: 06-frontend-integration-deployment*
*Completed: 2026-01-29*
