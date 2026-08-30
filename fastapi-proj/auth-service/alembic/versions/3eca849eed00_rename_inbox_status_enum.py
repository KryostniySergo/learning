"""rename inbox status enum

Revision ID: 3eca849eed00
Revises: 7d191954deeb
Create Date: 2026-08-30 23:25:11.105054

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3eca849eed00"
down_revision: str | Sequence[str] | None = "7d191954deeb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE inmessagestatus RENAME TO inboxmessagestatus")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE inboxmessagestatus RENAME TO inmessagestatus")
