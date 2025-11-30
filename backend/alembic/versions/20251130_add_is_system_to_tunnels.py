"""Add is_system flag to tunnels table

Revision ID: 20251130_system_tunnel
Revises: 20251125_add_tunnel
Create Date: 2025-11-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251130_system_tunnel'
down_revision = '20251125_add_tunnel'
branch_labels = None
depends_on = None


def upgrade():
    """Add is_system column to tunnels table

    This flag identifies system tunnels that:
    - Are created automatically when a node is registered
    - Cannot be deleted via API (protected)
    - Are used for hub-to-edge management access
    - Get deleted only when the associated node is deleted
    """

    # Add is_system column with default False for existing tunnels
    op.add_column('tunnels',
        sa.Column('is_system', sa.Boolean(),
                  nullable=False, server_default='false')
    )

    # Create index for faster filtering of system tunnels
    op.create_index(
        'idx_tunnels_is_system',
        'tunnels',
        ['is_system']
    )


def downgrade():
    """Remove is_system column from tunnels table"""

    # Drop index
    op.drop_index('idx_tunnels_is_system', 'tunnels')

    # Drop column
    op.drop_column('tunnels', 'is_system')
