from datetime import datetime
from uuid import UUID

from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyNewsRepository
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


class NewsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.news = SqlAlchemyNewsRepository(session)

    async def create_news(
        self,
        school_id: UUID,
        author_id: UUID,
        title: str,
        content: str,
        preview_image_url: str | None = None,
        published_at: datetime | None = None,
    ):
        """Создать новость."""
        news_item = await self.news.create_news(
            school_id=school_id,
            author_id=author_id,
            title=title,
            content=content,
            preview_image_url=preview_image_url,
            published_at=published_at,
        )
        await self.session.commit()
        return news_item

    async def get_preview_list(self, school_id: UUID | None = None, limit: int = 20):
        """Получить список preview новостей."""
        news_items = await self.news.get_preview_list(school_id=school_id, limit=limit)
        return list(news_items)

    async def get_news(self, news_id: UUID):
        """Получить полную информацию о новости."""
        news_item = await self.news.get_by_id(news_id)
        if not news_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Новость не найдена")
        return news_item
