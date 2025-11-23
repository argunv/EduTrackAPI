import uuid

from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData()

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class AssociationBase(DeclarativeBase):
    """Базовый класс для связующих таблиц (many-to-many) без автоматического id.

    Используется для таблиц с составным первичным ключом.
    """
    metadata = Base.metadata  # Используем ту же metadata, что и Base
