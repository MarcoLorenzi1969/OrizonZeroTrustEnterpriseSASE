"""Add reverse tunnel configuration to nodes

Revision ID: 20251125_add_tunnel
Revises: 20251111_add_groups
Create Date: 2025-11-25 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '20251125_add_tunnel'
down_revision = '20251111_add_groups'
branch_labels = None
depends_on = None


def upgrade():
    """Add reverse tunnel configuration fields to nodes table"""

    # Add reverse_tunnel_type column
    op.add_column('nodes',
        sa.Column('reverse_tunnel_type', sa.String(20),
                  nullable=False, server_default='SSH')
    )

    # Add exposed_applications column (JSON array)
    op.add_column('nodes',
        sa.Column('exposed_applications', JSON,
                  nullable=False, server_default='[]')
    )

    # Add application_ports column (JSON dict)
    op.add_column('nodes',
        sa.Column('application_ports', JSON,
                  nullable=False, server_default='{}')
    )

    # Add agent_token column (unique token for agent authentication)
    op.add_column('nodes',
        sa.Column('agent_token', sa.String(255),
                  nullable=True, unique=True)
    )

    # Create check constraint for tunnel type
    op.execute("""
        ALTER TABLE nodes
        ADD CONSTRAINT check_tunnel_type
        CHECK (reverse_tunnel_type IN ('SSH', 'SSL'))
    """)

    # Create index for faster filtering by tunnel type
    op.create_index(
        'idx_nodes_tunnel_type',
        'nodes',
        ['reverse_tunnel_type']
    )

    # Create index for agent_token lookups
    op.create_index(
        'idx_nodes_agent_token',
        'nodes',
        ['agent_token']
    )


def downgrade():
    """Remove reverse tunnel configuration fields"""

    # Drop indexes
    op.drop_index('idx_nodes_agent_token', 'nodes')
    op.drop_index('idx_nodes_tunnel_type', 'nodes')

    # Drop constraint
    op.execute('ALTER TABLE nodes DROP CONSTRAINT IF EXISTS check_tunnel_type')

    # Drop columns
    op.drop_column('nodes', 'agent_token')
    op.drop_column('nodes', 'application_ports')
    op.drop_column('nodes', 'exposed_applications')
    op.drop_column('nodes', 'reverse_tunnel_type')
