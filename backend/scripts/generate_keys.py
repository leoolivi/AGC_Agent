#!/usr/bin/env python3
"""Generate encryption keys for ACG configuration."""
import secrets

from cryptography.fernet import Fernet


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret key."""
    return secrets.token_urlsafe(32)


def generate_fernet_key() -> str:
    """Generate a Fernet encryption key for Google tokens."""
    return Fernet.generate_key().decode()


def main() -> None:
    """Generate and print all required keys."""
    print("=== ACG Configuration Keys ===\n")
    
    print("JWT_SECRET_KEY:")
    print(generate_jwt_secret())
    print()
    
    print("GOOGLE_TOKEN_ENCRYPTION_KEY:")
    print(generate_fernet_key())
    print()
    
    print("\nCopy these values to your .env file")
    print("⚠️  Keep these keys secret and never commit them to version control!")


if __name__ == "__main__":
    main()
