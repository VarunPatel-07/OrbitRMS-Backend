# Security Policy for OrbitRMS-Backend

## Reporting Security Vulnerabilities

**Do not open public GitHub issues for security vulnerabilities.**

If you discover a security vulnerability, please email:

- **Primary**: contact.varunpatel.dev@gmail.com
- **Subject line**: "SECURITY: [Brief description]"

Please include:

1. Description of the vulnerability
2. Affected component/endpoint
3. Steps to reproduce (if applicable)
4. Potential impact
5. Suggested fix (if you have one)

We will respond within 48 hours and work with you on a fix and responsible disclosure timeline.

## Security Architecture

### Authentication & Session Management

**JWT Implementation:**

- Algorithm: HS256 (configurable via `JWT_ALGORITHM` in EnvConfig)
- Tokens include `user_id` and `session_id` claims
- Expiration: Set via JWT standard `exp` claim
- Revocation: Linked session records can be invalidated independently

**Session Storage:**

- Sessions stored in database (Sessions table)
- Each login creates new session record
- Sessions are checked on every authenticated request
- Supports per-session invalidation (logout without global token revocation)

**Validation Flow:**

```
Request → UserAuthenticatorMiddleware
    ↓
1. Extract token from Authorization header
2. Verify JWT signature with JWT_SECRET_KEY
3. Check token expiration
4. Load session from database
5. Verify user.account_status == True
6. Verify organization.status == True
7. Inject user object into route handler
```

**Best Practices:**

- Never share `JWT_SECRET_KEY` or session secrets
- Rotate secrets immediately if compromised
- Use HTTPS for all token transmission
- Implement token rotation for long-lived sessions

### Password Security

**Hashing:**

- Algorithm: bcrypt with salt (via `bcrypt.hashpw()`)
- Cost factor: Default bcrypt settings
- Storage: Only hashed passwords in database (password field)

**Requirements (enforce in application):**

- Minimum length: Validate in Pydantic models
- Complexity: Optional (no current requirement)
- Expiration: Implement password reset workflows

**Password Reset:**

- Use time-limited tokens (implement token expiration check)
- Email verification required
- Old password validation for security
- One-time use tokens

**Never:**

- Log passwords or password hashes
- Compare passwords in plaintext
- Store passwords in plaintext
- Transmit passwords over unencrypted connections

### Encryption

**Multi-layer Encryption:**

- `ENCRYPTION_KEY`: Main encryption key for sensitive data
- `SUPER_SECURE_HASH_PASSWORD`: Additional hash layer for extra security

**Encrypted Data:**

- Social media tokens (access_token, refresh_token in SocialMediaAccount model)
- User session secrets
- API keys (potentially)

**Implementation Pattern:**

```python
from cryptography.fernet import Fernet

# Load key from EnvConfig.ENCRYPTION_KEY
cipher = Fernet(EnvConfig.ENCRYPTION_KEY)

# Encrypt before storage
encrypted_token = cipher.encrypt(token.encode())

# Decrypt when needed
decrypted_token = cipher.decrypt(encrypted_token).decode()
```

**Never:**

- Hardcode encryption keys
- Log encrypted or decrypted sensitive data
- Use weak encryption algorithms

### Data Protection

**Organization Isolation:**

- Every query must filter by `organization_id`
- User can only access data within their organization
- No cross-organization data leakage

**Sensitive Data Fields:**

- Passwords: Always hashed with bcrypt
- Tokens: Encrypted with Fernet before storage
- Email addresses: Logged only in error contexts (sanitized)
- Personal info: PII access controlled per organization

**Data Retention:**

- Implement retention policies for logs
- Delete unused sessions regularly
- Archive old records per compliance needs

## API Security

### Rate Limiting

**Configuration:**

- Environment variable: `API_RATE_LIMITING` (e.g., "100/minute")
- Middleware: `slowapi` via `@limiter.limit()` decorator
- Per-endpoint configuration supported

**Best Practices:**

- Apply to all public endpoints
- Stricter limits for authentication endpoints
- Consider user-based vs. IP-based limiting
- Monitor rate limit violations

**Example:**

```python
@router.post("/sign-in")
@limiter.limit("5/minute")  # Stricter for auth
async def sign_in(request: Request, credentials: LoginRequest):
    pass
```

### Input Validation

**Pydantic Models:**

- All request bodies validated with Pydantic
- Type checking, format validation, length constraints
- Automatic sanitization of invalid inputs

**SQL Injection Prevention:**

- Use SQLAlchemy ORM exclusively (no raw SQL queries)
- Parameterized queries built automatically
- Never interpolate user input into SQL

**XSS Prevention:**

- Validate input types via Pydantic
- Sanitize HTML in rich text fields if needed
- Use Content Security Policy headers (configure in CORS middleware)

### CORS Security

**Configuration:**

- Managed via `CustomCorsMiddleWare` in middleware/
- Whitelist trusted origins (use `FRONTEND_URL` from EnvConfig)
- Methods: GET, POST, PUT, DELETE (as needed)
- Credentials: Handle carefully with origin whitelist

**Best Practices:**

- Never use `allow_origins=["*"]` with credentials
- Whitelist specific domains instead of wildcards
- Set appropriate `allow_headers` and `expose_headers`

### API Key Security (Client Inquiries)

**Implementation:**

- API keys stored in database (ApiKey model)
- Associated with organization
- Used for public client inquiry submissions
- Validated before processing

**Best Practices:**

- Generate cryptographically secure keys
- Support key rotation
- Support key expiration/revocation
- Log API key usage (sanitized)
- Hash keys in database (store hash, not plaintext)

## Dependency Management

### Requirements.txt Maintenance

**Current Dependencies:**

- FastAPI 0.115.6 (web framework)
- SQLAlchemy 2.0.36 (ORM)
- PyJWT 2.10.1 (authentication)
- bcrypt 4.2.1 (password hashing)
- cryptography 44.0.0 (encryption)
- python-dotenv 1.0.1 (env vars)
- slowapi 0.1.9 (rate limiting)
- openai 2.6.1 (AI integration)
- cloudinary 1.42.2 (image storage)

**Update Process:**

1. Review security advisories monthly
2. Update dependencies: `pip install --upgrade package`
3. Run tests: `pytest`
4. Check for breaking changes
5. Update requirements.txt: `pip freeze > requirements.txt`
6. Commit with security update note

**Critical Vulnerabilities:**

- Address immediately
- Update within 24 hours if production impact
- Test thoroughly before deploying

## External Service Integration

### OpenAI Integration

**Token Security:**

- Store `OPENAI_API_KEY` in environment only
- Never log API keys
- Rotate keys regularly via OpenAI dashboard
- Review usage patterns for unauthorized access

**Usage Limits:**

- Implement rate limiting on `/orbit-ai/conversation`
- Consider token usage billing/limits
- Validate user input before sending to OpenAI

### Cloudinary Integration

**Credentials:**

- `CLOUDINARY_CLOUD_NAME`: Public
- `CLOUDINARY_API_KEY`: Keep private
- `CLOUDINARY_API_SECRET`: Keep private (never expose)

**Upload Security:**

- Validate file types before upload
- Set size limits
- Use Cloudinary's moderation features
- Implement virus scanning if needed

### Social Media OAuth

**Token Storage:**

- Access tokens encrypted with `ENCRYPTION_KEY`
- Refresh tokens encrypted with `ENCRYPTION_KEY`
- Store in SocialMediaAccount model
- Never log tokens

**OAuth Flow:**

- Use state parameter to prevent CSRF
- Validate state parameter on callback
- Use HTTPS redirect URIs
- Implement token refresh logic

## Database Security

### Connection Security

**Connection String:**

- Stored in `DATABASE_CONNECTION_STRING` environment variable
- Format: `mysql+aiomysql://user:password@host:port/database`
- Use SSL/TLS for remote connections: `?ssl=true`

**Connection Pooling:**

- SQLAlchemy manages connection pool
- Set pool size appropriate for load
- Implement connection timeouts

### Query Security

**Best Practices:**

- Use ORM queries exclusively (SQLAlchemy)
- Never use f-strings or string formatting for SQL
- Validate and type-check all parameters
- Use parameterized queries (automatic with ORM)

**SQL Injection Protection:**

```python
# ✅ SAFE: Uses ORM parameterization
user = db.query(User).filter(User.email == email).first()

# ❌ UNSAFE: String interpolation
user = db.query(User).filter(f"email = '{email}'").first()
```

### Backup & Recovery

**Best Practices:**

- Automated daily backups
- Backup encryption
- Test backup restoration regularly
- Off-site backup storage
- Backup access control

## Environment Configuration

### Secret Management

**Never commit secrets:**

```bash
# ✅ Good: Environment variables
OPENAI_API_KEY=sk-... (in .env, not in git)

# ❌ Bad: Hardcoded
OPENAI_API_KEY = "sk-..." (in source code)
```

**Access via EnvConfig:**

```python
from config.EnvConfig import EnvConfig

# Access safely
api_key = EnvConfig.OPENAI_API_KEY
```

**Production Deployment:**

- Use secrets management service (AWS Secrets Manager, etc.)
- Set environment variables on deployment platform
- Never use .env files in production
- Rotate secrets regularly

### Configuration by Environment

**Development (.env):**

- Local database credentials
- Test API keys
- Debug logging enabled

**Staging (.env.staging):**

- Staging database
- Production-like secrets
- Production rate limiting
- Error monitoring enabled

**Production (.env.production):**

- Production database (managed service)
- Production secrets (from secrets manager)
- Strict rate limiting
- Error tracking/alerting
- CORS restricted to frontend domain

## Logging & Monitoring

### Safe Logging Practices

**What to log:**

- Request/response metadata (timestamps, endpoints, status codes)
- Error stack traces (without sensitive data)
- Authentication events (user_id, success/failure, timestamp)
- Rate limit violations
- Admin actions

**Never log:**

- Passwords or password hashes
- API keys or tokens
- Email addresses (except in security events)
- Personal information (SSN, credit cards, etc.)
- SQL queries with user data

**Implementation:**

```python
# ✅ Safe
logger.info(f"User {user_id} logged in from {ip_address}")

# ❌ Unsafe
logger.info(f"User login: email={email}, password={password}")
```

### Error Monitoring

- Integrate with Sentry or similar (see monitoring.py)
- Alert on critical errors
- Review error logs regularly
- Investigate unusual patterns
- Sanitize error messages in responses

## Maintenance & Patching

### Maintenance Mode Security

**Purpose:**

- Perform upgrades safely
- Deploy new versions
- Recover from incidents

**Implementation:**

- `MaintenanceMode` model controls global status
- `MaintenanceModeScheduler` manages scheduled windows
- All requests blocked during maintenance
- Custom maintenance message shown
- Audit log of maintenance activities

**Best Practices:**

- Plan maintenance windows
- Test changes before deployment
- Have rollback plan
- Monitor systems during maintenance
- Communicate with users

## Incident Response

### Security Incident Procedure

1. **Identify**: Detect security issue or breach
2. **Contain**: Limit scope (disable account, revoke keys, etc.)
3. **Assess**: Determine impact and affected systems
4. **Notify**: Alert relevant stakeholders
5. **Remediate**: Fix underlying vulnerability
6. **Document**: Log incident details for review
7. **Follow-up**: Implement preventive measures

### Breach Notification

- Notify affected users within 24 hours
- Provide guidance on password changes
- Monitor for unauthorized access
- Comply with data protection regulations

## Compliance & Standards

**Best Practices Followed:**

- OWASP Top 10 mitigations
- CWE/SANS Top 25 addressed
- Industry security standards
- GDPR considerations for data handling

**Audit Trail:**

- Admin actions logged
- Login/logout events tracked
- Permission changes recorded
- API key generation/revocation logged

## Security Checklist for Contributors

- [ ] No secrets in code/commits
- [ ] Environment variables used for all sensitive data
- [ ] Input validation via Pydantic models
- [ ] Organization isolation checks in queries
- [ ] Rate limiting on appropriate endpoints
- [ ] Passwords hashed with bcrypt (never plaintext)
- [ ] Tokens validated via middleware
- [ ] SQL injection protected (ORM only)
- [ ] HTTPS enforced in production
- [ ] Error messages sanitized (no sensitive data)
- [ ] Dependencies up-to-date with no high vulnerabilities
- [ ] Logging doesn't expose sensitive data

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/advanced/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/faq/security.html)

## Contact

Security concerns: **contact.varunpatel.dev@gmail.com**

---

**Last Updated:** January 2026
**Maintained By:** OrbitRMS Security Team
