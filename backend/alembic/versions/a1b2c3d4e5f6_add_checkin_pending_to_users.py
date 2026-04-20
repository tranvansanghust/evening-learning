"""add checkin_pending to users

Revision ID: a1b2c3d4e5f6
Revises: 87d575cf97ab
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '87d575cf97ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add checkin_pending boolean column to users table."""
    op.add_column(
        'users',
        sa.Column(
            'checkin_pending',
            sa.Boolean(),
            nullable=False,
            server_default='0',
        )
    )


def downgrade() -> None:
    """Remove checkin_pending column from users table."""
    op.drop_column('users', 'checkin_pending')
