"""add mcq columns to quiz_answer

Revision ID: a1b2c3d4e5f6
Revises: fa6c6359d5d0
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'fa6c6359d5d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('quiz_answers', sa.Column('question_id', sa.String(36), nullable=True))
    op.add_column('quiz_answers', sa.Column('correct_answer', sa.Text(), nullable=True))
    op.add_column('quiz_answers', sa.Column('choices', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('quiz_answers', 'choices')
    op.drop_column('quiz_answers', 'correct_answer')
    op.drop_column('quiz_answers', 'question_id')
