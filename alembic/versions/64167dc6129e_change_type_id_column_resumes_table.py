"""change_type_id_column_resumes_table

Revision ID: 64167dc6129e
Revises: 2278cef7d047
Create Date: 2025-01-03 17:28:48.562949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision: str = '64167dc6129e'
down_revision: Union[str, None] = '2278cef7d047'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Convert the id column to UUID
    op.alter_column(
        'resumes',
        'id',
        existing_type=sa.String(),
        type_=UUID(as_uuid=True),
        existing_nullable=False
    )


def downgrade():
    # Revert the id column back to String
    op.alter_column(
        'resumes',
        'id',
        existing_type=UUID(as_uuid=True),
        type_=sa.String(),
        existing_nullable=False
    )