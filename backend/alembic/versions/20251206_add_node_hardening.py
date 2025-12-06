"""Add hardening information fields to nodes table

Revision ID: 20251206_hardening
Revises: 20251130_system_tunnel
Create Date: 2025-12-06 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251206_hardening'
down_revision = '20251130_system_tunnel'
branch_labels = None
depends_on = None


def upgrade():
    """Add hardening information columns to nodes table

    These columns store security hardening information for each node:
    - Firewall status and rules
    - Antivirus/Defender status
    - Open/listening ports
    - Security modules (SELinux, AppArmor, etc.)
    - Security updates info
    - SSH configuration (Linux/macOS)
    - SSL/TLS configuration
    - Audit logging status
    """

    # Add hardening columns as JSON for flexibility across OS types
    op.add_column('nodes',
        sa.Column('hardening_firewall', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_antivirus', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_open_ports', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_security_modules', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_updates', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_ssh_config', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_ssl_info', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_audit', sa.JSON(), nullable=True)
    )
    op.add_column('nodes',
        sa.Column('hardening_last_scan', sa.DateTime(), nullable=True)
    )


def downgrade():
    """Remove hardening columns from nodes table"""

    op.drop_column('nodes', 'hardening_last_scan')
    op.drop_column('nodes', 'hardening_audit')
    op.drop_column('nodes', 'hardening_ssl_info')
    op.drop_column('nodes', 'hardening_ssh_config')
    op.drop_column('nodes', 'hardening_updates')
    op.drop_column('nodes', 'hardening_security_modules')
    op.drop_column('nodes', 'hardening_open_ports')
    op.drop_column('nodes', 'hardening_antivirus')
    op.drop_column('nodes', 'hardening_firewall')
