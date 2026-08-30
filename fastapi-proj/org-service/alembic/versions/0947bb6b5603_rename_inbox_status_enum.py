"""rename inbox status enum

Revision ID: 0947bb6b5603
Revises: cfd70df5b414
Create Date: 2026-08-30 23:24:30.795888

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0947bb6b5603"
down_revision: str | Sequence[str] | None = "cfd70df5b414"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE inmessagestatus RENAME TO inboxmessagestatus")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE inboxmessagestatus RENAME TO inmessagestatus")
