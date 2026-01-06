"""Configuration management."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # Server settings
    AUTH_SERVER_HOST = os.getenv('AUTH_SERVER_HOST', 'localhost')
    AUTH_SERVER_PORT = int(os.getenv('AUTH_SERVER_PORT', 5000))
    RESOURCE_SERVER_HOST = os.getenv('RESOURCE_SERVER_HOST', 'localhost')
    RESOURCE_SERVER_PORT = int(os.getenv('RESOURCE_SERVER_PORT', 5001))

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/oauth.db')

    # Security
    SECRET_KEY = os.getenv('AUTH_SERVER_SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'RS256')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))
    BCRYPT_ROUNDS = int(os.getenv('BCRYPT_ROUNDS', 12))

    # Authorization code expiration (5 minutes)
    AUTH_CODE_EXPIRES = 300

    # Session expiration (1 hour)
    SESSION_EXPIRES = 3600

    @classmethod
    def get_auth_server_url(cls) -> str:
        """Get authorization server base URL."""
        return f"http://{cls.AUTH_SERVER_HOST}:{cls.AUTH_SERVER_PORT}"

    @classmethod
    def get_resource_server_url(cls) -> str:
        """Get resource server base URL."""
        return f"http://{cls.RESOURCE_SERVER_HOST}:{cls.RESOURCE_SERVER_PORT}"
