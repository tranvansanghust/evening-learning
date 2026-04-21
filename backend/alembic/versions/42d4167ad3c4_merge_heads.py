"""merge_heads

Revision ID: 42d4167ad3c4
Revises: a48efb32b68d, c1d2e3f4a5b6
Create Date: 2026-04-21 13:59:39.189374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42d4167ad3c4'
down_revision: Union[str, Sequence[str], None] = ('a48efb32b68d', 'c1d2e3f4a5b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
