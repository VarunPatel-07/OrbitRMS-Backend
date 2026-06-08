# OrbitRMS Backend - Complete Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Database Models](#database-models)
6. [API Endpoints](#api-endpoints)
7. [Authentication & Authorization](#authentication--authorization)
8. [Background Tasks & Schedulers](#background-tasks--schedulers)
9. [Configuration](#configuration)
10. [Development Setup](#development-setup)
11. [Deployment](#deployment)
12. [Key Features](#key-features)
13. [Security Features](#security-features)
14. [Error Handling](#error-handling)
15. [Testing](#testing)

---

## Project Overview

**OrbitRMS (Orbit Resource Management System)** is a comprehensive backend system designed to manage organizations, employees, attendance, leaves, social media integration, client inquiries, and AI-powered features. The system provides a multi-tenant architecture where each organization operates independently with its own employees, settings, and configurations.

### Core Purpose

The backend serves as the central API layer for:

- **Organization Management**: Multi-tenant organization setup and configuration
- **Employee Management**: Complete employee lifecycle management
- **Attendance & Leaves**: Tracking attendance and managing leave requests
- **Social Media Integration**: Managing social media accounts and posts
- **Client Inquiries**: Handling client inquiry forms and submissions
- **AI Integration**: OpenAI-powered conversational AI features
- **Feed System**: Internal organization feed with likes and comments
- **Admin Panel**: Super admin functionality for system-wide management

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   FastAPI App   │
│   (index.py)    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ MySQL │ │ Redis │
│  DB   │ │ Cache │
└───────┘ └───────┘
```

### Application Flow

1. **Request Flow**: Client → FastAPI → Middleware → Route Handler → Database → Response
2. **Authentication**: JWT-based authentication with session management
3. **Background Processing**: Async tasks for likes, comments, and scheduled jobs
4. **Caching**: Redis for session management and temporary data storage

### Design Patterns

- **Repository Pattern**: Database models separated from business logic
- **Dependency Injection**: FastAPI's dependency system for database sessions and authentication
- **Middleware Pattern**: Authentication and rate limiting middleware
- **Background Task Pattern**: Async workers for non-blocking operations

---

## Technology Stack

### Core Framework

- **FastAPI** (0.115.6): Modern, fast web framework for building APIs
- **Python 3.8+**: Programming language

### Database & ORM

- **SQLAlchemy** (2.0.36): SQL toolkit and ORM
- **MySQL**: Primary relational database (via PyMySQL/aiomysql)
- **Alembic** (1.14.0): Database migration tool
- **Redis/Valkey** (5.2.1): Caching and queue management

### Authentication & Security

- **PyJWT** (2.10.1): JSON Web Token implementation
- **bcrypt** (4.2.1): Password hashing
- **cryptography** (44.0.0): Additional cryptographic functions
- **slowapi** (0.1.9): Rate limiting

### Data Validation

- **Pydantic** (2.10.4): Data validation using Python type annotations

### Background Tasks & Scheduling

- **APScheduler** (3.11.0): Advanced Python Scheduler
- **asyncio**: Asynchronous task processing

### External Services Integration

- **OpenAI** (2.6.1): AI conversation API
- **Cloudinary** (1.42.2): Image and media storage
- **Facebook SDK** (3.1.0): Facebook API integration
- **Authlib** (1.6.1): OAuth integration for social media

### Email Services

- **fastapi-mail** (1.4.2): Email sending functionality
- **aiosmtplib** (3.0.2): Async SMTP client

### Utilities

- **python-dotenv** (1.0.1): Environment variable management
- **arrow** (1.2.3): Date and time manipulation
- **beautifulsoup4** (4.12.3): HTML parsing
- **requests** (2.32.3): HTTP library
- **httpx** (0.28.1): Async HTTP client

### Development Tools

- **black** (25.1.0): Code formatter
- **isort** (6.0.0): Import sorter
- **uvicorn** (0.38.0): ASGI server

---

## Project Structure

```
ObitRMS-Backend/
├── BackgroundDataHandler/          # Initial data seeding
│   ├── data/                        # Default data JSON files
│   │   ├── defaultClientFormFields.json
│   │   ├── defaultDepartmentData.json
│   │   ├── defaultDesignationsData.json
│   │   ├── defaultProjectStatuses.json
│   │   └── defaultRolePermissionData.json
│   ├── DataSeederHelper.py          # Helper functions for seeding
│   └── initialDataSeeder.py         # Main seeder functions
│
├── BackgroundTasks/                 # Background task modules
│   ├── LeavesModule/                # Leave-related background tasks
│   └── SocialMediaModule/           # Social media background tasks
│
├── Config/                          # Configuration management
│   └── EnvConfig.py                 # Environment variable configuration
│
├── Constant/                        # Application constants
│   ├── constant.py                  # General constants
│   └── countryLocaleMapping.py      # Country locale mappings
│
├── Database/                        # Database configuration
│   ├── Base.py                      # Base model class
│   ├── CacheDatabase.py             # Redis/Valkey connection
│   └── Database.py                   # MySQL connection and session management
│
├── Email/                           # Email templates and utilities
│   ├── Html/                        # HTML email templates
│   │   ├── admin-access-code.html
│   │   ├── create-password.html
│   │   ├── email-verification.html
│   │   ├── new-client-inquiry-mail.html
│   │   ├── reset-password.html
│   │   ├── reset-password-instruction.html
│   │   └── welcome-new-user-mail.html
│   └── HtmlEmailBody.py             # Email body generators
│
├── ErrorMessages/                   # Error message definitions
│   └── AuthErrorMessage.py          # Authentication error messages
│
├── Helper/                          # Utility functions
│   ├── createModelInstance.py       # Model instance creation helpers
│   ├── emailSender.py               # Email sending utilities
│   ├── formateDateOnTheBaseOfTheCountry.py  # Date formatting
│   ├── helper.py                    # General helper functions
│   ├── jwtHelper.py                 # JWT token utilities
│   └── organizationHelper.py        # Organization-related helpers
│
├── Middleware/                      # Custom middleware
│   ├── UserAuthenticator.py         # User authentication middleware
│   └── verifyToken.py                # Token verification utilities
│
├── migrations/                      # Database migrations
│   ├── development/                 # Development environment migrations
│   │   └── alembic/
│   └── staging/                     # Staging environment migrations
│       └── alembic/
│
├── PydanticModels/                  # Request/Response validation models
│   ├── Admin/                       # Admin-related models
│   ├── authentication/              # Authentication models
│   ├── ConfigModule/                # Configuration models
│   ├── HelperPydanticModel.py       # Shared helper models
│   ├── Organizations/                # Organization-related models
│   ├── OrganizationSettings/        # Organization settings models
│   ├── SocialMediaModule/           # Social media models
│   └── UserModels.py                # User-related models
│
├── routes/                          # API route handlers
│   ├── Admin/                       # Admin panel routes
│   │   ├── Auth/                    # Admin authentication
│   │   ├── MaintenanceModeManager/  # Maintenance mode management
│   │   └── Organization/            # Admin organization management
│   ├── ApiManager/                  # API key management
│   ├── auth/                        # User authentication routes
│   ├── ClientInquires/              # Client inquiry routes
│   ├── ConfigModule/                # Configuration routes
│   ├── CountryInfo/                 # Country information routes
│   ├── ImageUploadation/            # Image upload routes
│   ├── OrbitAi/                     # AI conversation routes
│   ├── Organizations/               # Organization routes
│   ├── OrganizationSettings/        # Organization settings routes
│   └── SocialMediaModule/           # Social media routes
│
├── Schedulers/                      # Scheduled background jobs
│   ├── BulkCommentFeeder.py         # Comment processing worker
│   ├── BulkLikeFeeder.py            # Like processing worker
│   └── MaintenanceModeScheduler.py  # Maintenance mode scheduler
│
├── SqlModels/                       # SQLAlchemy database models
│   ├── HelperModel/                 # Helper model utilities
│   │   ├── AdminModelHelperUtils.py
│   │   ├── ConfigModelUtils.py
│   │   ├── OrganizationModelUtils.py
│   │   ├── SocialMediaModule.py
│   │   └── UserModelUtils.py
│   └── Models.py                    # Main database models
│
├── index.py                         # Application entry point
├── RateLimiting.py                  # Rate limiting configuration
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project configuration (Black, isort)
├── docker-compose.yml               # Docker Compose configuration
├── vercel.json                      # Vercel deployment configuration
├── local-run.sh                     # Local development script
├── docker-run.sh                    # Docker run script
└── dev_db_migration.sh              # Database migration script
```

---

## Database Models

### Core Models

#### User Model

The central user model representing employees in the system.

**Key Relationships:**

- `personal_info`: One-to-one with PersonalInfo
- `employee_info`: One-to-one with EmployeeInfo
- `organization`: Many-to-one with Organization
- `applied_leaves`: One-to-many with AttendanceLeavesModule
- `feed_likes`: One-to-many with FeedLikes
- `feed_comments`: One-to-many with FeedComments
- `sessions`: One-to-many with Sessions

**Key Fields:**

- `id`: UUID primary key
- `password`: Hashed password
- `account_status`: Boolean for account activation
- `profile_created`: Boolean flag for profile completion
- `password_created`: Boolean flag for password setup
- `organization_id`: Foreign key to Organization
- `current_address_id` / `permanent_address_id`: Foreign keys to Address

#### Organization Model

Represents a tenant organization in the multi-tenant system.

**Key Relationships:**

- `employees`: One-to-many with User
- `general_info`: One-to-one with OrganizationGeneralInfo
- `organization_settings`: One-to-one with OrganizationSettings
- `config_modules`: One-to-many with ConfigModule
- `client_inquires`: One-to-one with ClientInquires
- `org_updates`: One-to-many with OrganizationUpdates (feed posts)
- `social_media_accounts`: One-to-many with SocialMediaAccount
- `leaves_settings`: One-to-many with LeavesSettings

**Key Fields:**

- `id`: UUID primary key
- `status`: Boolean for organization activation
- `organization_created`: Boolean flag for setup completion

#### PersonalInfo Model

Stores personal information for users.

**Key Fields:**

- `first_name`, `middle_name`, `last_name`, `full_name`
- `profile_picture`, `profile_picture_bg`
- `gender`, `date_of_birth`, `blood_group`
- `about`: Text field for user bio
- `user_id`: Foreign key to User

#### EmployeeInfo Model

Stores employment-related information.

**Key Relationships:**

- `user`: Many-to-one with User
- `reporting_manager`: Many-to-one with User (self-referential)

**Key Fields:**

- `employee_id`: Unique employee identifier
- `department_id`: Foreign key to Department
- `designation_id`: Foreign key to Designations
- `reporting_to_id`: Foreign key to User (manager)
- `joining_date`: Employment start date
- `role_id`: Foreign key to RolesPermission

#### OrganizationUpdates Model

Represents posts in the organization feed.

**Key Relationships:**

- `organization`: Many-to-one with Organization
- `publisher`: Many-to-one with User
- `feed_likes`: One-to-many with FeedLikes
- `feed_comments`: One-to-many with FeedComments

#### FeedLikes Model

Tracks likes on feed posts.

**Key Relationships:**

- `user`: Many-to-one with User
- `organization_update`: Many-to-one with OrganizationUpdates

#### FeedComments Model

Stores comments on feed posts.

**Key Relationships:**

- `user`: Many-to-one with User
- `organization_update`: Many-to-one with OrganizationUpdates

#### AttendanceLeavesModule Model

Manages leave requests and attendance.

**Key Relationships:**

- `user`: Many-to-one with User (applicant)
- `notify_to_users`: Many-to-many with User (notification recipients)

**Key Fields:**

- `leave_type`: Enum for leave types
- `start_date`, `end_date`: Leave period
- `status`: Enum for leave status (pending, approved, rejected)
- `reason`: Text field for leave reason

#### LeaveBalance Model

Tracks available leave balance for users.

**Key Relationships:**

- `user`: Many-to-one with User

**Key Fields:**

- `leave_type`: Type of leave
- `balance`: Available balance
- `total_allotted`: Total allocated leaves

#### SocialMediaAccount Model

Stores connected social media accounts.

**Key Relationships:**

- `organization`: Many-to-one with Organization

**Key Fields:**

- `platform`: Enum (Facebook, Instagram, Twitter, LinkedIn)
- `account_id`: Platform-specific account identifier
- `access_token`: Encrypted access token
- `refresh_token`: Encrypted refresh token
- `is_active`: Boolean for account status

#### SocialMediaPosts Model

Stores social media posts.

**Key Relationships:**

- `organization`: Many-to-one with Organization
- `social_media_account`: Many-to-one with SocialMediaAccount

#### ClientInquires Model

Stores client inquiry submissions.

**Key Relationships:**

- `organization`: Many-to-one with Organization

**Key Fields:**

- `form_data`: JSON field for dynamic form data
- `status`: Enum for inquiry status

#### ConfigModule Models

**Department Model:**

- `department_name`: Name of the department
- `organization_id`: Foreign key to Organization

**Designations Model:**

- `designations_name`: Name of the designation
- `organization_id`: Foreign key to Organization

**ProjectStatus Model:**

- `status_name`: Name of the project status
- `organization_id`: Foreign key to Organization

**RolesPermission Model:**

- `role_name`: Name of the role
- `organization_id`: Foreign key to Organization

**RoleAssociatedPermissionModule Model:**

- Links roles to specific permissions
- `role_id`: Foreign key to RolesPermission
- `permission_id`: Foreign key to PermissionModule

#### MaintenanceMode Model

Controls system-wide maintenance mode.

**Key Fields:**

- `is_active`: Boolean for maintenance status
- `message`: Maintenance message
- `updated_by`: User who updated the status

#### MaintenanceLog Model

Logs maintenance mode changes.

**Key Fields:**

- `started_at`, `ended_at`: Maintenance window
- `status`: Enum (scheduled, active, completed)
- `message`: Maintenance message
- `started_by`, `ended_by`: User identifiers

#### Admin Model

Super admin accounts for system management.

**Key Relationships:**

- `admin_sessions`: One-to-many with OrbitAdminSessions

**Key Fields:**

- `email`: Admin email
- `password`: Hashed password

---

## API Endpoints

### Authentication Routes (`/app/v1/auth`)

#### User Authentication

- `POST /sign-up`: Register a new organization and admin user
- `POST /sign-in`: User login with email and password
- `POST /verify-email`: Verify user email address
- `POST /resend-verification-mail`: Resend verification email
- `POST /forgot-password`: Request password reset
- `POST /reset-password`: Reset password with token
- `POST /create-password`: Create password for new users
- `GET /verify-meta-tag`: Verify organization meta tag

### Organization Routes (`/app/v1/organizations`)

#### Organization Management

- `GET /`: Get organization details
- `PUT /`: Update organization information
- `GET /employees`: Get list of employees
- `POST /employees`: Add new employee
- `PUT /employees/{id}`: Update employee information
- `DELETE /employees/{id}`: Delete employee

### Employee Routes (`/app/v1/employees`)

#### Employee Management

- `GET /`: Get current user's employee profile
- `PUT /`: Update employee profile
- `GET /profile`: Get complete employee profile
- `PUT /profile`: Update complete profile

### Attendance Routes (`/app/v1/attendance`)

#### Attendance & Leaves

- `POST /leaves`: Apply for leave
- `GET /leaves`: Get leave requests
- `PUT /leaves/{id}`: Update leave request
- `DELETE /leaves/{id}`: Delete leave request
- `GET /leave-balance`: Get leave balance
- `GET /attendance`: Get attendance records

### Feed Routes (`/app/v1/feed`)

#### Organization Feed

- `GET /`: Get organization feed posts
- `POST /`: Create new feed post
- `PUT /{id}`: Update feed post
- `DELETE /{id}`: Delete feed post
- `POST /{id}/like`: Like/unlike a post
- `POST /{id}/comment`: Add comment to post
- `GET /{id}/comments`: Get post comments

### Organization Settings Routes (`/app/v1/organization-settings`)

#### Settings Management

- `GET /`: Get organization settings
- `PUT /`: Update organization settings
- `GET /holidays`: Get organization holidays
- `POST /holidays`: Add holiday
- `PUT /holidays/{id}`: Update holiday
- `DELETE /holidays/{id}`: Delete holiday

### Config Module Routes (`/app/v1/config`)

#### Configuration Management

- `GET /departments`: Get departments
- `POST /departments`: Add department
- `PUT /departments/{id}`: Update department
- `DELETE /departments/{id}`: Delete department
- `GET /designations`: Get designations
- `POST /designations`: Add designation
- `PUT /designations/{id}`: Update designation
- `DELETE /designations/{id}`: Delete designation
- `GET /project-statuses`: Get project statuses
- `POST /project-statuses`: Add project status
- `PUT /project-statuses/{id}`: Update project status
- `DELETE /project-statuses/{id}`: Delete project status
- `GET /roles`: Get roles
- `POST /roles`: Add role
- `PUT /roles/{id}`: Update role
- `DELETE /roles/{id}`: Delete role

### Client Inquiries Routes (`/app/v1/client-inquiries`)

#### Inquiry Management

- `POST /submit`: Submit client inquiry (public endpoint)
- `GET /`: Get inquiries (authenticated)
- `GET /{id}`: Get specific inquiry
- `PUT /{id}`: Update inquiry status
- `DELETE /{id}`: Delete inquiry

### Social Media Routes (`/app/v1/social-media`)

#### Social Media Management

- `GET /accounts`: Get connected social media accounts
- `POST /accounts`: Connect new social media account
- `PUT /accounts/{id}`: Update social media account
- `DELETE /accounts/{id}`: Disconnect account
- `GET /posts`: Get social media posts
- `POST /posts`: Create new post
- `PUT /posts/{id}`: Update post
- `DELETE /posts/{id}`: Delete post

#### Social Media Authentication

- `GET /auth/{platform}/authorize`: Initiate OAuth flow
- `GET /auth/{platform}/callback`: OAuth callback handler

### OrbitAI Routes (`/app/v1/orbit-ai`)

#### AI Conversation

- `POST /conversation`: Chat with AI (supports image input)
  - Accepts: text input, images, conversation history
  - Returns: AI-generated responses

### Image Upload Routes (`/app/v1/image-upload`)

#### Media Management

- `POST /`: Upload image to Cloudinary
- `DELETE /`: Delete image from Cloudinary

### Country Info Routes (`/app/v1/country-info`)

#### Country Data

- `GET /countries`: Get list of all countries
- `GET /countries/{code}`: Get specific country details

### API Manager Routes (`/app/v1/api-manager`)

#### API Key Management

- `PUT /client-inquiry/enable-api`: Enable/disable client inquiry API
- `GET /client-inquiry/api-status`: Get API status
- `POST /client-inquiry/generate-key`: Generate new API key
- `GET /client-inquiry/keys`: List API keys

### Admin Routes (`/app/v1/admin`)

#### Admin Authentication

- `POST /auth/sign-in`: Admin login
- `POST /auth/sign-out`: Admin logout

#### Admin Organization Management

- `GET /organizations`: List all organizations
- `GET /organizations/{id}`: Get organization details
- `PUT /organizations/{id}`: Update organization
- `DELETE /organizations/{id}`: Delete organization
- `POST /organizations/{id}/activate`: Activate organization
- `POST /organizations/{id}/deactivate`: Deactivate organization

#### Admin Employee Management

- `GET /organizations/{org_id}/employees`: List employees
- `GET /organizations/{org_id}/employees/{id}`: Get employee details
- `PUT /organizations/{org_id}/employees/{id}`: Update employee
- `DELETE /organizations/{org_id}/employees/{id}`: Delete employee

#### Maintenance Mode

- `GET /maintenance-mode`: Get maintenance mode status
- `PUT /maintenance-mode`: Update maintenance mode
- `GET /maintenance-logs`: Get maintenance logs
- `POST /maintenance-logs`: Create maintenance schedule
- `PUT /maintenance-logs/{id}`: Update maintenance log
- `DELETE /maintenance-logs/{id}`: Delete maintenance log

### Health Check Routes

- `GET /`: Root health check endpoint
- `GET /health`: Health status endpoint

---

## Authentication & Authorization

### Authentication Flow

1. **User Registration**:
   - User signs up with organization details
   - System creates organization and admin user
   - Verification email sent
   - User verifies email and creates password

2. **User Login**:
   - User provides email and password
   - System validates credentials
   - JWT token generated with user_id and session_id
   - Session stored in database
   - Token returned to client

3. **Token Validation**:
   - Client sends token in Authorization header
   - `UserAuthenticatorMiddleware` validates token
   - Checks user account status
   - Checks organization status
   - Verifies session exists
   - Returns user object to route handler

### JWT Token Structure

```json
{
  "user_id": "uuid",
  "session_id": "uuid",
  "exp": timestamp,
  "iat": timestamp
}
```

### Session Management

- Sessions stored in `Sessions` table
- Each login creates new session
- Sessions can be invalidated individually
- Session expiration handled by JWT expiry

### Password Security

- Passwords hashed using bcrypt
- Additional encryption layer for sensitive data
- Password reset tokens with expiration
- Rate limiting on password reset attempts

### Authorization Levels

1. **Public Endpoints**: No authentication required
   - Client inquiry submission
   - Email verification
   - Password reset

2. **User Endpoints**: Requires valid user token
   - All organization-specific routes
   - Employee profile management
   - Feed interactions

3. **Admin Endpoints**: Requires admin token
   - Organization management
   - System-wide settings
   - Maintenance mode control

### Middleware Stack

1. **CORS Middleware**: Handles cross-origin requests
2. **Rate Limiting Middleware**: Prevents API abuse
3. **Session Middleware**: Manages session state
4. **Authentication Middleware**: Validates user tokens
5. **Maintenance Mode Check**: Blocks requests during maintenance

---

## Background Tasks & Schedulers

### Background Workers

#### BulkLikeFeeder

- **Purpose**: Processes like/unlike actions asynchronously
- **Queue**: Redis `likes_queue`
- **Process**:
  1. Pops events from Redis queue
  2. Creates or deletes FeedLikes records
  3. Invalidates related cache entries
  4. Processes continuously in background

#### BulkCommentFeeder

- **Purpose**: Processes comment submissions asynchronously
- **Queue**: Redis `comments_queue`
- **Process**: Similar to BulkLikeFeeder for comments

### Scheduled Jobs

#### MaintenanceModeScheduler

- **Frequency**: Runs every 1 minute
- **Purpose**: Manages scheduled maintenance windows
- **Process**:
  1. Checks for scheduled maintenance logs
  2. Activates maintenance mode when start time reached
  3. Deactivates maintenance mode when end time reached
  4. Updates MaintenanceMode table accordingly

### Task Queue Architecture

```
Client Request → API Endpoint → Redis Queue → Background Worker → Database
```

### Benefits

- **Non-blocking**: API responses not delayed by heavy operations
- **Scalability**: Workers can be scaled independently
- **Reliability**: Failed tasks can be retried
- **Performance**: Improved response times for users

---

## Configuration

### Environment Variables

All configuration is managed through environment variables loaded from `.env` file.

#### Database Configuration

```env
DATABASE_CONNECTION_STRING=mysql+aiomysql://user:password@host:port/database
STAGING_MIGRATION_DB_URL=mysql://...
DEVELOPMENT_MIGRATION_DB_URL=mysql://...
```

#### JWT & Security

```env
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=your-encryption-key
SUPER_SECURE_HASH_PASSWORD=additional-hash-password
API_RATE_LIMITING=100/minute
```

#### Application Config

```env
FRONTEND_URL=https://your-frontend.com
BACKEND_BASE_URL=https://your-backend.com
SESSION_SECRET_KEY=your-session-secret
BACKEND_APP_ENVIRONMENT=PRODUCTION|STAGING|DEVELOPMENT
GEONAME_API_USERNAME=your-geoname-username
```

#### Email Configuration

```env
GOOGLE_APP_PASSWORD=your-app-password
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PORT=465
EMAIL_SERVER_ADDRESS=smtp.gmail.com
```

#### Cloudinary Configuration

```env
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

#### Redis/Valkey Configuration

```env
CACHED_DATABASE_HOST=localhost
CACHED_DATABASE_PORT=6379
CACHED_DATABASE_PASSWORD=your-redis-password
```

#### Social Media Links

```env
INSTAGRAM_LINK=https://instagram.com/your-profile
FACEBOOK_LINK=https://facebook.com/your-profile
LINKEDIN_LINK=https://linkedin.com/your-profile
```

#### Admin Configuration

```env
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin-password
ORBITRMS_OWNER_EMAIL=owner@example.com
ORBIT_CONTACT_EMAIL=contact@example.com
```

#### OpenAI Configuration

```env
OPENAI_API_KEY=your-openai-api-key
```

#### Meta/Facebook API

```env
META_APP_ID=your-app-id
META_APP_SECRET=your-app-secret
META_API_VERSION=v18.0
META_GRAPH_BASE_URL=https://graph.facebook.com
```

#### Twitter API

```env
TWITTER_CONSUMER_KEY=your-consumer-key
TWITTER_CONSUMER_SECRETE=your-consumer-secret
```

#### REST API

```env
REST_API_URL=https://your-rest-api.com
```

### Configuration Class

All environment variables are accessed through `Config.EnvConfig` class, which:

- Loads variables from `.env` file
- Provides type-safe access
- Organizes variables by category
- Handles missing variables gracefully

---

## Development Setup

### Prerequisites

- Python 3.8 or higher
- MySQL database
- Redis/Valkey server
- Git

### Installation Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/VarunPatel-07/OrbitRMS-Backend.git
   cd OrbitRMS-Backend
   ```

2. **Create Virtual Environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   ```bash
   cp .env.example .env  # If example exists
   # Edit .env with your configuration
   ```

5. **Set Up Database**
   - Create MySQL database
   - Update `DATABASE_CONNECTION_STRING` in `.env`
   - Run migrations:
     ```bash
     alembic upgrade head
     ```

6. **Set Up Redis/Valkey**
   - Install Redis/Valkey
   - Update Redis configuration in `.env`
   - Or use Docker:
     ```bash
     docker compose up -d
     ```

7. **Run the Application**

   **Option 1: Using local-run.sh**

   ```bash
   chmod +x local-run.sh
   ./local-run.sh
   ```

   **Option 2: Manual Start**

   ```bash
   uvicorn index:app --reload
   ```

8. **Access the Application**
   - API: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Alternative Docs: `http://localhost:8000/redoc`

### Database Migrations

#### Development Environment

```bash
cd migrations/development
alembic upgrade head
alembic revision --autogenerate -m "description"
alembic upgrade head
```

#### Staging Environment

```bash
cd migrations/staging
alembic upgrade head
```

### Code Formatting

The project uses Black and isort for code formatting:

```bash
# Format code
black .

# Sort imports
isort .
```

### Pre-commit Hooks

If pre-commit is configured:

```bash
pre-commit install
```

---

## Deployment

### Vercel Deployment

The project includes `vercel.json` for Vercel deployment:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "index.py",
      "use": "@vercel/python",
      "config": {
        "maxDuration": 60
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "index.py"
    }
  ]
}
```

**Deployment Steps:**

1. Install Vercel CLI: `npm i -g vercel`
2. Login: `vercel login`
3. Deploy: `vercel --prod`

### Docker Deployment

#### Using Docker Compose

1. **Build and Run**

   ```bash
   docker compose up --build -d
   ```

2. **View Logs**

   ```bash
   docker compose logs -f
   ```

3. **Stop Services**
   ```bash
   docker compose down
   ```

#### Manual Docker Build

```bash
# Build image
docker build -t orbitrms-backend .

# Run container
docker run -p 8000:8000 --env-file .env orbitrms-backend
```

### Production Considerations

1. **Environment Variables**: Ensure all production secrets are set
2. **Database**: Use production-grade MySQL with backups
3. **Redis**: Use managed Redis service or cluster
4. **SSL/TLS**: Enable HTTPS for all connections
5. **Rate Limiting**: Adjust rate limits for production load
6. **CORS**: Restrict allowed origins to production frontend
7. **Logging**: Set up proper logging and monitoring
8. **Error Tracking**: Integrate error tracking service (Sentry, etc.)
9. **Backups**: Regular database backups
10. **Monitoring**: Set up health checks and alerts

### Health Checks

The application provides health check endpoints:

- `GET /`: Full health check with database status
- `GET /health`: Simple health status

Use these for load balancer health checks and monitoring.

---

## Key Features

### 1. Multi-Tenant Architecture

- Each organization operates independently
- Isolated data per organization
- Organization-specific configurations
- Scalable tenant management

### 2. Employee Management

- Complete employee profiles
- Personal and professional information
- Reporting structure (manager hierarchy)
- Role and permission management
- Department and designation tracking

### 3. Attendance & Leave Management

- Leave request system
- Leave balance tracking
- Multiple leave types
- Approval workflow
- Notification system for leave requests
- Holiday management

### 4. Organization Feed

- Internal social feed for organizations
- Post creation with media
- Like and comment functionality
- Real-time updates via background workers
- Caching for performance

### 5. Social Media Integration

- Connect multiple social media accounts
- OAuth authentication for platforms
- Post scheduling and management
- Support for Facebook, Instagram, Twitter, LinkedIn
- Encrypted token storage

### 6. Client Inquiry System

- Dynamic form builder
- Customizable inquiry forms
- API key-based submissions
- Inquiry status tracking
- Email notifications

### 7. AI Integration

- OpenAI GPT-4 integration
- Conversational AI interface
- Image analysis support
- Multi-turn conversations
- Natural language processing

### 8. Admin Panel

- Super admin functionality
- Organization management
- Employee management across organizations
- Maintenance mode control
- System-wide settings

### 9. Configuration Management

- Department management
- Designation management
- Project status tracking
- Role and permission system
- Customizable settings per organization

### 10. Image Management

- Cloudinary integration
- Image upload and storage
- CDN delivery
- Image optimization
- Secure upload handling

### 11. Email System

- HTML email templates
- Email verification
- Password reset emails
- Welcome emails
- Client inquiry notifications
- Background email sending

### 12. Maintenance Mode

- Scheduled maintenance windows
- Automatic activation/deactivation
- Custom maintenance messages
- System-wide blocking
- Maintenance log tracking

---

## Security Features

### Authentication Security

- **JWT Tokens**: Secure token-based authentication
- **Session Management**: Database-backed sessions
- **Password Hashing**: bcrypt with salt
- **Token Expiration**: Time-based token expiry
- **Multi-layer Encryption**: Additional encryption for sensitive data

### API Security

- **Rate Limiting**: Prevents API abuse
- **CORS Protection**: Configurable cross-origin policies
- **Input Validation**: Pydantic models for all inputs
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **XSS Protection**: Input sanitization

### Data Security

- **Encrypted Tokens**: Social media tokens encrypted at rest
- **Secure Password Storage**: Hashed passwords only
- **Environment Variables**: Secrets in environment, not code
- **Database Connection Security**: SSL/TLS for database connections

### Access Control

- **Role-Based Access**: Permission system
- **Organization Isolation**: Data separation per tenant
- **Account Status Checks**: Active/inactive account validation
- **Organization Status Checks**: Active/inactive organization validation

### Security Best Practices

- Regular dependency updates
- Secure password requirements
- Token rotation capabilities
- Audit logging for sensitive operations
- Error message sanitization

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "message": "Error description",
  "success": false,
  "error": "Detailed error message (optional)",
  "status_code": 400
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Maintenance mode or service down

### Error Categories

1. **Validation Errors**: Pydantic validation failures
2. **Authentication Errors**: Invalid or missing tokens
3. **Authorization Errors**: Insufficient permissions
4. **Not Found Errors**: Resource doesn't exist
5. **Business Logic Errors**: Domain-specific errors
6. **System Errors**: Database, external service failures

### Error Handling Middleware

- Global exception handlers
- Custom error responses
- Error logging
- User-friendly error messages
- Detailed error information in development

---

## Testing

### Test Structure

Tests should be organized in the `test/` directory:

```
test/
├── test_auth.py
├── test_organizations.py
├── test_employees.py
├── test_attendance.py
└── test_helpers.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest test/test_auth.py
```

### Test Best Practices

- Unit tests for helper functions
- Integration tests for API endpoints
- Mock external services (OpenAI, Cloudinary, etc.)
- Use test database
- Clean up test data after tests

---

## Additional Resources

### API Documentation

- **Swagger UI**: Available at `/docs` when server is running
- **ReDoc**: Available at `/redoc` when server is running

### Code Style

- **Black**: Line length 100, Python 3.8+ compatible
- **isort**: Import sorting compatible with Black
- **Type Hints**: Use type hints for better code clarity

### Database Migrations

- Use Alembic for all schema changes
- Never modify models directly in production
- Test migrations in development first
- Keep migration files in version control

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Ensure code passes formatting checks
6. Submit a pull request

### Support

For issues, questions, or contributions:

- **Email**: contact.varunpatel.dev@gmail.com
- **GitHub**: [VarunPatel-07](https://github.com/VarunPatel-07)
- **Website**: [https://varunpatel.vercel.app/](https://varunpatel.vercel.app/)

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Changelog

### Version 1.0.0

- Initial release
- Core features implemented
- Multi-tenant architecture
- Employee management
- Attendance and leave system
- Social media integration
- AI conversation features
- Admin panel

---

**Last Updated**: 2024
**Maintained by**: Varun Patel
