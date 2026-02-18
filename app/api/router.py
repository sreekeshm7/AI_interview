from fastapi import APIRouter

from app.api.routes.collector import router as collector_router
from app.api.routes.interviews import router as interviews_router
from app.api.routes.transcripts import router as transcripts_router
from app.api.routes.voice import router as voice_router

api_router = APIRouter()
api_router.include_router(collector_router)
api_router.include_router(interviews_router)
api_router.include_router(transcripts_router)
api_router.include_router(voice_router)
