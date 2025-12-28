"""add multiple roles support

Revision ID: 0002_add_multiple_roles
Revises: 0001_initial
Create Date: 2025-12-28 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_add_multiple_roles"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем новый enum с расширенными ролями (если еще не существует)
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole_new')")
    ).scalar()
    
    userrole_new = postgresql.ENUM(
        "student", "guardian", "teacher", "class_teacher", "subject_teacher",
        "head_teacher", "director", "deputy_director", "methodist", "scheduler",
        "psychologist", "librarian", "admin", "secretary",
        name="userrole_new",
        create_type=False,  # Не создаем автоматически, делаем вручную
    )
    
    if not result:
        userrole_new.create(conn, checkfirst=True)
    
    # Проверяем, существует ли таблица user_role_assignments
    inspector = sa.inspect(conn)
    has_table = "user_role_assignments" in inspector.get_table_names()
    
    if not has_table:
        # Создаем таблицу для назначения ролей
        op.create_table(
            "user_role_assignments",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("role", userrole_new, primary_key=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        )
    
        # Переносим данные из users.role в user_role_assignments (если поле role еще существует)
        inspector = sa.inspect(conn)
        users_columns = [col["name"] for col in inspector.get_columns("users")]
        
        if "role" in users_columns:
            # Проверяем, есть ли уже данные в user_role_assignments
            count_result = conn.execute(
                sa.text("SELECT COUNT(*) FROM user_role_assignments")
            ).scalar()
            
            if count_result == 0:
                # Переносим данные из users.role в user_role_assignments
                # Маппинг старых ролей на новые (для совместимости)
                op.execute("""
                    INSERT INTO user_role_assignments (user_id, role, assigned_at)
                    SELECT 
                        id, 
                        CASE 
                            WHEN role::text = 'student' THEN 'student'::userrole_new
                            WHEN role::text = 'guardian' THEN 'guardian'::userrole_new
                            WHEN role::text = 'teacher' THEN 'teacher'::userrole_new
                            WHEN role::text = 'admin' THEN 'admin'::userrole_new
                            ELSE 'admin'::userrole_new
                        END,
                        created_at
                    FROM users
                    WHERE role IS NOT NULL
                """)
            
            # Удаляем старое поле role из users
            op.drop_column("users", "role")
        
        # Удаляем старый enum (если он больше не используется)
        old_enum_exists = conn.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole')")
        ).scalar()
        
        if old_enum_exists:
            op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    # Восстанавливаем старый enum
    userrole_old = postgresql.ENUM("student", "teacher", "guardian", "admin", name="userrole", create_type=True)
    userrole_old.create(op.get_bind(), checkfirst=True)
    
    # Восстанавливаем старое поле role
    op.add_column(
        "users",
        sa.Column("role", userrole_old, nullable=True),
    )
    
    # Переносим данные обратно (берем первую роль из назначений, маппим на старые роли)
    op.execute("""
        UPDATE users u
        SET role = (
            SELECT CASE 
                WHEN ura.role::text IN ('student') THEN 'student'::userrole
                WHEN ura.role::text IN ('guardian') THEN 'guardian'::userrole
                WHEN ura.role::text IN ('teacher', 'class_teacher', 'subject_teacher', 'head_teacher', 'director', 'deputy_director', 'methodist', 'scheduler', 'psychologist', 'librarian', 'secretary') THEN 'teacher'::userrole
                WHEN ura.role::text IN ('admin') THEN 'admin'::userrole
                ELSE 'admin'::userrole
            END
            FROM user_role_assignments ura
            WHERE ura.user_id = u.id
            ORDER BY ura.assigned_at
            LIMIT 1
        )
    """)
    
    # Делаем поле NOT NULL
    op.alter_column("users", "role", nullable=False)
    
    # Удаляем таблицу назначений ролей
    op.drop_table("user_role_assignments")
    
    # Удаляем новый enum
    op.execute("DROP TYPE IF EXISTS userrole_new")
