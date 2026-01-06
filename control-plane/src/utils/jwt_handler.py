"""JWT token handling utilities."""
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any
from .config import Config
from .security import generate_token


class JWTHandler:
    """Handle JWT token creation and verification."""

    def __init__(self, private_key, public_key):
        """Initialize JWT handler with RSA keys.

        Args:
            private_key: RSA private key for signing
            public_key: RSA public key for verification
        """
        self.private_key = private_key
        self.public_key = public_key

    def create_access_token(
        self,
        user_id: str,
        client_id: str,
        scopes: list
    ) -> tuple[str, str, datetime]:
        """Create JWT access token.

        Args:
            user_id: User identifier
            client_id: Agent client identifier
            scopes: List of granted scopes

        Returns:
            Tuple of (token, jti, expiration_datetime)
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
        jti = generate_token(16)

        payload = {
            'iss': Config.get_auth_server_url(),
            'sub': user_id,
            'aud': Config.get_resource_server_url(),
            'exp': int(expires_at.timestamp()),
            'iat': int(now.timestamp()),
            'client_id': client_id,
            'scope': ' '.join(scopes),
            'jti': jti
        }

        token = jwt.encode(payload, self.private_key, algorithm='RS256')
        return token, jti, expires_at

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT access token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            ValueError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=['RS256'],
                audience=Config.get_resource_server_url(),
                issuer=Config.get_auth_server_url()
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    def decode_token_without_verification(self, token: str) -> Dict[str, Any]:
        """Decode token without verification (for introspection).

        Args:
            token: JWT token string

        Returns:
            Decoded token payload
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            raise ValueError(f"Cannot decode token: {str(e)}")
