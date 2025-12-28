"""move profile to separate table

Revision ID: 0005_move_profile_to_separate_table
Revises: 0004_add_new_features
Create Date: 2025-12-28 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_profile_separate'
down_revision: Union[str, None] = '0004_add_new_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу user_profiles
    op.create_table(
        'user_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True, unique=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('show_birthday', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Проверяем, существуют ли колонки в таблице users перед миграцией данных
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('date_of_birth', 'show_birthday', 'avatar_url')
    """))
    existing_columns = {row[0] for row in result}
    
    # Переносим данные из users в user_profiles только если колонки существуют
    if existing_columns:
        # Строим SELECT с проверкой существования колонок
        select_parts = ['id']
        where_parts = []
        
        if 'date_of_birth' in existing_columns:
            select_parts.append('date_of_birth')
            where_parts.append('date_of_birth IS NOT NULL')
        else:
            select_parts.append('NULL::date as date_of_birth')
        
        if 'show_birthday' in existing_columns:
            select_parts.append('show_birthday')
        else:
            select_parts.append('true as show_birthday')
        
        if 'avatar_url' in existing_columns:
            select_parts.append('avatar_url')
            where_parts.append('avatar_url IS NOT NULL')
        else:
            select_parts.append('NULL::varchar as avatar_url')
        
        select_parts.append('created_at')
        
        where_clause = ' OR '.join(where_parts) if where_parts else 'true'
        
        conn.execute(sa.text(f"""
            INSERT INTO user_profiles (user_id, date_of_birth, show_birthday, avatar_url, updated_at)
            SELECT {', '.join(select_parts)}
            FROM users
            WHERE {where_clause}
        """))
    
    # Удаляем поля из таблицы users, если они существуют
    if 'avatar_url' in existing_columns:
        op.drop_column('users', 'avatar_url')
    if 'show_birthday' in existing_columns:
        op.drop_column('users', 'show_birthday')
    if 'date_of_birth' in existing_columns:
        op.drop_column('users', 'date_of_birth')


def downgrade() -> None:
    # Возвращаем поля в таблицу users
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('show_birthday', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    
    # Переносим данные обратно из user_profiles в users
    op.execute("""
        UPDATE users u
        SET date_of_birth = up.date_of_birth,
            show_birthday = up.show_birthday,
            avatar_url = up.avatar_url
        FROM user_profiles up
        WHERE u.id = up.user_id
    """)
    
    # Удаляем таблицу user_profiles
    op.drop_table('user_profiles')
