"""Pet Nutrition Agent — Chat API (SSE)。"""
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select

from app.core.database import AsyncSessionLocal
from app.core.deps import get_current_user
from app.core.logger import get_logger
from app.models import Conversation, Message
from app.models.user import User

router = APIRouter()
logger = get_logger(service="api")


def _build_initial_state(
    query: str, label_image_path: str | None, pet_profile: dict | None
) -> dict:
    """构造初始 AgentState。

    图片不嵌入消息内容 — 让 LLM 走 extract_label_nutrition 工具读盘,
    避免它自己"看"图后给出未经引擎核算的结论。
    """
    user_message = {"role": "user", "content": query}
    return {
        "messages": [user_message],
        "pet_profile": pet_profile or {},
        "diet_input": None,
        "label_image_path": label_image_path,
        "assessment": None,
        "tool_results": {},
        "iteration_count": 0,
        "final_response": None,
        "report_md": None,
    }


async def _save_chat_history(
    thread_id: str, user_query: str, assistant_content: str, title: str = "", user_id: int = 1
) -> None:
    """持久化对话到 MySQL。失败静默,不阻塞主流程。"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.thread_id == thread_id)
            )
            conv = result.scalar_one_or_none()

            if conv is None:
                conv = Conversation(
                    thread_id=thread_id,
                    user_id=user_id,
                    title=title[:100] if title else "新对话",
                )
                session.add(conv)
                await session.flush()

            session.add(Message(
                conversation_id=conv.id, sender="user",
                content=user_query[:5000], message_type="text",
            ))
            if assistant_content:
                session.add(Message(
                    conversation_id=conv.id, sender="assistant",
                    content=assistant_content[:5000], message_type="text",
                ))
            await session.commit()
    except Exception:
        logger.warning(f"Failed to persist chat history: {traceback.format_exc(limit=1)}")


def _summarize_tool_output(tool_name: str, output) -> str:
    """提取工具输出关键摘要,避免向客户端推送过长内容。"""
    if not output:
        return ""
    if isinstance(output, str):
        return output[:300] + ("..." if len(output) > 300 else "")
    if isinstance(output, dict):
        # 新工具的关键字段优先
        if tool_name == "assess_nutrition" and output.get("status") == "ok":
            n_findings = len(output.get("findings", []))
            energy = output.get("energy", {})
            balance = energy.get("balance_pct")
            return f"评估完成: {n_findings} 项 findings, 能量偏差 {balance}%"
        if tool_name == "lookup_ingredient":
            return f"找到 {output.get('total', 0)} 项匹配 ({output.get('status', '')})"
        if tool_name == "compute_energy_requirement" and output.get("status") == "ok":
            return f"RER {output.get('rer')} / MER {output.get('mer')} kcal/day ({output.get('life_stage')})"
        if tool_name == "extract_label_nutrition" and output.get("status") == "ok":
            return f"标签解析成功: {output.get('label')}"
        return output.get("message") or output.get("response") or str(output)[:300]
    return str(output)[:300]


async def _stream_agent_response(agent_graph, initial_state: dict, thread_config: dict):
    """核心流:转发 LLM token、tool_call/tool_result;末尾发 assessment/report。"""
    try:
        async for event in agent_graph.astream_events(
            initial_state, thread_config, version="v2"
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text = chunk.content
                    if isinstance(text, str):
                        yield f"data: {json.dumps({'type': 'token', 'content': text}, ensure_ascii=False)}\n\n"

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                safe_input: dict = {}
                for k, v in tool_input.items():
                    try:
                        json.dumps(v)
                        safe_input[k] = v
                    except (TypeError, ValueError):
                        safe_input[k] = str(v)
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'args': safe_input}, ensure_ascii=False)}\n\n"

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = event.get("data", {}).get("output")
                summary = _summarize_tool_output(tool_name, output)
                yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'summary': summary}, ensure_ascii=False)}\n\n"

        # 流结束后:从最终 state 发结构化终态事件
        # AsyncSqliteSaver 走异步接口,SqliteSaver 走同步;这里只有异步用例。
        final_state = await agent_graph.aget_state(thread_config)
        sv = final_state.values if final_state else {}

        if sv.get("assessment"):
            yield f"data: {json.dumps({'type': 'assessment', 'data': sv['assessment']}, ensure_ascii=False)}\n\n"

        if sv.get("report_md"):
            yield f"data: {json.dumps({'type': 'report', 'markdown': sv['report_md']}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception:
        logger.error(f"Agent stream error: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': '系统异常,请稍后再试'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _extract_assistant_content(state_values: dict) -> str:
    """从最终 state 提取要落库的助手回复(优先 report_md / final_response)。"""
    if state_values.get("report_md"):
        return state_values["report_md"][:5000]
    if state_values.get("final_response"):
        return state_values["final_response"][:5000]
    for m in reversed(state_values.get("messages", [])):
        content = getattr(m, "content", "") if hasattr(m, "content") else str(m)
        if content and not (hasattr(m, "tool_calls") and m.tool_calls):
            return content[:5000]
    return ""


@router.post("/chat")
async def chat(
    request: Request,
    query: str = Form(...),
    session_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User | None = Depends(get_current_user),
):
    agent_graph = request.app.state.agent_graph
    label_image_path: str | None = None
    if image and image.filename:
        img_dir = Path("uploads/images")
        img_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = f"{ts}_{image.filename}"
        saved_path = img_dir / safe_name
        content = await image.read()
        with open(saved_path, "wb") as f:
            f.write(content)
        label_image_path = str(saved_path)
        logger.info(f"Label image saved: {label_image_path}")

    thread_id = session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    thread_config = {"configurable": {"thread_id": thread_id}}

    pet_profile: dict = {}
    if current_user and current_user.id:
        pet_profile = {"name": current_user.username}  # 仅作显示种子;真档案由 Agent 收集

    initial_state = _build_initial_state(query, label_image_path, pet_profile)

    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'msg': '小宠营养师正在评估...'})}\n\n"

        async for chunk in _stream_agent_response(agent_graph, initial_state, thread_config):
            yield chunk

        final_state = await agent_graph.aget_state(thread_config)
        sv = final_state.values if final_state else {}
        assistant_content = _extract_assistant_content(sv)

        await _save_chat_history(
            thread_id=thread_id,
            user_query=query,
            assistant_content=assistant_content,
            title=query[:100],
            user_id=current_user.id if current_user else 1,
        )

    response = StreamingResponse(event_stream(), media_type="text/event-stream")
    response.headers["X-Session-ID"] = thread_id
    response.headers["Access-Control-Expose-Headers"] = "X-Session-ID"
    return response


@router.post("/chat/{session_id}/resume")
async def chat_resume(
    request: Request,
    session_id: str,
    query: str = Form(...),
    current_user: User | None = Depends(get_current_user),
):
    """续接对话 — 不再有医疗向 'already_triaged' 短路,标准 ReAct 继续。"""
    agent_graph = request.app.state.agent_graph
    thread_config = {"configurable": {"thread_id": session_id}}

    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'msg': '小宠营养师正在评估...'})}\n\n"

        resume_state = {
            "messages": [{"role": "user", "content": query}],
        }

        async for chunk in _stream_agent_response(agent_graph, resume_state, thread_config):
            yield chunk

        final_state = await agent_graph.aget_state(thread_config)
        sv = final_state.values if final_state else {}
        assistant_content = _extract_assistant_content(sv)

        await _save_chat_history(
            thread_id=session_id,
            user_query=query,
            assistant_content=assistant_content,
            title="",
            user_id=current_user.id if current_user else 1,
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history")
async def list_conversations(
    limit: int = 20,
    current_user: User | None = Depends(get_current_user),
):
    user_id = current_user.id if current_user else 1
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
            )
            convs = result.scalars().all()
            return {
                "conversations": [
                    {
                        "id": c.id,
                        "thread_id": c.thread_id,
                        "title": c.title,
                        "status": c.status,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                    }
                    for c in convs
                ]
            }
    except Exception:
        logger.warning(f"Failed to list conversations: {traceback.format_exc(limit=1)}")
        return {"conversations": [], "error": "数据库不可用"}


@router.get("/history/{thread_id}")
async def get_conversation_messages(thread_id: str):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.thread_id == thread_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                return {"messages": [], "error": "对话不存在"}

            msg_result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
            )
            messages = msg_result.scalars().all()
            return {
                "thread_id": thread_id,
                "title": conv.title,
                "messages": [
                    {
                        "sender": m.sender,
                        "content": m.content,
                        "type": m.message_type,
                        "time": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in messages
                ],
            }
    except Exception:
        logger.warning(f"Failed to get messages: {traceback.format_exc(limit=1)}")
        return {"messages": [], "error": "数据库不可用"}
