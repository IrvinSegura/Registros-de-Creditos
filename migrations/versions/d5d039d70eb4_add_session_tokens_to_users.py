"""add session tokens to users

Revision ID: d5d039d70eb4
Revises: a0466543d65d
Create Date: 2026-10-22 21:30:00.000000

"""
import secrets

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5d039d70eb4'
down_revision = 'a0466543d65d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_token', sa.String(length=64), nullable=True))

    # Every existing account gets its own token; sessions opened before this (which hold the id) end
    users = sa.table('users', sa.column('id', sa.Integer()), sa.column('session_token', sa.String()))
    connection = op.get_bind()
    for (user_id,) in connection.execute(sa.select(users.c.id)).all():
        connection.execute(
            users.update().where(users.c.id == user_id).values(session_token=secrets.token_urlsafe(32))
        )

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('session_token', existing_type=sa.String(length=64), nullable=False)
        batch_op.create_unique_constraint('uq_users_session_token', ['session_token'])


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('uq_users_session_token', type_='unique')
        batch_op.drop_column('session_token')
