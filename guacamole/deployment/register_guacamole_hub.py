#!/usr/bin/env python3
"""
Orizon Zero Trust Connect - Register Guacamole Hub

This script registers the Guacamole server as a hub in the Orizon ZTC system.
Run this on the main Orizon hub (46.101.189.126) after Guacamole installation.
"""

import asyncio
import asyncpg
import uuid
from datetime import datetime
import sys

# Database configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "orizon_ztc"
DB_USER = "orizonuser"
DB_PASSWORD = "orizonpass"

# Guacamole hub details
GUAC_HUB_IP = "167.71.33.70"
GUAC_HUB_NAME = "Guacamole SSH/RDP Hub"
GUAC_HUB_DESCRIPTION = "Apache Guacamole gateway for web-based SSH/RDP/VNC access"


async def register_guacamole_hub():
    """Register Guacamole server as hub in Orizon database"""

    print("=" * 60)
    print("Orizon ZTC - Guacamole Hub Registration")
    print("=" * 60)
    print()

    # Connect to database
    print(f"Connecting to database: {DB_NAME}@{DB_HOST}...")
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        sys.exit(1)

    try:
        # Check if guacamole hub already exists
        existing = await conn.fetchrow(
            """
            SELECT id, name FROM nodes
            WHERE ip_address = $1 AND node_type = 'hub'
            """,
            GUAC_HUB_IP
        )

        if existing:
            print(f"\n⚠ Guacamole hub already registered:")
            print(f"  ID: {existing['id']}")
            print(f"  Name: {existing['name']}")
            print(f"  IP: {GUAC_HUB_IP}")

            # Update existing record
            await conn.execute(
                """
                UPDATE nodes
                SET
                    name = $1,
                    description = $2,
                    status = 'online',
                    last_seen = $3,
                    updated_at = $3
                WHERE ip_address = $4 AND node_type = 'hub'
                """,
                GUAC_HUB_NAME,
                GUAC_HUB_DESCRIPTION,
                datetime.utcnow(),
                GUAC_HUB_IP
            )
            print("✓ Hub record updated")

        else:
            # Create new hub record
            hub_id = str(uuid.uuid4())
            print(f"\nCreating Guacamole hub record...")
            print(f"  ID: {hub_id}")
            print(f"  Name: {GUAC_HUB_NAME}")
            print(f"  IP: {GUAC_HUB_IP}")

            await conn.execute(
                """
                INSERT INTO nodes (
                    id, name, description, node_type, status,
                    ip_address, last_seen, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                hub_id,
                GUAC_HUB_NAME,
                GUAC_HUB_DESCRIPTION,
                'hub',
                'online',
                GUAC_HUB_IP,
                datetime.utcnow(),
                datetime.utcnow(),
                datetime.utcnow()
            )
            print("✓ Hub registered successfully")

        # Add guacamole-specific columns if not exist
        print("\nChecking database schema...")
        try:
            await conn.execute(
                """
                ALTER TABLE nodes
                ADD COLUMN IF NOT EXISTS guacamole_connection_id VARCHAR(255),
                ADD COLUMN IF NOT EXISTS guacamole_rdp_connection_id VARCHAR(255)
                """
            )
            print("✓ Database schema updated")
        except Exception as e:
            print(f"⚠ Schema update: {e}")

        # Verify registration
        hub = await conn.fetchrow(
            """
            SELECT id, name, ip_address, node_type, status, last_seen
            FROM nodes
            WHERE ip_address = $1 AND node_type = 'hub'
            """,
            GUAC_HUB_IP
        )

        if hub:
            print("\n" + "=" * 60)
            print("✓ GUACAMOLE HUB REGISTRATION SUCCESSFUL")
            print("=" * 60)
            print(f"\nHub Details:")
            print(f"  ID: {hub['id']}")
            print(f"  Name: {hub['name']}")
            print(f"  Type: {hub['node_type']}")
            print(f"  IP Address: {hub['ip_address']}")
            print(f"  Status: {hub['status']}")
            print(f"  Last Seen: {hub['last_seen']}")
            print()
            print("Next Steps:")
            print("1. Access Guacamole: https://167.71.33.70/guacamole/")
            print("2. Login with: guacadmin / guacadmin")
            print("3. Change default password")
            print("4. Access Orizon dashboard to sync nodes")
            print()

        else:
            print("✗ Verification failed - hub not found in database")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Registration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await conn.close()
        print("Database connection closed")


if __name__ == "__main__":
    print()
    print("This script will register the Guacamole hub in Orizon ZTC")
    print("Run this on the main Orizon hub server (46.101.189.126)")
    print()

    response = input("Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Registration cancelled")
        sys.exit(0)

    print()
    asyncio.run(register_guacamole_hub())
