#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - Create Admin User Script
For: Marco @ Syneto/Orizon
Creates the first admin user for the application
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db.database import get_db
from app.models.user import User
from app.auth.security import get_password_hash
from sqlalchemy import select
import getpass


async def create_admin_user():
    """Create admin user interactively"""

    print("\n" + "="*60)
    print("  Orizon Zero Trust Connect - Create Admin User")
    print("="*60 + "\n")

    # Get user input
    print("Enter admin user details:\n")

    email = input("Email: ").strip()
    if not email:
        print("❌ Email is required")
        return

    full_name = input("Full Name: ").strip()
    if not full_name:
        print("❌ Full name is required")
        return

    password = getpass.getpass("Password (min 12 chars): ")
    password_confirm = getpass.getpass("Confirm Password: ")

    if password != password_confirm:
        print("❌ Passwords do not match")
        return

    if len(password) < 12:
        print("❌ Password must be at least 12 characters")
        return

    # Connect to database
    print("\n🔄 Connecting to database...")

    try:
        async for db in get_db():
            # Check if user already exists
            result = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"❌ User with email {email} already exists")
                return

            # Create admin user
            hashed_password = get_password_hash(password)

            admin_user = User(
                email=email,
                full_name=full_name,
                hashed_password=hashed_password,
                role="superuser",
                is_active=True,
                totp_enabled=False
            )

            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

            print("\n" + "="*60)
            print("✅ Admin user created successfully!")
            print("="*60)
            print(f"\nUser ID:   {admin_user.id}")
            print(f"Email:     {admin_user.email}")
            print(f"Name:      {admin_user.full_name}")
            print(f"Role:      {admin_user.role}")
            print(f"\n📝 Next steps:")
            print("  1. Login at the frontend with these credentials")
            print("  2. Enable 2FA in Settings for enhanced security")
            print("  3. Create additional users via the API\n")

    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
