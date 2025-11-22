from edutrack.infrastructure.repositories.sqlalchemy import SqlAlchemyUserRepository
from edutrack.infrastructure.services.security import create_access_token, verify_password
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


class AuthService:
    def __init__(self, session: AsyncSession):
        self.users = SqlAlchemyUserRepository(session)

    async def authenticate(self, email: str, password: str) -> str:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return create_access_token(str(user.id))
