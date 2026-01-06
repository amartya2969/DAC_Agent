"""Input validation utilities."""
import re
from typing import List, Tuple


def validate_email(email: str) -> bool:
    """Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"

    return True, "Password is valid"


def validate_redirect_uri(uri: str) -> bool:
    """Validate redirect URI.

    Args:
        uri: Redirect URI to validate

    Returns:
        True if valid, False otherwise
    """
    if not uri or not isinstance(uri, str):
        return False

    # Must be HTTPS or localhost HTTP
    if uri.startswith('https://'):
        return True
    if uri.startswith('http://localhost') or uri.startswith('http://127.0.0.1'):
        return True

    return False


def validate_scopes(requested_scopes: List[str], allowed_scopes: List[str]) -> bool:
    """Validate that requested scopes are allowed.

    Args:
        requested_scopes: List of requested scope strings
        allowed_scopes: List of allowed scope strings

    Returns:
        True if all requested scopes are allowed, False otherwise
    """
    if not requested_scopes:
        return False

    return all(scope in allowed_scopes for scope in requested_scopes)


def validate_scope_string(scope_string: str) -> bool:
    """Validate scope string format.

    Args:
        scope_string: Space-separated scope string

    Returns:
        True if valid, False otherwise
    """
    if not scope_string or not isinstance(scope_string, str):
        return False

    # Check each scope matches pattern (alphanumeric, colon, underscore, dash)
    scopes = scope_string.split()
    pattern = r'^[a-zA-Z0-9:_-]+$'

    return all(re.match(pattern, scope) for scope in scopes)


def validate_client_id(client_id: str) -> bool:
    """Validate client ID format.

    Args:
        client_id: Client ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not client_id or not isinstance(client_id, str):
        return False

    # Must start with 'agent_' and contain only alphanumeric and underscores
    pattern = r'^agent_[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, client_id))


def validate_state(state: str) -> bool:
    """Validate OAuth state parameter.

    Args:
        state: State parameter to validate

    Returns:
        True if valid, False otherwise
    """
    if not state or not isinstance(state, str):
        return False

    # Must be at least 8 characters
    if len(state) < 8:
        return False

    # Must contain only alphanumeric, dash, and underscore
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, state))
