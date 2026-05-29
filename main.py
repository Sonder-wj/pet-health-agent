"""Pet Nutrition Agent — FastAPI 入口。

LangGraph 的 AsyncSqliteSaver 走异步上下文管理(async with),
所以由 lifespan 持有 saver 的生命周期,编译好的 graph 挂在 app.state 上。
路由通过 request.app.state.agent_graph 取实例。
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.graph import build_graph
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.core.config import settings
from app.core.database import init_db
from app.core.logger import get_logger
from app.core.middleware import LoggingMiddleware

logger = get_logger(service="main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Pet Nutrition Agent starting up...")

    # MySQL 持久化是 best-effort —— 连不上只 warn 不阻止启动。
    try:
        await init_db()
        logger.info("Database tables ready")
    except Exception as e:
        logger.warning(f"Database unavailable, history persistence disabled: {e}")

    # LangGraph 异步 checkpoint —— from_conn_string 是 async context manager,
    # 用它包住整个 app 生命周期,saver 进出由 langgraph 自己管。
    async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB_PATH) as saver:
        app.state.agent_graph = build_graph(saver)
        logger.info(f"Agent graph compiled with AsyncSqliteSaver({settings.CHECKPOINT_DB_PATH})")
        yield

    logger.info("Pet Nutrition Agent shutting down...")


app = FastAPI(
    title="Pet Nutrition Agent",
    description="AI 宠物营养评估管家 — LangGraph ReAct + 确定性营养引擎",
    version="0.2.0",
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
    return {"status": "ok", "service": "pet-nutrition-agent"}


# SPA fallback: serve index.html for all non-API routes
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    path = Path("static") / full_path
    if path.is_file():
        return FileResponse(str(path))
    return FileResponse("static/index.html")
