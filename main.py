from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401

app = FastAPI(title=settings.app_name)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://jobpylot.dev",
        "https://www.jobpylot.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    try:
        print(f"[startup] Database URL: {settings.database_url[:50]}..." if len(settings.database_url) > 50 else f"[startup] Database URL: {settings.database_url}")
        Base.metadata.create_all(bind=engine)
        print("[startup] Database tables created successfully")
    except Exception as exc:
        print(f"[startup-error] Database initialization failed: {exc}")
        import traceback
        traceback.print_exc()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    try:
        from app.db.session import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        return {"status": "error", "database": str(exc)}


app.include_router(api_router, prefix=settings.api_prefix)
