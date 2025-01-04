"""modify_users_table_primary_key

Revision ID: 2278cef7d047
Revises: 8245a000cfe5
Create Date: 2025-01-03 17:00:08.414509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2278cef7d047'
down_revision: Union[str, None] = '8245a000cfe5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the existing primary key constraint
    op.execute('ALTER TABLE users DROP CONSTRAINT users_pkey')
    # Create a temporary primary key constraint on user_id
    op.execute('ALTER TABLE users ADD PRIMARY KEY (user_id)')
    
    # Drop the existing id column
    op.drop_column('users', 'id')

def downgrade():
    # Add back the id column
    op.add_column('users', 
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True)
    )
    
    # Move primary key back to id
    op.execute('ALTER TABLE users DROP CONSTRAINT users_pkey')
    op.create_primary_key('users_pkey', 'users', ['id'])
    
    # Add back the index on id
    op.create_index('ix_users_id', 'users', ['id'])
