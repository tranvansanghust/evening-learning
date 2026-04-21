"""add_spaced_repetition_to_quiz_summary

Revision ID: c1d2e3f4a5b6
Revises: 87d575cf97ab
Create Date: 2026-04-20 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '87d575cf97ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add spaced repetition columns to quiz_summaries."""
    op.add_column('quiz_summaries', sa.Column('next_review_at', sa.DateTime(), nullable=True))
    op.add_column(
        'quiz_summaries',
        sa.Column('review_count', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    """Remove spaced repetition columns from quiz_summaries."""
    op.drop_column('quiz_summaries', 'review_count')
    op.drop_column('quiz_summaries', 'next_review_at')
