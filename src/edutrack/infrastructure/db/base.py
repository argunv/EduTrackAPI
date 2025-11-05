import uuid
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import MetaData


class Base(DeclarativeBase):
    metadata = MetaData()

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore
        return cls.__name__.lower()

    @declared_attr
    def id(cls):
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID

        return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)





