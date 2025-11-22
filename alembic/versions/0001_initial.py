"""initial schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("student", "teacher", "guardian", "admin", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "schools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("school_id", "name", name="uq_class_school_name"),
    )

    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "teachers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("hired_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("school_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "guardians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
    )

    op.create_table(
        "student_guardians",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id"), primary_key=True),
        sa.Column("guardian_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("guardians.id"), primary_key=True),
    )

    op.create_table(
        "class_students",
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classes.id"), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id"), primary_key=True),
    )

    op.create_table(
        "class_subjects",
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classes.id"), primary_key=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id"), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachers.id")),
    )

    op.create_table(
        "lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachers.id"), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "grades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "attendance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("present", "absent", "late", name="attendancestatus"),
            nullable=False,
        ),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("noted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "homeworks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lessons.id"), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
    )

    op.create_table(
        "homework_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("homework_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("homeworks.id"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("grade", sa.Integer()),
        sa.UniqueConstraint("homework_id", "student_id", name="uq_homework_submission"),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "message_recipients",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id"), primary_key=True),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "email_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "failed", name="messagedeliverystatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("email_outbox")
    op.drop_table("message_recipients")
    op.drop_table("messages")
    op.drop_table("homework_submissions")
    op.drop_table("homeworks")
    op.drop_table("attendance")
    op.drop_table("grades")
    op.drop_table("lessons")
    op.drop_table("class_subjects")
    op.drop_table("class_students")
    op.drop_table("student_guardians")
    op.drop_table("guardians")
    op.drop_table("students")
    op.drop_table("teachers")
    op.drop_table("subjects")
    op.drop_table("classes")
    op.drop_table("schools")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS attendancestatus")
    op.execute("DROP TYPE IF EXISTS messagedeliverystatus")
