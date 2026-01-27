---
phase: 01-infrastructure-foundation
plan: 05
subsystem: auth
tags: [jwt, token-exchange, better-auth, jose, api-client, frontend-backend-integration]

# Dependency graph
requires:
  - phase: 01-01
    provides: Backend foundation with FastAPI and structured logging
  - phase: 01-02
    provides: Frontend with Better Auth session management
  - phase: 01-03
    provides: Backend JWT validation middleware
  - phase: 01-04
    provides: Docker Compose orchestration with shared AUTH_SECRET
provides:
  - Token exchange endpoint converting Better Auth sessions to backend JWT tokens
  - API client with automatic token fetching and caching
  - End-to-end authenticated request flow from frontend to backend
  - Database schema initialization for Better Auth
  - Complete Phase 1 infrastructure verification
affects: [02-document-ingestion, 03-rag-pipeline, all-authenticated-features]

# Tech tracking
tech-stack:
  added: [jose]
  patterns: [token exchange pattern, JWT caching, bearer token authentication, database WAL mode]

key-files:
  created:
    - frontend/app/api/auth/backend-token/route.ts
    - frontend/lib/api-client.ts
    - frontend/scripts/create-schema.ts
    - frontend/scripts/init-db.ts
  modified:
    - frontend/app/dashboard/page.tsx
    - frontend/lib/auth.ts
    - docker-compose.override.yml

key-decisions:
  - "Token exchange pattern: Better Auth session -> JWT token via /api/auth/backend-token"
  - "Jose library for JWT creation (ESM-native, Next.js compatible)"
  - "15-minute token expiry with 1-minute refresh buffer"
  - "Token caching in memory to reduce exchange endpoint calls"
  - "Manual database schema creation (Better Auth v1.4.17 doesn't auto-create)"
  - "WAL mode enabled for better SQLite concurrency"
  - "Browser uses localhost:8000, server-side uses backend:8000 for API calls"

patterns-established:
  - "fetchWithAuth wrapper for all backend API calls"
  - "clearTokenCache on logout for security"
  - "ApiError class for structured error handling"
  - "Token exchange validates session before creating JWT"
  - "Dashboard UI pattern for testing backend integration"

# Metrics
duration: 30min
completed: 2026-01-27
---

# Phase 01 Plan 05: Frontend-Backend Auth Integration Summary

**Token exchange endpoint using jose library converts Better Auth sessions to backend JWT tokens with 15-minute expiry, cached API client attaches tokens to all backend requests, completing end-to-end authenticated flow with manual database schema initialization**

## Performance

- **Duration:** 30 min
- **Started:** 2026-01-27T19:38:00Z
- **Completed:** 2026-01-27T20:08:00Z
- **Tasks:** 2 (1 automated, 1 human verification checkpoint)
- **Files modified:** 7

## Accomplishments
- Token exchange endpoint at /api/auth/backend-token creates backend-compatible JWTs from Better Auth sessions
- API client with automatic token fetching, caching, and Bearer header attachment
- Dashboard testing interface for protected endpoint integration
- Manual database schema creation scripts for Better Auth tables
- WAL mode enabled for improved SQLite concurrency
- Complete end-to-end verification: register -> login -> dashboard -> backend API call -> logout
- Browser/server API URL configuration for Docker environment

## Task Commits

Each task was committed atomically:

1. **Task 1: Create token exchange endpoint and API client** - `d948d29` (feat)
   - Follow-up fix: Add database schema initialization - `31ea61f` (fix)
   - Follow-up fix: Use localhost for browser API requests - `5b9afe6` (fix)
   - Follow-up fix: Enable WAL mode and improve database initialization - `dbe029d` (fix)
2. **Task 2: Human verification checkpoint** - Approved by user

## Files Created/Modified
- `frontend/app/api/auth/backend-token/route.ts` - Token exchange endpoint validating session and creating JWT
- `frontend/lib/api-client.ts` - API client with token caching and fetchWithAuth wrapper
- `frontend/app/dashboard/page.tsx` - Dashboard with backend integration test UI
- `frontend/scripts/create-schema.ts` - Database schema creation for Better Auth tables
- `frontend/scripts/init-db.ts` - Database initialization utility
- `frontend/lib/auth.ts` - Enhanced with WAL mode and explicit database configuration
- `docker-compose.override.yml` - Added NEXT_PUBLIC_API_URL for browser API requests

## Decisions Made
- **Token exchange pattern**: Explicit endpoint to convert Better Auth session cookies to JWT tokens, ensuring deterministic flow without speculative behavior
- **Jose library**: ESM-native JWT library for Next.js compatibility (instead of jsonwebtoken)
- **15-minute token expiry**: Short-lived tokens with 1-minute refresh buffer for security
- **In-memory token caching**: Reduces exchange endpoint calls while maintaining security
- **Manual schema creation**: Better Auth v1.4.17 doesn't auto-create schema, requiring explicit initialization scripts
- **WAL mode for SQLite**: Enabled Write-Ahead Logging for better concurrency in Docker environment
- **Dual API URL configuration**: Browser uses localhost:8000 (can't resolve Docker service names), server-side uses backend:8000

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added database schema initialization scripts**
- **Found during:** Task 1 verification (Better Auth session creation failing)
- **Issue:** Better Auth v1.4.17 does not automatically create database schema on first run. Application failed with "no such table: user" error when attempting registration.
- **Fix:** Created manual schema initialization scripts (create-schema.ts, init-db.ts) with all required tables: user, session, account, verification. Includes foreign key constraints, indexes, and proper column types.
- **Files modified:** frontend/scripts/create-schema.ts, frontend/scripts/init-db.ts
- **Verification:** Database schema created successfully, user registration works
- **Committed in:** 31ea61f (separate fix commit)

**2. [Rule 3 - Blocking] Fixed browser API URL configuration**
- **Found during:** Task 1 verification (dashboard backend API call failing)
- **Issue:** Frontend API client using NEXT_PUBLIC_API_URL=http://backend:8000 from production config, but browsers cannot resolve Docker service names (only container-to-container networking works with service names).
- **Fix:** Added NEXT_PUBLIC_API_URL=http://localhost:8000 to docker-compose.override.yml for development. Browser-side requests now use localhost, server-side can still use 'backend' service name internally.
- **Files modified:** docker-compose.override.yml
- **Verification:** Dashboard "Test Protected Endpoint" button successfully calls backend API
- **Committed in:** 5b9afe6 (separate fix commit)

**3. [Rule 2 - Missing Critical] Enabled WAL mode for SQLite**
- **Found during:** Task 1 verification (potential concurrency issues)
- **Issue:** SQLite in Docker without WAL mode can have poor concurrency performance and locking issues with multiple requests.
- **Fix:** Enhanced frontend/lib/auth.ts to enable WAL (Write-Ahead Logging) mode, create explicit database instance with crypto.randomUUID() for ID generation, and improve database initialization.
- **Files modified:** frontend/lib/auth.ts
- **Verification:** Database operations smoother, no locking errors observed
- **Committed in:** dbe029d (separate fix commit)

---

**Total deviations:** 3 auto-fixed (2 missing critical, 1 blocking)
**Impact on plan:** All fixes essential for basic functionality and security. Database schema creation and WAL mode are critical for Better Auth to work in Docker. Browser API URL fix unblocks end-to-end testing. No scope creep.

## Issues Encountered
- **Better Auth schema auto-creation**: Documentation suggests auto-creation, but v1.4.17 requires manual schema initialization. Resolved by creating explicit schema creation scripts.
- **Docker networking vs browser networking**: Service names work container-to-container but not browser-to-container. Resolved with dual configuration using NEXT_PUBLIC_API_URL override for development.

## User Setup Required

**Environment configuration:**

Users must:
1. Copy `.env.example` to `.env`
2. Generate AUTH_SECRET: `openssl rand -base64 32`
3. Set AUTH_SECRET in `.env` (used as both BETTER_AUTH_SECRET and JWT_SECRET_KEY)

**First-time database setup:**
```bash
cd frontend
npm run init-db  # Creates database schema
```

This is required before first use. The init-db script is idempotent and safe to run multiple times.

## Next Phase Readiness

**Phase 1 Infrastructure Foundation: COMPLETE**

All infrastructure components verified:
- Backend FastAPI with structured logging and JWT validation
- Frontend Next.js with Better Auth session management
- Token exchange pattern for frontend-to-backend authentication
- Docker Compose orchestration with all services healthy
- FalkorDB ready for knowledge graph (Phase 4)
- End-to-end auth flow working: register -> login -> dashboard -> backend API -> logout

**Ready for Phase 2: Document Ingestion**
- Authentication infrastructure complete
- Docker environment verified
- API client pattern established for backend communication
- Structured logging captures request flow
- All services healthy and communicating

**No blockers or concerns for next phase.**

---
*Phase: 01-infrastructure-foundation*
*Completed: 2026-01-27*
