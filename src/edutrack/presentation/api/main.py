import logging
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from edutrack.presentation.api.routes.v1 import router as v1_router
from edutrack.application.health import check_health
from edutrack.infrastructure.db.database import get_session


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edutrack.api")


def create_app() -> FastAPI:
    app = FastAPI(title="EduTrack API", version="1.0.0")
    app.include_router(v1_router)

    @app.get("/health")
    async def health(session: AsyncSession = Depends(get_session)):
        status_data = await check_health(session)
        status_code = 200 if status_data["status"] == "ok" else 503
        return JSONResponse(content=status_data, status_code=status_code)

    return app


app = create_app()





