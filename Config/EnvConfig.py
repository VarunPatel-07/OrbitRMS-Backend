import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EnvConfig:

    # ! ----------- Starting Of The All The EnvSecrets Related To Database Or Migration ---------

    # Main database connection string
    DATABASE_CONNECTION_STRING = os.getenv("DATABASE_CONNECTION_STRING")

    # Staging migration database URL (used for staging environment migrations)
    STAGING_MIGRATION_DB_URL = os.getenv("STAGING_MIGRATION_DB_URL")

    # Development migration database URL (used for development environment migrations)
    DEVELOPMENT_MIGRATION_DB_URL = os.getenv("DEVELOPMENT_MIGRATION_DB_URL")

    # ! ----------- Ending Of The All The EnvSecrets Related To Database Or Migration ---------

    # ? ----------- Starting Of The All The EnvSecrets Related To JWT ---------

    # Secret key used to sign JWT tokens
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # Algorithm used for JWT encoding and decoding
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

    # Encryption key used for sensitive data encryption
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

    # Super secure hash password (used for extra hashing mechanisms)
    SUPER_SECURE_HASH_PASSWORD = os.getenv("SUPER_SECURE_HASH_PASSWORD")

    # API rate limiting configuration
    API_RATE_LIMITING = os.getenv("API_RATE_LIMITING")

    # ? ----------- Ending Of The All The EnvSecrets Related To JWT ---------

    # * ----------- Starting Of The All The EnvSecrets Related To Application Config ---------

    # Frontend application URL
    FRONTEND_URL = os.getenv("FRONTEND_URL")

    BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL")

    SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

    # Backend environment type (e.g., development, staging, production)
    BACKEND_APP_ENVIRONMENT = os.getenv("BACKEND_APP_ENVIRONMENT")

    # Geoname API username (for location-related services)
    GEONAME_API_USERNAME = os.getenv("GEONAME_API_USERNAME")

    # * ----------- Ending Of The All The EnvSecrets Related To Application Config ---------

    # ^ ----------- Starting Of The All The EnvSecrets Related To Email/Mail Services ---------

    # Google App-specific password (for sending emails via Gmail SMTP)
    GOOGLE_APP_PASSWORD = os.getenv("GOOGLE_APP_PASSWORD")

    # Email address used for sending application emails
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")

    # SMTP email server port
    EMAIL_PORT = os.getenv("EMAIL_PORT")

    # SMTP email server address
    EMAIL_SERVER_ADDRESS = os.getenv("EMAIL_SERVER_ADDRESS")

    # ^ ----------- Ending Of The All The EnvSecrets Related To Email/Mail Services ---------

    # ~ ----------- Starting Of The All The EnvSecrets Related To Cloudinary ---------

    # Cloudinary cloud name (used for storing and retrieving media)
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")

    # Cloudinary API key (for authentication)
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")

    # Cloudinary API secret (for secure operations)
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

    # ~ ----------- Ending Of The All The EnvSecrets Related To Cloudinary ---------

    # + ----------- Starting Of The All The EnvSecrets Related To Cached Database ---------

    # Cached database host (used for local cache server)
    CACHED_DATABASE_HOST = os.getenv("CACHED_DATABASE_HOST")

    # Cached database port
    CACHED_DATABASE_PORT = os.getenv("CACHED_DATABASE_PORT")

    # Cached database password
    CACHED_DATABASE_PASSWORD = os.getenv("CACHED_DATABASE_PASSWORD")

    # + ----------- Ending Of The All The EnvSecrets Related To Cached Database ---------

    # % ----------- Starting Of The All The EnvSecrets Related To Social Media Links ---------

    # Instagram profile/page link
    INSTAGRAM_LINK = os.getenv("INSTAGRAM_LINK")

    # Facebook profile/page link
    FACEBOOK_LINK = os.getenv("FACEBOOK_LINK")

    # LinkedIn profile/page link
    LINKEDIN_LINK = os.getenv("LINKEDIN_LINK")

    # % ----------- Ending Of The All The EnvSecrets Related To Social Media Links ---------

    # $ ----------- Starting Of The All The EnvSecrets Related To Admin/Owner ---------

    # Admin panel email address
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

    # Admin panel password
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    # OrbitRMS owner email
    ORBITRMS_OWNER_EMAIL = os.getenv("ORBITRMS_OWNER_EMAIL")

    # Orbit contact email
    ORBIT_CONTACT_EMAIL = os.getenv("ORBIT_CONTACT_EMAIL")

    # $ ----------- Ending Of The All The EnvSecrets Related To Admin/Owner ---------

    # & ----------- Starting Of The All The EnvSecrets Related To REST API ---------

    # REST API base URL
    REST_API_URL = os.getenv("REST_API_URL")

    # & ----------- Ending Of The All The EnvSecrets Related To REST API ---------

    # ! ------- STARTING OF ALL THE SOCIAL MEDIA MODULE RELATED API KEY ---------
    META_APP_ID = os.getenv("META_APP_ID")
    META_APP_SECRET = os.getenv("META_APP_SECRET")
    META_API_VERSION = os.getenv("META_API_VERSION")
    META_GRAPH_BASE_URL = os.getenv("META_GRAPH_BASE_URL")
