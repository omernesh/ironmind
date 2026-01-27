# Phase 1: Infrastructure Foundation - Research

**Researched:** 2026-01-27
**Domain:** FastAPI backend infrastructure, Better Auth authentication, Docker Compose orchestration, structured logging
**Confidence:** MEDIUM-HIGH

## Summary

Phase 1 establishes production-ready infrastructure for IRONMIND with authentication, multi-service orchestration, and observability. The research confirms the chosen technology stack is well-aligned with modern best practices for 5-day rapid deployment scenarios.

**Better Auth** provides TypeScript-first authentication with email/password support, session management, and email verification flows. It uses database-backed sessions with optional cookie caching for performance. The library integrates cleanly with Next.js frontend while providing backend API validation methods.

**FastAPI** with JWT token validation via dependency injection is the standard approach for backend authentication. Using `HTTPException(status_code=401)` with proper headers ensures OAuth2 compliance. The `asgi-correlation-id` middleware combined with **structlog** enables production-grade structured JSON logging with request correlation across pipeline stages.

**Docker Compose** remains the industry standard for local development and small-scale production deployments. Service-to-service communication uses service names (not localhost), and secrets should be mounted as files rather than environment variables for security.

**Primary recommendation:** Use Better Auth with email/password + email verification, FastAPI with dependency injection for token validation, asgi-correlation-id + structlog for logging, and Docker Compose with user-defined networks and secrets management.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Better Auth | latest (2026) | Frontend authentication | TypeScript-first, framework-agnostic, built-in email/password with verification, modern alternative to NextAuth |
| FastAPI | 0.100+ | Backend API framework | Async-first, type-safe, built-in OAuth2 support with dependency injection |
| PyJWT | 2.8+ | JWT token handling | Official JWT implementation, recommended by FastAPI docs |
| pwdlib | latest | Password hashing | Modern replacement for passlib, uses Argon2 (recommended by FastAPI) |
| structlog | 24.1+ | Structured logging | Industry standard for JSON logging in Python, context variable support |
| asgi-correlation-id | 4.3+ | Request correlation | FastAPI-specific middleware for distributed tracing |
| Gunicorn | 21+ | Production server | Industry standard WSGI server, works with Uvicorn workers |
| Uvicorn | 0.25+ | ASGI server | FastAPI's recommended ASGI implementation, supports workers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi-mail | 1.4+ | Email sending | SMTP integration for verification/password reset emails |
| python-dotenv | 1.0+ | Environment config | Loading .env files in development |
| fastapi-healthchecks | latest | Health endpoints | Kubernetes-style liveness/readiness probes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Better Auth | NextAuth.js / Auth.js | NextAuth.js is now part of Better Auth ecosystem; Better Auth is more modern |
| PyJWT | python-jose | PyJWT is simpler and officially recommended by FastAPI as of 2025 |
| structlog | Python logging | Standard logging lacks context variables, harder to configure for JSON |
| Argon2 (pwdlib) | bcrypt | Argon2 is memory-hard, more resistant to GPU attacks |

**Installation:**
```bash
# Backend (FastAPI)
pip install fastapi[standard] uvicorn[standard] gunicorn
pip install pyjwt pwdlib python-multipart
pip install structlog asgi-correlation-id
pip install fastapi-mail python-dotenv

# Frontend (Next.js)
npm install better-auth
npm install @better-auth/react  # For React hooks
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Settings with pydantic-settings
│   ├── middleware/
│   │   ├── auth.py          # JWT validation dependency
│   │   └── logging.py       # Structlog configuration
│   ├── routers/
│   │   └── health.py        # Health check endpoint
│   └── core/
│       └── security.py      # JWT utilities
├── requirements.txt
├── Dockerfile
└── .env

frontend/
├── app/
│   ├── api/
│   │   └── auth/
│   │       └── [...all]/route.ts  # Better Auth handler
│   └── lib/
│       ├── auth.ts          # Better Auth server config
│       └── auth-client.ts   # Better Auth React client
├── package.json
└── .env.local

docker-compose.yml
.env                          # Shared environment variables
```

### Pattern 1: FastAPI JWT Validation with Dependency Injection
**What:** Use FastAPI's dependency system to validate JWT tokens and extract user_id
**When to use:** Every protected endpoint that requires authentication
**Example:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt
from jwt.exceptions import InvalidTokenError

security = HTTPBearer()

async def get_current_user_id(token: str = Depends(security)) -> str:
    """Validate JWT token and extract user_id."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Better Auth tokens use 'sub' claim for user ID
        payload = jwt.decode(
            token.credentials,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except InvalidTokenError:
        raise credentials_exception

# Usage in endpoint
@app.get("/api/protected")
async def protected_route(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id}
```

### Pattern 2: Structured Logging with Request Correlation
**What:** Configure structlog with asgi-correlation-id for JSON logging with request_id
**When to use:** Application initialization in main.py
**Example:**
```python
# Source: https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e
import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

# Add middleware
app.add_middleware(CorrelationIdMiddleware)

# Usage in code
logger = structlog.get_logger()

@app.get("/api/process")
async def process_request():
    logger.info("processing_started", step="docling")
    # request_id automatically included from correlation_id
    return {"status": "ok"}
```

### Pattern 3: Better Auth Email/Password Setup
**What:** Configure Better Auth with email verification and password reset
**When to use:** Frontend authentication initialization
**Example:**
```typescript
// Source: https://www.better-auth.com/docs/authentication/email-password
import { betterAuth } from "better-auth";
import { sendEmail } from "./email-provider";

export const auth = betterAuth({
  database: {
    provider: "postgres",
    url: process.env.DATABASE_URL
  },
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: true,
    minPasswordLength: 8,
    sendVerificationEmail: async ({ user, url, token }) => {
      await sendEmail({
        to: user.email,
        subject: "Verify your email",
        html: `Click to verify: <a href="${url}">Verify Email</a>`
      });
    },
    sendResetPassword: async ({ user, url, token }) => {
      await sendEmail({
        to: user.email,
        subject: "Reset your password",
        html: `Click to reset: <a href="${url}">Reset Password</a>`
      });
    }
  }
});
```

### Pattern 4: Docker Compose Service Communication
**What:** Services communicate via service names on internal ports, not localhost
**When to use:** All inter-service communication in Docker Compose
**Example:**
```yaml
# Source: https://docs.docker.com/compose/how-tos/networking/
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://db:5432/ironmind
      - FALKORDB_URL=redis://falkordb:6379
    depends_on:
      - falkordb

  falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "6379:6379"
    volumes:
      - falkordb_data:/data
    environment:
      - REDIS_ARGS=--requirepass ${FALKORDB_PASSWORD}

volumes:
  falkordb_data:
```

### Pattern 5: Health Check Endpoints
**What:** Separate liveness and readiness probes for Kubernetes-style health checks
**When to use:** Backend API initialization
**Example:**
```python
# Source: https://www.index.dev/blog/how-to-implement-health-check-in-python
from fastapi import APIRouter, status

router = APIRouter()

@router.get("/health")
async def health_check():
    """Liveness probe - is the app running?"""
    return {"status": "healthy"}

@router.get("/ready")
async def readiness_check():
    """Readiness probe - can the app handle traffic?"""
    # Check critical dependencies with timeout
    try:
        # await check_database_connection(timeout=2)
        # await check_falkordb_connection(timeout=2)
        return {"status": "ready"}
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")
```

### Anti-Patterns to Avoid
- **Using localhost in Docker Compose**: Each container has its own localhost. Use service names instead.
- **Storing secrets in environment variables**: Use Docker secrets or mounted files for passwords/API keys.
- **Validating auth in middleware globally**: Better Auth recommends validating per-route for flexibility.
- **Blocking email sending**: Don't await email sending in password reset to prevent timing attacks.
- **Exposing /docs in production**: Disable FastAPI docs endpoints or protect them with authentication.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request correlation IDs | Custom middleware with UUID generation | asgi-correlation-id | Handles header extraction, generation, context variables, and Celery propagation |
| JWT token validation | Manual token parsing and validation | FastAPI OAuth2PasswordBearer + PyJWT | Handles OAuth2 spec, automatic 401 responses, OpenAPI docs integration |
| Structured logging | Custom JSON formatters | structlog | Context variables, processor chains, async-safe, production-tested |
| Email sending | Raw SMTP connection | fastapi-mail | Connection pooling, template support, attachment handling, async support |
| Password hashing | Custom bcrypt/Argon2 implementation | pwdlib | Secure defaults, algorithm agility, timing-attack protection |
| Session management | Custom session store | Better Auth | Database sessions, cookie caching, refresh tokens, secure defaults |
| Health checks | Simple status endpoints | fastapi-healthchecks | Liveness/readiness separation, dependency checks, timeout handling |

**Key insight:** Authentication and observability are security-critical domains where custom implementations often miss edge cases. Better Auth handles timing attacks, token rotation, and session fixation. Structlog and asgi-correlation-id provide battle-tested correlation across async contexts. Use proven libraries for these foundational concerns.

## Common Pitfalls

### Pitfall 1: Using localhost for Inter-Container Communication
**What goes wrong:** Backend tries to connect to `localhost:6379` for FalkorDB and connection fails.
**Why it happens:** Each container has its own network namespace; localhost refers to the container itself, not the host or other containers.
**How to avoid:** Use service names defined in docker-compose.yml (e.g., `redis://falkordb:6379` not `redis://localhost:6379`).
**Warning signs:** "Connection refused" errors in logs despite services running; `docker ps` shows services healthy but app can't connect.

### Pitfall 2: Secrets in Environment Variables
**What goes wrong:** Passwords and API keys leak through logs, process listings, or error messages.
**Why it happens:** Environment variables are visible to all processes and often logged during debugging.
**How to avoid:** Use Docker secrets mounted at `/run/secrets/<secret_name>` or load from files specified in env vars (e.g., `DATABASE_PASSWORD_FILE=/run/secrets/db_password`).
**Warning signs:** Secrets visible in `docker inspect`, GitHub Actions logs showing full env vars, accidental commits of .env files.

### Pitfall 3: CSRF with Cookie-Based Auth
**What goes wrong:** Cross-site requests can perform actions on behalf of authenticated users.
**Why it happens:** Better Auth uses cookies for sessions; browsers automatically send cookies with all requests to the domain.
**How to avoid:** For Better Auth + separate backend, use Bearer token approach (JWT in Authorization header) instead of cookie-based sessions. Or implement CSRF tokens if using cookies.
**Warning signs:** Security audit flags CSRF vulnerabilities; malicious sites can trigger actions without user consent.

### Pitfall 4: Blocking on Email Sending
**What goes wrong:** Password reset endpoint takes 5+ seconds to respond; timing attacks reveal valid email addresses.
**Why it happens:** Synchronous SMTP connection and email sending blocks the async request handler.
**How to avoid:** Don't await email sending in Better Auth callbacks; use background tasks or message queue. Return immediately after queueing.
**Warning signs:** Slow auth endpoints; response times differ between valid/invalid emails; SMTP timeouts cause 500 errors.

### Pitfall 5: Context Variable Leakage in Async Code
**What goes wrong:** Request correlation IDs from one request appear in logs for another request.
**Why it happens:** Structlog's contextvars can leak between async contexts if not properly isolated.
**How to avoid:** Use `asgi-correlation-id` middleware which properly manages context lifecycle. Clear context variables at request boundaries.
**Warning signs:** Correlation IDs in logs don't match request headers; multiple requests share the same correlation ID.

### Pitfall 6: Exposing Database Connection Strings
**What goes wrong:** Database credentials exposed in Docker Compose files or FastAPI error messages.
**Why it happens:** Direct use of connection strings in config; FastAPI debug mode shows full tracebacks.
**How to avoid:** Use secrets for credentials; disable debug mode in production; configure Uvicorn to hide detailed errors.
**Warning signs:** Connection strings in Git history; Sentry/logging shows full DATABASE_URL values.

### Pitfall 7: Better Auth Session Validation on Every Request
**What goes wrong:** Database hammered with session lookups; 100ms+ added to every request.
**Why it happens:** Default Better Auth session validation queries database on each request.
**How to avoid:** Enable cookie caching in Better Auth config; session data stored in signed cookie, DB only checked when cache expires.
**Warning signs:** High database CPU; slow response times; database connection pool exhaustion.

## Code Examples

Verified patterns from official sources:

### Health Check Endpoint (Liveness + Readiness)
```python
# Source: https://www.index.dev/blog/how-to-implement-health-check-in-python
from fastapi import APIRouter, HTTPException, status
import structlog

logger = structlog.get_logger()
router = APIRouter()

@router.get("/health")
async def health():
    """Liveness probe - basic app health."""
    return {"status": "healthy"}

@router.get("/ready")
async def readiness():
    """Readiness probe - dependency health."""
    checks = {}
    all_healthy = True

    # Check critical dependencies with timeouts
    # Note: Implement actual checks based on your dependencies

    if not all_healthy:
        logger.warning("readiness_check_failed", checks=checks)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks}
        )

    return {"status": "ready", "checks": checks}
```

### Complete Structlog + ASGI Correlation Setup
```python
# Source: https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e
import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

def configure_logging(environment: str = "production"):
    """Configure structlog for JSON logging in production."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if environment == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

app = FastAPI()

# Add correlation ID middleware
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Request-ID",
    generator=lambda: str(uuid.uuid4())
)

configure_logging(environment=os.getenv("ENVIRONMENT", "production"))
```

### FastAPI JWT Authentication Dependency
```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

SECRET_KEY = "your-secret-key-from-env"  # Load from environment
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(BaseModel):
    username: str | None = None

async def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Extract and validate user_id from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    return user_id

# Protected endpoint example
@app.get("/users/me")
async def read_users_me(user_id: Annotated[str, Depends(get_current_user_id)]):
    return {"user_id": user_id}
```

### Docker Compose with Secrets
```yaml
# Source: https://docs.docker.com/compose/how-tos/use-secrets/
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    secrets:
      - db_password
      - mailgun_api_key
    environment:
      - DATABASE_PASSWORD_FILE=/run/secrets/db_password
      - MAILGUN_API_KEY_FILE=/run/secrets/mailgun_api_key

secrets:
  db_password:
    file: ./secrets/db_password.txt
  mailgun_api_key:
    file: ./secrets/mailgun_api_key.txt
```

### Better Auth Backend Validation (TypeScript)
```typescript
// Source: https://www.better-auth.com/docs/concepts/api
import { auth } from "./auth-config";
import { headers } from "next/headers";

// In API route or Server Action
export async function validateSession() {
  const session = await auth.api.getSession({
    headers: await headers()
  });

  if (!session) {
    throw new Error("Unauthorized");
  }

  return session.user.id;  // Extract user_id for backend calls
}
```

### Mailgun Email Sending with FastAPI-Mail
```python
# Source: https://pypi.org/project/fastapi-mail/
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAILGUN_SMTP_LOGIN"),
    MAIL_PASSWORD=os.getenv("MAILGUN_SMTP_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.mailgun.org",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fm = FastMail(conf)

async def send_verification_email(email: str, verification_url: str):
    """Send email verification message."""
    message = MessageSchema(
        subject="Verify your IRONMIND account",
        recipients=[email],
        body=f"Click to verify: {verification_url}",
        subtype=MessageType.html
    )

    await fm.send_message(message)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NextAuth.js | Better Auth | 2025-2026 | Better Auth is TypeScript-first, more flexible, actively maintained |
| passlib | pwdlib | 2024-2025 | FastAPI officially recommends pwdlib, uses Argon2 by default |
| python-jose | PyJWT | 2024-2025 | PyJWT is simpler, officially recommended in FastAPI docs |
| bcrypt | Argon2 | 2023+ | Argon2 is memory-hard, more GPU-attack resistant |
| Python logging | structlog | Ongoing | structlog provides context variables for async, easier JSON config |
| Docker Swarm | Docker Compose (dev) / K8s (prod) | 2022+ | Swarm development slowed, Compose for dev and K8s for prod is standard |
| .env in root | Docker secrets | 2020+ | Secrets mounted as files are more secure than environment variables |

**Deprecated/outdated:**
- **bcrypt for password hashing**: Argon2 is now recommended (pwdlib default)
- **python-jose**: PyJWT is officially recommended by FastAPI
- **OAuth2PasswordRequestForm**: Still works but HTTPBearer is cleaner for token-only APIs
- **Docker Swarm for production**: Use Kubernetes or managed container services

## Open Questions

Things that couldn't be fully resolved:

1. **Better Auth + FastAPI Backend Integration**
   - What we know: Better Auth provides session validation via `auth.api.getSession()` with headers
   - What's unclear: How to integrate Better Auth JWT validation directly in FastAPI (Better Auth is Node.js/TypeScript)
   - Recommendation: Frontend (Next.js) handles Better Auth sessions, extracts token/user_id, passes to FastAPI via Authorization header. FastAPI validates with shared secret or public key from `/api/auth/jwks` endpoint.

2. **Cookie Caching vs Database Sessions Performance**
   - What we know: Better Auth supports cookie caching to reduce DB queries
   - What's unclear: Exact performance impact and when to enable (5-day deadline constraint)
   - Recommendation: Start with default database sessions (simpler), enable cookie caching if performance profiling shows session validation is a bottleneck.

3. **Mailgun SMTP vs API for Email Sending**
   - What we know: Mailgun supports both SMTP and HTTP API, fastapi-mail uses SMTP
   - What's unclear: Which approach is more reliable for verification/password reset (< 1min delivery SLA)
   - Recommendation: Use SMTP with fastapi-mail initially (simpler integration), monitor delivery times, switch to HTTP API if SMTP is slow.

4. **Hetzner VPS Resource Requirements**
   - What we know: Docker Compose can run frontend, backend, docling-serve, FalkorDB
   - What's unclear: Minimum VPS specs (CPU/RAM) for acceptable performance with all services
   - Recommendation: Start with Hetzner CPX31 (4 vCPU, 8GB RAM) or higher; monitor resource usage, scale up if needed. Docling may be memory-intensive.

5. **Structured Logging Volume in Development**
   - What we know: Structlog can output pretty console logs (dev) or JSON (prod)
   - What's unclear: Should development use JSON logs or human-readable format
   - Recommendation: Use `structlog.dev.ConsoleRenderer()` in development for readability, JSON in production only.

## Sources

### Primary (HIGH confidence)
- [FastAPI OAuth2 JWT Tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) - Official JWT validation docs
- [Better Auth Email/Password Docs](https://www.better-auth.com/docs/authentication/email-password) - Official authentication setup
- [Better Auth API Docs](https://www.better-auth.com/docs/concepts/api) - Backend session validation
- [Docker Compose Secrets](https://docs.docker.com/compose/how-tos/use-secrets/) - Official secrets management
- [Docker Compose Networking](https://docs.docker.com/compose/how-tos/networking/) - Service communication patterns
- [asgi-correlation-id PyPI](https://pypi.org/project/asgi-correlation-id/) - Correlation ID middleware
- [fastapi-mail PyPI](https://pypi.org/project/fastapi-mail/) - Email sending library
- [FalkorDB Docker Docs](https://docs.falkordb.com/operations/docker.html) - Docker Compose configuration

### Secondary (MEDIUM confidence)
- [Structlog FastAPI Gist](https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e) - Production logging setup
- [FastAPI Health Checks](https://www.index.dev/blog/how-to-implement-health-check-in-python) - Liveness/readiness patterns
- [Mailgun Password Reset Tutorial](https://www.mailgun.com/blog/dev-life/how-to-build-transactional-password-reset-email-workflows/) - Email workflow implementation
- [Better Auth vs NextAuth](https://betterstack.com/community/guides/scaling-nodejs/better-auth-vs-nextauth-authjs-vs-autho/) - Library comparison
- [FastAPI Security Pitfalls](https://medium.com/@ThinkingLoop/fastapi-security-pitfalls-that-almost-leaked-my-user-data-c9903bc13fd7) - Common mistakes
- [Docker Compose Networking Mysteries](https://www.netdata.cloud/academy/docker-compose-networking-mysteries/) - Service communication pitfalls
- [Hetzner FastAPI Deployment](https://turbocloud.dev/book/deploy-fastapi/) - VPS deployment guide
- [FastAPI Docker Best Practices](https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/) - Production Dockerfile patterns

### Tertiary (LOW confidence)
- [Better Auth with Next.js Medium](https://medium.com/@amitupadhyay878/better-auth-with-next-js-a-complete-guide-for-modern-authentication-06eec09d6a64) - Tutorial, needs verification
- [Docker Compose Common Mistakes](https://javanexus.com/blog/common-docker-compose-mistakes) - Blog post, cross-verify recommended

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified from official docs, PyPI, and authoritative sources
- Architecture: MEDIUM-HIGH - Patterns verified from official docs and production examples, Better Auth + FastAPI integration needs validation
- Pitfalls: MEDIUM - Sourced from blog posts and community discussions, cross-referenced where possible

**Research date:** 2026-01-27
**Valid until:** 2026-02-27 (30 days - stable technologies with slow-moving best practices)

**Notes:**
- Better Auth is Node.js/TypeScript focused; Python integration requires custom JWT validation
- Mailgun SMTP configuration verified but delivery performance untested
- Hetzner VPS resource requirements should be validated during deployment
- asgi-correlation-id + structlog is well-documented but may have edge cases in hybrid sync/async code
