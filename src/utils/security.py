"""Security utilities for hashing, encryption, and token generation."""
import bcrypt
import secrets
import hashlib
import base64
from typing import Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def hash_password(password: str) -> str:
    """Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password as string
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash.

    Args:
        password: Plain text password
        password_hash: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def generate_token(length: int = 32) -> str:
    """Generate cryptographically secure random token.

    Args:
        length: Number of bytes for token (default 32)

    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash token for storage using SHA-256.

    Args:
        token: Token to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code challenge against verifier.

    Args:
        code_verifier: Original code verifier
        code_challenge: Code challenge from authorization request

    Returns:
        True if verification succeeds, False otherwise
    """
    # Compute SHA-256 hash of verifier
    computed_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    # Base64 URL encode and remove padding
    computed_challenge = base64.urlsafe_b64encode(computed_hash).decode('utf-8').rstrip('=')
    return computed_challenge == code_challenge


def generate_rsa_keys() -> Tuple:
    """Generate RSA key pair for JWT signing.

    Returns:
        Tuple of (private_key, public_key)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key


def save_keys(private_key, public_key, directory: str = 'keys'):
    """Save RSA keys to PEM files.

    Args:
        private_key: Private key object
        public_key: Public key object
        directory: Directory to save keys (default 'keys')
    """
    import os
    os.makedirs(directory, exist_ok=True)

    # Save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(f'{directory}/private_key.pem', 'wb') as f:
        f.write(private_pem)

    # Save public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(f'{directory}/public_key.pem', 'wb') as f:
        f.write(public_pem)


def load_keys(directory: str = 'keys') -> Tuple:
    """Load RSA keys from PEM files.

    Args:
        directory: Directory containing keys (default 'keys')

    Returns:
        Tuple of (private_key, public_key)
    """
    # Load private key
    with open(f'{directory}/private_key.pem', 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    # Load public key
    with open(f'{directory}/public_key.pem', 'rb') as f:
        public_key = serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )

    return private_key, public_key
