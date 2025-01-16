"""add_updated_at_to_interview_sessions

Revision ID: aa43dc25010e
Revises: fdc646f90cac
Create Date: 2025-01-16 11:51:17.087808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = 'aa43dc25010e'
down_revision: Union[str, None] = 'fdc646f90cac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interview_sessions', 
                  sa.Column('updated_at', 
                           sa.DateTime(), 
                           nullable=False, 
                           server_default=func.now()))


def downgrade() -> None:
    op.drop_column('interview_sessions', 'updated_at')
