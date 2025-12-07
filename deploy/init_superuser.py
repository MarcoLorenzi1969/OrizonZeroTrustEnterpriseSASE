#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - Initialize Default Superuser
For: Marco @ Syneto/Orizon

This script creates or updates the default superuser account.
Run this after initial deployment to set up admin access.

Default credentials:
- Email: marco@syneto.eu
- Password: Syneto2601AA
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole, UserStatus


# Default superuser credentials
DEFAULT_SUPERUSER = {
    "email": "marco@syneto.eu",
    "username": "marco",
    "full_name": "Marco Lorenzi",
    "company": "Syneto/Orizon",
    "password": "Syneto2601AA",
    "role": UserRole.SUPERUSER,
}


async def init_superuser():
    """Create or update the default superuser"""

    print("\n" + "=" * 60)
    print("  Orizon Zero Trust Connect - Initialize Superuser")
    print("=" * 60 + "\n")

    try:
        # Initialize database connection
        await init_db()

        async with AsyncSessionLocal() as db:
            # Check if user exists
            result = await db.execute(
                select(User).where(User.email == DEFAULT_SUPERUSER["email"])
            )
            existing_user = result.scalar_one_or_none()

            # Generate password hash
            password_hash = get_password_hash(DEFAULT_SUPERUSER["password"])

            if existing_user:
                # Update existing user
                print(f"User {DEFAULT_SUPERUSER['email']} already exists.")
                print("Updating password and ensuring superuser role...")

                await db.execute(
                    update(User)
                    .where(User.email == DEFAULT_SUPERUSER["email"])
                    .values(
                        hashed_password=password_hash,
                        role=DEFAULT_SUPERUSER["role"],
                        is_active=True,
                        status=UserStatus.ACTIVE,
                    )
                )
                await db.commit()
                print(f"Password updated for {DEFAULT_SUPERUSER['email']}")
            else:
                # Create new user
                print(f"Creating superuser: {DEFAULT_SUPERUSER['email']}")

                new_user = User(
                    email=DEFAULT_SUPERUSER["email"],
                    username=DEFAULT_SUPERUSER["username"],
                    full_name=DEFAULT_SUPERUSER["full_name"],
                    company=DEFAULT_SUPERUSER["company"],
                    hashed_password=password_hash,
                    role=DEFAULT_SUPERUSER["role"],
                    status=UserStatus.ACTIVE,
                    is_active=True,
                    can_create_users=True,
                    can_manage_tunnels=True,
                    can_view_logs=True,
                    can_manage_nodes=True,
                )

                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)
                print(f"Superuser created with ID: {new_user.id}")

            # Verify the password works
            result = await db.execute(
                select(User).where(User.email == DEFAULT_SUPERUSER["email"])
            )
            user = result.scalar_one()

            if verify_password(DEFAULT_SUPERUSER["password"], user.hashed_password):
                print("\nPassword verification: OK")
            else:
                print("\nPassword verification: FAILED")
                return

            print("\n" + "=" * 60)
            print("  Default Superuser Credentials")
            print("=" * 60)
            print(f"\n  Email:    {DEFAULT_SUPERUSER['email']}")
            print(f"  Password: {DEFAULT_SUPERUSER['password']}")
            print(f"  Role:     SUPERUSER")
            print("\n" + "=" * 60)
            print("  Use these credentials to login to the web interface")
            print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(init_superuser())
    sys.exit(exit_code or 0)
