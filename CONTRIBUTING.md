# Contributing to OrbitRMS-Backend

Thank you for your interest in contributing to OrbitRMS! This document provides guidelines and workflows for contributing to the backend system.

## Getting Started

### Prerequisites

- Python 3.8+
- MySQL database
- Redis/Valkey
- Git

### Development Setup

```bash
# Clone repository
git clone https://github.com/VarunPatel-07/OrbitRMS-Backend.git
cd OrbitRMS-Backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env .env.local

# Start development environment
./local-run.sh
```

## Project Structure Overview

**Key directories:**

- `routes/` - API endpoint handlers organized by feature
- `models/sql/` - SQLAlchemy database models (Models.py)
- `models/pydantic/` - Request/response validation schemas
- `middleware/` - Authentication, rate limiting, CORS
- `jobs/schedulers/` - Background workers (BulkCommentFeeder, BulkLikeFeeder)
- `database/` - Connection management (Database.py, CacheDatabase.py)
- `config/` - Environment configuration (EnvConfig.py)
- `migrations/` - Alembic database migrations by environment

## Code Conventions

### File Organization

- **Routes**: Group related endpoints in feature folders (`/routes/organizations/`, `/routes/auth/`)
- **Models**: Keep SQL models in `models/sql/Models.py`, validation schemas in `models/pydantic/`
- **Utilities**: Helper functions go in `utils/` with clear subfolders (helper/, logging/, responseMessages/)

### Naming Conventions

```python
# Routes: PascalCase for router objects
OrbitAiRoute = APIRouter(prefix="/app/v1/orbit-ai")

# Functions: snake_case
async def handle_user_authentication(request):

# Classes: PascalCase
class UserAuthenticatorMiddleware:

# Constants: UPPER_SNAKE_CASE
API_RATE_LIMITING = "100/minute"
```

### Code Formatting

The project uses **Black** (100 char line length) and **isort**:

```bash
# Format all files
black .
isort .

# Format specific file
black routes/auth/authentication.py
```

### Import Ordering

isort is configured with Black profile. Imports are auto-sorted:

```python
# Standard library
import os, json

# Third-party
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Local
from config.EnvConfig import EnvConfig
from models.sql.Models import User
```

## Making Changes

### Multi-Tenant Architecture Patterns

**Always consider organization isolation:**

```python
# ✅ CORRECT: Filter by organization
employees = db.query(User).filter(
    User.organization_id == user['organization_id']
).all()

# ❌ WRONG: Missing organization filter
employees = db.query(User).all()
```

### Database Changes

1. **Modify schema**: Edit relevant model in `models/sql/Models.py`
2. **Create migration**:
   ```bash
   cd migrations/development
   alembic revision --autogenerate -m "Add new_field to users table"
   ```
3. **Review migration**: Check generated file for correctness
4. **Apply locally**: `alembic upgrade head`
5. **Document**: Update DOCUMENTATION.md Database Models section

### Adding New Routes

1. Create file in appropriate `routes/` subfolder
2. Use consistent structure:

   ```python
   from fastapi import APIRouter, Depends, HTTPException, status
   from middleware.UserAuthenticator import UserAuthenticatorMiddleware
   from middleware.RateLimiting import limiter

   router = APIRouter(prefix="/app/v1/feature", tags=["Feature"])

   @router.get("/")
   @limiter.limit("100/minute")
   async def get_feature(request: Request, user: dict = Depends(UserAuthenticatorMiddleware)):
       # Implementation
       pass
   ```

3. Register router in `index.py`: `app.include_router(router)`
4. Add endpoint to DOCUMENTATION.md API Endpoints section

### Background Tasks

For async processing (likes, comments, bulk operations):

- Use Redis queues: `CacheDatabase` class in `database/CacheDatabase.py`
- Implement worker in `jobs/schedulers/` following BulkLikeFeeder pattern
- Register scheduler in `index.py` with APScheduler

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=.

# Specific test file
pytest test/test_auth.py

# Verbose output
pytest -v
```

### Writing Tests

- Create test files in `test/` directory matching route name: `test_auth.py`, `test_organizations.py`
- Use FastAPI TestClient:

  ```python
  from fastapi.testclient import TestClient
  from index import app

  client = TestClient(app)

  def test_user_login():
      response = client.post("/app/v1/auth/sign-in", json={...})
      assert response.status_code == 200
  ```

- Test both success and error cases
- Mock database queries when appropriate

## Security Considerations

### Never commit secrets

- All API keys, passwords, tokens go in `.env`
- Use `EnvConfig.VARIABLE_NAME` to access secrets
- Environment variables are loaded via `python-dotenv`

### Password & Token Handling

```python
# ✅ Hash passwords with bcrypt
from bcrypt import hashpw, gensalt
hashed = hashpw(password.encode(), gensalt())

# ✅ Validate tokens via UserAuthenticatorMiddleware
user = Depends(UserAuthenticatorMiddleware)

# ❌ Never store plaintext passwords
# ❌ Never log tokens or sensitive data
```

### Input Validation

Use Pydantic models for all request bodies:

```python
from models.pydantic.UserModels import UserLoginRequest

@router.post("/sign-in")
async def sign_in(request: UserLoginRequest):
    # Pydantic automatically validates email format, password length, etc.
    pass
```

### Rate Limiting

Apply to public/expensive endpoints:

```python
@router.post("/submit-inquiry")
@limiter.limit(EnvConfig.API_RATE_LIMITING)
async def submit_inquiry(request: Request, ...):
    pass
```

## Pull Request Workflow

1. **Create feature branch**: `git checkout -b feature/your-feature-name`
2. **Make focused changes**: One feature per PR
3. **Format code**: Run `black . && isort .` before committing
4. **Test locally**: Ensure `./local-run.sh` starts cleanly
5. **Update documentation**: Add/update DOCUMENTATION.md for significant changes
6. **Commit messages**: Use clear, descriptive messages
   ```
   feat: add email notification for leave approvals
   fix: correct organization filter in employee query
   docs: update API endpoint documentation
   ```
7. **Push and create PR**: Include description of changes and any breaking changes

## Common Development Tasks

### Add a new API endpoint

1. Add Pydantic model in `models/pydantic/`
2. Add database model if needed in `models/sql/Models.py`
3. Create route file in `routes/`
4. Import and register in `index.py`
5. Document in DOCUMENTATION.md

### Add new environment variable

1. Add to `.env` file with description
2. Add to `config/EnvConfig.py` as class variable
3. Load via `os.getenv("VAR_NAME")`
4. Document in DOCUMENTATION.md Configuration section

### Fix a database issue

1. Identify model in `models/sql/Models.py`
2. Create migration: `alembic revision --autogenerate -m "description"`
3. Test: `alembic upgrade head` then `alembic downgrade -1` then upgrade again
4. Document changes

## Questions or Need Help?

- Review [DOCUMENTATION.md](DOCUMENTATION.md) for architecture details
- Check existing implementations in `routes/` for patterns
- See [SECURITY.md](SECURITY.md) for security guidelines
- Contact: [contact.varunpatel.dev@gmail.com](mailto:contact.varunpatel.dev@gmail.com)

## License

By contributing, you agree that your contributions will be licensed under the MIT License. The OrbitRMS name and branding are trademarks and are not included under the MIT License (see [TRADEMARK.md](TRADEMARK.md)).
