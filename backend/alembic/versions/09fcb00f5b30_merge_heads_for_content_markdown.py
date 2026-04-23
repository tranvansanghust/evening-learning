"""merge_heads_for_content_markdown

Revision ID: 09fcb00f5b30
Revises: 74d83fa0bdb7, e5f6a7b8c9d0
Create Date: 2026-04-23 10:33:10.475520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09fcb00f5b30'
down_revision: Union[str, Sequence[str], None] = ('74d83fa0bdb7', 'e5f6a7b8c9d0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
