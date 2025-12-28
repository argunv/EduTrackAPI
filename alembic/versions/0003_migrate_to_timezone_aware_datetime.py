"""migrate to timezone aware datetime

Revision ID: 0003_timezone_aware
Revises: 0002_add_multiple_roles
Create Date: 2025-12-28 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_timezone_aware"
down_revision = "0002_add_multiple_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Список всех таблиц и колонок с DateTime, которые нужно мигрировать
    datetime_columns = [
        ("user_role_assignments", "assigned_at"),
        ("users", "created_at"),
        ("schools", "created_at"),
        ("classes", "created_at"),
        ("subjects", "created_at"),
        ("students", "enrolled_at"),
        ("teachers", "hired_at"),
        ("lessons", "created_at"),
        ("lessons", "start_at"),
        ("lessons", "end_at"),
        ("grades", "created_at"),
        ("attendance", "noted_at"),
        ("homework_submissions", "submitted_at"),
        ("messages", "created_at"),
        ("email_outbox", "created_at"),
        ("email_outbox", "sent_at"),
    ]
    
    # Мигрируем каждую колонку с TIMESTAMP на TIMESTAMP WITH TIME ZONE
    for table_name, column_name in datetime_columns:
        # Проверяем, существует ли таблица и колонка
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        
        if table_name not in inspector.get_table_names():
            continue
        
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        if column_name not in columns:
            continue
        
        # Изменяем тип колонки на TIMESTAMP WITH TIME ZONE
        # PostgreSQL автоматически конвертирует существующие значения
        op.execute(
            sa.text(f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {column_name} TYPE TIMESTAMP WITH TIME ZONE
                USING {column_name} AT TIME ZONE 'UTC'
            """)
        )


def downgrade() -> None:
    # Обратная миграция: конвертируем обратно в TIMESTAMP без timezone
    datetime_columns = [
        ("user_role_assignments", "assigned_at"),
        ("users", "created_at"),
        ("schools", "created_at"),
        ("classes", "created_at"),
        ("subjects", "created_at"),
        ("students", "enrolled_at"),
        ("teachers", "hired_at"),
        ("lessons", "created_at"),
        ("lessons", "start_at"),
        ("lessons", "end_at"),
        ("grades", "created_at"),
        ("attendance", "noted_at"),
        ("homework_submissions", "submitted_at"),
        ("messages", "created_at"),
        ("email_outbox", "created_at"),
        ("email_outbox", "sent_at"),
    ]
    
    for table_name, column_name in datetime_columns:
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        
        if table_name not in inspector.get_table_names():
            continue
        
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        if column_name not in columns:
            continue
        
        # Конвертируем обратно в TIMESTAMP без timezone
        op.execute(
            sa.text(f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {column_name} TYPE TIMESTAMP
                USING {column_name} AT TIME ZONE 'UTC'
            """)
        )
