"""merge multiple heads

Revision ID: 6e04619fe8df
Revises: g4h5i6j7k8l9, e2f537e4eb44
Create Date: 2025-11-15 20:26:03.286238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e04619fe8df'
down_revision: Union[str, None] = ('g4h5i6j7k8l9', 'e2f537e4eb44')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
