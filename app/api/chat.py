"""Pet Health Agent — Chat API (SSE)"""
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select

from app.agent.graph import agent_graph
from app.core.database import AsyncSessionLocal
from app.core.deps import get_current_user
from app.core.logger import get_logger
from app.models import Conversation, Message
from app.models.user import User

router = APIRouter()
logger = get_logger(service="api")


def _build_initial_state(
    query: str, image_path: str | None, pet_profile: dict | None
) -> dict:
    content_parts = []
    if image_path:
        ext = Path(image_path).suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
        mime_type = mime_map.get(ext, "image/jpeg")
        import base64
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{img_b64}"},
        })
        content_parts.append({"type": "text", "text": query})
    else:
        content_parts.append({"type": "text", "text": query})

    user_message = {
        "role": "user",
        "content": content_parts if len(content_parts) > 1 else query,
    }

    return {
        "messages": [user_message],
        "pet_profile": pet_profile or {},
        "collected_symptoms": [],
        "tool_results": {},
        "triage_level": None,
        "pending_question": None,
        "awaiting_user_input": False,
        "visit_summary": None,
        "image_path": image_path,
        "iteration_count": 0,
        "final_response": None,
        "already_triaged": False,
        "symptom_history": [],
    }


async def _save_chat_history(
    thread_id: str, user_query: str, assistant_content: str, title: str = "", user_id: int = 1
) -> None:
    """持久化对话记录到 MySQL。失败时静默跳过，不影响主流程。"""
    try:
        async with AsyncSessionLocal() as session:
            # 查找或创建对话
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

            # 保存用户消息
            user_msg = Message(
                conversation_id=conv.id,
                sender="user",
                content=user_query[:5000],
                message_type="text",
            )
            session.add(user_msg)

            # 保存助手回复
            if assistant_content:
                assistant_msg = Message(
                    conversation_id=conv.id,
                    sender="assistant",
                    content=assistant_content[:5000],
                    message_type="text",
                )
                session.add(assistant_msg)

            await session.commit()
    except Exception:
        logger.warning(f"Failed to persist chat history: {traceback.format_exc(limit=1)}")


async def _stream_agent_response(
    initial_state: dict, thread_config: dict
):
    """核心流式逻辑：通过 astream_events 逐 token 推送，并发送 tool_call/tool_result 事件。"""
    try:
        async for event in agent_graph.astream_events(  # type: ignore[attr-defined]
            initial_state, thread_config, version="v2"
        ):
            kind = event.get("event", "")

            # LLM 逐 token 输出
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text = chunk.content
                    if isinstance(text, str):
                        yield f"data: {json.dumps({'type': 'token', 'content': text}, ensure_ascii=False)}\n\n"

            # 工具被调用
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                # 序列化工具参数（过滤不可序列化的对象）
                safe_input = {}
                for k, v in tool_input.items():
                    try:
                        json.dumps(v)
                        safe_input[k] = v
                    except (TypeError, ValueError):
                        safe_input[k] = str(v)
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'args': safe_input}, ensure_ascii=False)}\n\n"

            # 工具返回结果
            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = event.get("data", {}).get("output")
                summary = _summarize_tool_output(tool_name, output)
                yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'summary': summary}, ensure_ascii=False)}\n\n"

        # 流结束后获取最终状态
        final_state = agent_graph.get_state(thread_config)  # type: ignore[attr-defined]
        state_values = final_state.values if final_state else {}

        if state_values.get("triage_level"):
            yield f"data: {json.dumps({'type': 'triage', 'level': state_values['triage_level']}, ensure_ascii=False)}\n\n"

        if state_values.get("awaiting_user_input") and state_values.get("pending_question"):
            yield f"data: {json.dumps({'type': 'question', 'message': state_values['pending_question']}, ensure_ascii=False)}\n\n"
        elif state_values.get("visit_summary"):
            yield f"data: {json.dumps({'type': 'visit_summary', 'message': state_values['visit_summary']}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception:
        logger.error(f"Agent stream error: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': '系统异常，请稍后再试'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _summarize_tool_output(tool_name: str, output) -> str:
    """提取工具输出的关键摘要，避免向客户端推送过长内容。"""
    if not output:
        return ""

    if isinstance(output, str):
        return output[:300] + ("..." if len(output) > 300 else "")
    if isinstance(output, dict):
        return output.get("question") or \
               output.get("findings") or \
               output.get("summary_markdown") or \
               output.get("message") or \
               output.get("response") or \
               str(output)[:300]
    if isinstance(output, list):
        return str(output[:5])
    return str(output)[:300]


@router.post("/chat")
async def chat(
    query: str = Form(...),
    session_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User | None = Depends(get_current_user),
):
    image_path = None
    if image and image.filename:
        img_dir = Path("uploads/images")
        img_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = f"{ts}_{image.filename}"
        image_path = img_dir / safe_name
        content = await image.read()
        with open(image_path, "wb") as f:
            f.write(content)
        logger.info(f"Image saved: {image_path}")

    thread_id = session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    thread_config = {"configurable": {"thread_id": thread_id}}
    pet_profile = {}
    if current_user and current_user.id:
        pet_profile = {"name": current_user.username}
    initial_state = _build_initial_state(
        query, str(image_path) if image_path else None, pet_profile
    )

    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'msg': '小宠正在思考...'})}\n\n"

        async for chunk in _stream_agent_response(initial_state, thread_config):
            yield chunk

        # 持久化：收集助手回复内容并保存
        # 从最终状态提取助手内容
        assistant_content = ""
        final_state = agent_graph.get_state(thread_config)  # type: ignore[attr-defined]
        if final_state and final_state.values:
            sv = final_state.values
            if sv.get("visit_summary"):
                assistant_content = sv["visit_summary"]
            elif sv.get("pending_question"):
                assistant_content = f"[追问] {sv['pending_question']}"
            elif sv.get("final_response"):
                assistant_content = sv["final_response"]
            else:
                msgs = sv.get("messages", [])
                for m in reversed(msgs):
                    content = getattr(m, "content", "") if hasattr(m, "content") else str(m)
                    if content and not (hasattr(m, "tool_calls") and m.tool_calls):
                        assistant_content = content[:5000]
                        break

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
    session_id: str,
    query: str = Form(...),
    current_user: User | None = Depends(get_current_user),
):
    thread_config = {"configurable": {"thread_id": session_id}}

    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'msg': '小宠正在思考...'})}\n\n"

        resume_state = {
            "messages": [{"role": "user", "content": query}],
            "awaiting_user_input": False,
            "already_triaged": True,  # 追问回复不重新分诊
        }

        async for chunk in _stream_agent_response(resume_state, thread_config):
            yield chunk

        # 持久化用户回答
        assistant_content = ""
        final_state = agent_graph.get_state(thread_config)  # type: ignore[attr-defined]
        if final_state and final_state.values:
            sv = final_state.values
            if sv.get("visit_summary"):
                assistant_content = sv["visit_summary"]
            elif sv.get("pending_question"):
                assistant_content = f"[追问] {sv['pending_question']}"
            elif sv.get("final_response"):
                assistant_content = sv["final_response"]
            else:
                msgs = sv.get("messages", [])
                for m in reversed(msgs):
                    content = getattr(m, "content", "") if hasattr(m, "content") else str(m)
                    if content and not (hasattr(m, "tool_calls") and m.tool_calls):
                        assistant_content = content[:5000]
                        break

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
    """获取历史对话列表"""
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
    """获取指定对话的消息记录"""
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
