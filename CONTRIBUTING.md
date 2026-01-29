# Contributing to IRONMIND

Thank you for your interest in contributing to IRONMIND!

## Development Setup

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- Git

### Local Development

1. Fork and clone the repository
2. Copy `.env.example` to `.env` and add your API keys
3. Start supporting services:
   ```bash
   docker-compose up falkordb docling -d
   ```
4. Start backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
5. Start frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints for all functions
- Format with Black: `black app/`
- Lint with Ruff: `ruff check app/`
- Use Pydantic for data validation

### TypeScript (Frontend)

- Use TypeScript strict mode
- Format with Prettier
- Lint with ESLint: `npm run lint`
- Use functional components with hooks

## Testing

### Backend

```bash
cd backend
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run test
```

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes with clear commit messages
3. Ensure tests pass
4. Update documentation if needed
5. Submit PR with description of changes

## Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Adding tests

Example: `feat: add document deletion endpoint`

## Project Structure

```
ironmind/
├── frontend/       # Next.js application
├── backend/        # FastAPI application
├── infra/          # Deployment configuration
├── docs/           # Documentation
└── .planning/      # Project planning (not for PRs)
```

## Questions?

Open an issue for questions or discussions about contributing.
