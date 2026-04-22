"""add q1_text q2_text to onboarding_state

Revision ID: e5f6a7b8c9d0
Revises: 42d4167ad3c4
Create Date: 2026-04-22 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = '42d4167ad3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('onboarding_states', sa.Column('q1_text', sa.String(300), nullable=True))
    op.add_column('onboarding_states', sa.Column('q2_text_if_no', sa.String(300), nullable=True))
    op.add_column('onboarding_states', sa.Column('q2_text_if_yes', sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column('onboarding_states', 'q2_text_if_yes')
    op.drop_column('onboarding_states', 'q2_text_if_no')
    op.drop_column('onboarding_states', 'q1_text')
