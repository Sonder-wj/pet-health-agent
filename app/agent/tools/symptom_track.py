"""症状追踪工具 — 跨天记录和趋势对比"""
from datetime import datetime

from langchain_core.tools import tool
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.symptom_log import SymptomLog


@tool
async def track_symptoms(
    action: str,
    thread_id: str = "",
    note: str = "",
) -> dict:
    """记录或查询宠物症状变化，用于跨天趋势对比。

    Args:
        action: 操作类型 — "log" 记录当前症状, "history" 查询历史记录
        thread_id: 对话 thread_id（必填，用于关联记录）
        note: 症状备注（action="log" 时必填），如"今天比昨天吐得少了"
    """
    if action == "log":
        if not note:
            return {"status": "error", "message": "记录症状时 note 不能为空"}
        return await _log_symptom(thread_id, note)
    elif action == "history":
        return await _get_history(thread_id)
    else:
        return {"status": "error", "message": f"未知操作: {action}，支持 log/history"}


async def _log_symptom(thread_id: str, note: str) -> dict:
    try:
        async with AsyncSessionLocal() as session:
            log = SymptomLog(
                thread_id=thread_id,
                note=note,
            )
            session.add(log)
            await session.commit()
            return {
                "status": "logged",
                "thread_id": thread_id,
                "note": note,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        return {"status": "error", "message": str(e), "fallback": "症状已记录在本地会话中"}


async def _get_history(thread_id: str) -> dict:
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SymptomLog)
                .where(SymptomLog.thread_id == thread_id)
                .order_by(SymptomLog.created_at)
                .limit(10)
            )
            logs = result.scalars().all()
            history = [
                {
                    "id": log.id,
                    "note": log.note,
                    "time": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
            return {
                "status": "ok",
                "thread_id": thread_id,
                "total": len(history),
                "history": history,
            }
    except Exception:
        return {"status": "error", "message": "数据库不可用，无法查询历史记录", "history": []}
