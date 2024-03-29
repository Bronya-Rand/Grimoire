"""add tables for multiuser

Revision ID: 7cbb06f823fc
Revises: 4b9a98eb28b8
Create Date: 2024-03-25 15:54:45.021609

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision: str = '7cbb06f823fc'
down_revision: Union[str, None] = '4b9a98eb28b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Base = declarative_base()


class Chat(Base):
    __tablename__ = 'chat'

    id = sa.Column(sa.Integer, primary_key=True)
    external_id = sa.Column(sa.String, nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)


class User(Base):
    __tablename__ = 'user'

    id = sa.Column(sa.Integer, primary_key=True)
    external_id = sa.Column(sa.String, nullable=False)


class Message(Base):
    __tablename__ = 'message'

    id = sa.Column(sa.Integer, primary_key=True)
    chat_id = sa.Column(sa.String, nullable=False)


def upgrade() -> None:
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # Creating User table and adding default user
    op.create_table('user',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('external_id', sa.String(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )

    default_user = User(external_id='DEFAULT_USER')
    session.add(default_user)
    session.commit()

    # Creating Chat table and adding already existing chat ids
    op.create_table('chat',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('external_id', sa.String(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    existing_chats = session.query(Message.chat_id).distinct()
    chats = [Chat(external_id=chat_id, user_id=default_user.id) for chat_id in existing_chats]
    session.add_all(chats)
    session.commit()

    # Migrating the data and modifying Knowledge table
    op.add_column('knowledge', sa.Column('new_chat_id', sa.Integer(), nullable=True))
    for chat in chats:
        op.execute('UPDATE knowledge SET new_chat_id = :chat_id WHERE chat_id = :external_id',
                   execution_options={
                       'chat_id': chat.id,
                       'external_id': chat.external_id
                   })
    op.drop_column('knowledge', 'chat_id')
    op.alter_column('knowledge', 'new_chat_id',
                    table_name='chat_id',
                    existing_nullable=True,
                    nullable=False)
    op.create_foreign_key(None, 'knowledge', 'chat', ['chat_id'], ['id'])

    # Migrating the data and modifying Message table
    op.add_column('message', sa.Column('new_chat_id', sa.Integer(), nullable=True))
    for chat in chats:
        op.execute('UPDATE message SET new_chat_id = :chat_id WHERE chat_id = :external_id',
                   execution_options={
                       'chat_id': chat.id,
                       'external_id': chat.external_id
                   })
    op.drop_column('message', 'chat_id')
    op.alter_column('message', 'new_chat_id',
                    table_name='chat_id',
                    existing_nullable=True,
                    nullable=False)
    op.create_foreign_key(None, 'message', 'chat', ['chat_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    chats = session.query(Chat).all()

    # Moving old ids into Message table
    op.drop_constraint(None, 'message', type_='foreignkey')
    op.add_column('message', sa.Column('old_chat_id', sa.VARCHAR(), nullable=True))
    for chat in chats:
        op.execute('UPDATE message SET old_chat_id = :external_id WHERE chat_id = :chat_id',
                   execution_options={
                       'chat_id': chat.id,
                       'external_id': chat.external_id
                   })
    op.drop_column('message', 'chat_id')
    op.alter_column('message', 'new_chat_id',
                    table_name='chat_id',
                    existing_nullable=True,
                    nullable=False)

    # Moving old ids into Knowledge table
    op.drop_constraint(None, 'knowledge', type_='foreignkey')
    op.add_column('knowledge', sa.Column('old_chat_id', sa.VARCHAR(), nullable=True))
    for chat in chats:
        op.execute('UPDATE knowledge SET old_chat_id = :external_id WHERE chat_id = :chat_id',
                   execution_options={
                       'chat_id': chat.id,
                       'external_id': chat.external_id
                   })
    op.drop_column('knowledge', 'chat_id')
    op.alter_column('knowledge', 'new_chat_id',
                    table_name='chat_id',
                    existing_nullable=True,
                    nullable=False)

    # Dropping new tables
    op.drop_table('chat')
    op.drop_table('user')
    # ### end Alembic commands ###
