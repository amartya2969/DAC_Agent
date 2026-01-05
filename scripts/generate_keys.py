"""Generate RSA key pair for JWT signing."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.security import generate_rsa_keys, save_keys


def generate_keys():
    """Generate and save RSA key pair."""
    print("Generating RSA key pair for JWT signing...")

    # Generate keys
    private_key, public_key = generate_rsa_keys()
    print("✓ Generated 2048-bit RSA key pair")

    # Save keys
    save_keys(private_key, public_key, directory='keys')
    print("✓ Saved keys to 'keys/' directory:")
    print("   - keys/private_key.pem")
    print("   - keys/public_key.pem")

    print("\n" + "=" * 60)
    print("IMPORTANT SECURITY NOTES:")
    print("=" * 60)
    print("1. Keep private_key.pem SECRET and secure")
    print("2. Never commit private_key.pem to version control")
    print("3. Use proper file permissions (chmod 600 private_key.pem)")
    print("4. Back up keys securely")
    print("5. Rotate keys periodically in production")
    print("=" * 60)


if __name__ == '__main__':
    generate_keys()
