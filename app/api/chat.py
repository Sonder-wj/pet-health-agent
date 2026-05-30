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
from app.core.deps import require_user
from app.core.logger import get_logger
from app.models import Conversation, Message, Pet, UserMemory
from app.models.user import User

# 最多注入到 system prompt 的长期记忆条数(避免上下文爆炸)
MEMORY_INJECT_LIMIT = 50

router = APIRouter()
logger = get_logger(service="api")


async def _save_uploaded_image(image: UploadFile | None) -> str | None:
    """保存用户上传的标签图片到 uploads/images/,返回相对路径(None 表示无图)。"""
    if not image or not image.filename:
        return None
    img_dir = Path("uploads/images")
    img_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = f"{ts}_{image.filename}"
    saved_path = img_dir / safe_name
    content = await image.read()
    with open(saved_path, "wb") as f:
        f.write(content)
    logger.info(f"Label image saved: {saved_path}")
    return str(saved_path)


def _build_initial_state(
    query: str,
    label_image_path: str | None,
    pet_profile: dict | None,
    user_pets: list[dict] | None = None,
    user_memories: list[dict] | None = None,
) -> dict:
    """构造初始 AgentState。

    图片不嵌入消息内容 — 让 LLM 走 extract_label_nutrition 工具读盘,
    避免它自己"看"图后给出未经引擎核算的结论。
    """
    user_message = {"role": "user", "content": query}
    return {
        "messages": [user_message],
        "pet_profile": pet_profile or {},
        "user_pets": user_pets or [],
        "user_memories": user_memories or [],
        "diet_input": None,
        "label_image_path": label_image_path,
        "assessment": None,
        "tool_results": {},
        "iteration_count": 0,
        "final_response": None,
        "report_md": None,
    }


async def _fetch_user_pets(user_id: int) -> list[dict]:
    """读取该用户已保存的所有宠物档案,注入到 chat 起始 state。失败返回空列表。"""
    try:
        async with AsyncSessionLocal() as session:
            r = await session.execute(
                select(Pet).where(Pet.user_id == user_id).order_by(Pet.created_at)
            )
            return [p.to_dict() for p in r.scalars().all()]
    except Exception as e:
        logger.warning(f"_fetch_user_pets failed for user_id={user_id}: {e}")
        return []


async def _fetch_user_memories(user_id: int, limit: int = MEMORY_INJECT_LIMIT) -> list[dict]:
    """读取该用户的长期记忆,按时间倒序取最新 N 条。未来可换语义检索。"""
    try:
        async with AsyncSessionLocal() as session:
            r = await session.execute(
                select(UserMemory)
                .where(UserMemory.user_id == user_id)
                .order_by(UserMemory.created_at.desc())
                .limit(limit)
            )
            return [m.to_dict() for m in r.scalars().all()]
    except Exception as e:
        logger.warning(f"_fetch_user_memories failed for user_id={user_id}: {e}")
        return []


async def _save_chat_history(
    thread_id: str, user_query: str, assistant_content: str, user_id: int, title: str = "",
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
    query: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_user),
):
    agent_graph = request.app.state.agent_graph
    label_image_path = await _save_uploaded_image(image)

    # 用户仅上传图片不打字时,补一段默认提示让 Agent 知道该干啥
    # (FastAPI 把 multipart 里的空字段解析为 None,直接 Form(...) 会 422)
    if not query or not query.strip():
        query = "请帮我看看这张包装照的营养情况" if label_image_path else "你好"

    thread_id = session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    # user_id 注入 configurable,save_pet_profile / list_pets 等工具通过 RunnableConfig 读取
    thread_config = {"configurable": {"thread_id": thread_id, "user_id": current_user.id}}

    # 跨 thread 持久档案 + 长期记忆:Agent 启动时即拥有完整用户上下文
    user_pets = await _fetch_user_pets(current_user.id)
    user_memories = await _fetch_user_memories(current_user.id)
    initial_state = _build_initial_state(
        query, label_image_path, pet_profile=None,
        user_pets=user_pets, user_memories=user_memories,
    )

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
            user_id=current_user.id,
        )

    response = StreamingResponse(event_stream(), media_type="text/event-stream")
    response.headers["X-Session-ID"] = thread_id
    response.headers["Access-Control-Expose-Headers"] = "X-Session-ID"
    return response


@router.post("/chat/{session_id}/resume")
async def chat_resume(
    request: Request,
    session_id: str,
    query: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_user),
):
    """续接对话 — 不再有医疗向 'already_triaged' 短路,标准 ReAct 继续。

    支持多模态:续接时也可以上传商品粮包装照,Agent 会调 extract_label_nutrition。
    """
    agent_graph = request.app.state.agent_graph
    label_image_path = await _save_uploaded_image(image)
    thread_config = {"configurable": {"thread_id": session_id, "user_id": current_user.id}}

    # 同 chat():仅上图不打字时补默认提示
    if not query or not query.strip():
        query = "请帮我看看这张包装照的营养情况" if label_image_path else "继续"

    # 续接也刷新档案 + 记忆 — 用户可能在另一个 thread 新建了宠物或新记忆
    user_pets = await _fetch_user_pets(current_user.id)
    user_memories = await _fetch_user_memories(current_user.id)

    async def event_stream():
        yield f"data: {json.dumps({'type': 'thinking', 'msg': '小宠营养师正在评估...'})}\n\n"

        # 续接 state:label_image_path 仅在本轮上传时设置,
        # checkpointer 会把它合并进已存在的 thread state(messages 追加,其他字段覆盖)。
        #
        # 必须重置的完成信号字段:
        # - iteration_count: 累计后撞 MAX_ITERATIONS 会强制走 _force_final_answer
        # - final_response / report_md: should_continue 和 after_tools 第一行就检查它们,
        #   不清空的话 Agent 还没来得及说话,图就立即 end → 用户看到"不回话"
        #
        # 注:assessment 保留 — 多轮里用户可能问"为什么钙不够",需要前一轮的评估上下文。
        resume_state: dict = {
            "messages": [{"role": "user", "content": query}],
            "iteration_count": 0,
            "final_response": None,
            "report_md": None,
            "user_pets": user_pets,           # 每轮刷新,反映其他 thread 的最新档案
            "user_memories": user_memories,   # 同上,记忆也跨 thread 同步
        }
        if label_image_path:
            resume_state["label_image_path"] = label_image_path

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
            user_id=current_user.id,
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history")
async def list_conversations(
    limit: int = 20,
    current_user: User = Depends(require_user),
):
    user_id = current_user.id
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
async def get_conversation_messages(
    thread_id: str,
    current_user: User = Depends(require_user),
):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation).where(Conversation.thread_id == thread_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                return {"messages": [], "error": "对话不存在"}

            # 防越权:别的账号的 thread_id 直接拒
            if conv.user_id != current_user.id:
                return {"messages": [], "error": "无权访问此对话"}

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
