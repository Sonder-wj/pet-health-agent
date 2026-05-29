"""Pet Health Agent — FastAPI 入口"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.core.database import init_db
from app.core.logger import get_logger
from app.core.middleware import LoggingMiddleware

logger = get_logger(service="main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Pet Health Agent starting up...")
    await init_db()
    logger.info("Database tables created")
    yield
    logger.info("Pet Health Agent shutting down...")


app = FastAPI(
    title="Pet Health Agent",
    description="AI 宠物健康问诊 Agent — LangGraph ReAct + GPT-4o",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pet-health-agent"}


# SPA fallback: serve index.html for all non-API routes
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    path = Path("static") / full_path
    if path.is_file():
        return FileResponse(str(path))
    return FileResponse("static/index.html")
