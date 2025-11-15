#!/usr/bin/env python3
"""
Generate secure secret keys for Orizon Zero Trust Connect
For: Marco @ Syneto/Orizon
"""

import secrets
import string

def generate_secret_key(length=64):
    """Generate a cryptographically secure random string"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    print("=" * 80)
    print("🔐 Orizon Zero Trust Connect - Secret Key Generator")
    print("=" * 80)
    print()

    # Generate keys
    secret_key = generate_secret_key(64)
    jwt_secret_key = generate_secret_key(64)

    print("✅ Generated secure secret keys:")
    print()
    print("Copy these into your .env file:")
    print("-" * 80)
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    print("-" * 80)
    print()

    # Option to use same key
    print("💡 TIP: Per semplificare, puoi usare la stessa chiave per entrambi:")
    print("-" * 80)
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={secret_key}")
    print("-" * 80)
    print()

    print("⚠️  IMPORTANTE:")
    print("   - NON condividere queste chiavi")
    print("   - NON commitare il file .env su Git")
    print("   - Usa chiavi diverse in development e production")
    print()
    print("=" * 80)
