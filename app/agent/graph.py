"""Pet Health Agent — LangGraph ReAct StateGraph"""
import json
import sqlite3

from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from app.agent.prompts.system import ER_RESPONSE_PROMPT, SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools.registry import ALL_TOOLS, TOOL_BY_NAME
from app.agent.tools.triage import run_triage
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="agent")

MAX_ITERATIONS = 8
LOOP_DETECTION_WINDOW = 2


def _build_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
        streaming=True,
    )


async def triage_node(state: AgentState) -> dict:
    """独立分诊节点：每轮新对话强制优先执行，LLM 判断 + 关键词兜底。"""
    # 已分诊过则跳过（resume 场景）
    if state.get("triage_level") and state.get("already_triaged"):
        return {}

    messages = state.get("messages", [])
    if not messages:
        return {}

    user_msg = messages[0].get("content") if isinstance(messages[0], dict) else getattr(messages[0], "content", "")
    if isinstance(user_msg, list):
        # 多模态消息：[{type: "image_url", ...}, {type: "text", ...}]
        user_text = ""
        for part in user_msg:
            if isinstance(part, dict) and part.get("type") == "text":
                user_text += part.get("text", "") + " "
        user_msg = user_text.strip()

    profile = state.get("pet_profile", {})
    species = profile.get("species", "未提供")

    result = await run_triage(
        species=species,
        symptoms=str(user_msg or ""),
        additional_info=json.dumps(profile, ensure_ascii=False) if profile else "",
    )

    logger.info(f"Triage result: {result['level']} (source: {result.get('source', 'unknown')})")

    return {
        "triage_level": result["level"],
        "tool_results": {**state.get("tool_results", {}), "emergency_triage": result},
        "already_triaged": True,
    }


async def er_response_node(state: AgentState) -> dict:
    """急诊响应节点：当分诊结果为 er_now 时，直接生成就医劝导，不进入工具循环。"""
    llm = _build_llm()
    messages = state.get("messages", [])
    result = state.get("tool_results", {}).get("emergency_triage", {})

    system_msg = {"role": "system", "content": ER_RESPONSE_PROMPT}
    context = [
        system_msg,
        {"role": "system", "content": f"分诊结果：{json.dumps(result, ensure_ascii=False)}"},
    ]
    # 只传已有的用户消息
    user_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
    full = context + user_msgs

    response = await llm.ainvoke(full)
    return {
        "messages": [response],
        "final_response": response.content if hasattr(response, "content") else str(response),
    }


def agent_node(state: AgentState) -> dict:
    """Agent 决策节点：LLM 看到当前状态，决定调用哪个工具或输出最终答案。"""
    llm = _build_llm().bind_tools(ALL_TOOLS)

    messages = state.get("messages", [])
    iteration = state.get("iteration_count", 0)

    if _detect_loop(messages):
        logger.warning(f"Loop detected at iteration {iteration}, forcing final answer")
        return _force_final_answer(messages, llm)

    if iteration >= MAX_ITERATIONS:
        logger.warning(f"Max iterations reached ({MAX_ITERATIONS}), forcing final answer")
        return _force_final_answer(messages, llm)

    system_msg = {"role": "system", "content": SYSTEM_PROMPT}
    full_messages = [system_msg] + list(messages)

    if state.get("pet_profile"):
        profile_str = json.dumps(state["pet_profile"], ensure_ascii=False)
        full_messages.append({
            "role": "system",
            "content": f"当前宠物资讯：{profile_str}",
        })

    if state.get("collected_symptoms"):
        symptoms_str = json.dumps(state["collected_symptoms"], ensure_ascii=False)
        full_messages.append({
            "role": "system",
            "content": f"已收集的症状信息：{symptoms_str}",
        })

    if state.get("triage_level"):
        full_messages.append({
            "role": "system",
            "content": f"分诊等级：{state['triage_level']}。根据此等级调整回复策略。",
        })

    if state.get("symptom_history"):
        history_str = json.dumps(state["symptom_history"], ensure_ascii=False)
        full_messages.append({
            "role": "system",
            "content": f"用户的历史症状记录（可用于趋势对比）：{history_str}",
        })

    if state.get("image_path"):
        full_messages.append({
            "role": "system",
            "content": f"用户上传了宠物照片，路径: {state['image_path']}。你可以调用 analyze_pet_image 工具对此照片进行专业兽医影像分析。",
        })

    response = llm.invoke(full_messages)

    return {
        "messages": [response],
        "iteration_count": iteration + 1,
    }


def _detect_loop(messages: list) -> bool:
    recent_tool_calls = []
    for msg in reversed(messages):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            recent_tool_calls.append(msg.tool_calls[0]["name"])
        else:
            break

    if len(recent_tool_calls) >= LOOP_DETECTION_WINDOW:
        return len(set(recent_tool_calls[-LOOP_DETECTION_WINDOW:])) == 1

    return False


def _force_final_answer(messages: list, llm) -> dict:
    safe_msgs = []
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            continue
        safe_msgs.append(m)

    system_msg = {
        "role": "system",
        "content": "请基于已有的所有信息，给用户一个完整的总结回复。"
                   "包括：1.对宠物状况的评估 2.建议采取的行动 3.需要注意的观察指标。"
                   "直接输出文本，不要调用工具。",
    }
    msgs = [system_msg] + safe_msgs
    response = llm.invoke(msgs)
    return {"messages": [response], "iteration_count": MAX_ITERATIONS}


async def tool_node(state: AgentState) -> dict:
    """工具执行节点：执行 LLM 选中的工具，返回结果。"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)

    if not tool_calls:
        return {}

    results: list = []
    merged: dict = {
        "tool_results": dict(state.get("tool_results", {})),
        "collected_symptoms": list(state.get("collected_symptoms", [])),
    }

    for tc in tool_calls:
        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {})
        tool_call_id = tc.get("id", "")

        tool = TOOL_BY_NAME.get(tool_name)
        if tool is None:
            msg = ToolMessage(
                content=json.dumps({"error": f"Unknown tool: {tool_name}"}),
                tool_call_id=tool_call_id,
            )
            results.append(msg)
            continue

        if tool_name == "collect_symptoms":
            result = await tool.ainvoke(tool_args)
            if result.get("dimension"):
                merged["collected_symptoms"].append({
                    "dimension": result["dimension"],
                    "field": result["field"],
                    "value": tool_args.get("current_symptoms", ""),
                })
            results.append(ToolMessage(
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call_id,
            ))
            merged["pending_question"] = result.get("question")
            merged["awaiting_user_input"] = result.get("status") == "asking"
            continue

        try:
            result = await tool.ainvoke(tool_args)
        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}")
            result = {"error": str(e)}

        merged["tool_results"][tool_name] = result

        if tool_name == "generate_visit_summary" and "summary_markdown" in result:
            merged["visit_summary"] = result["summary_markdown"]

        if tool_name == "final_answer":
            merged["final_response"] = result.get("response", "")

        if tool_name == "track_symptoms":
            merged["symptom_history"] = result.get("history", [])

        results.append(ToolMessage(
            content=json.dumps(result, ensure_ascii=False),
            tool_call_id=tool_call_id,
        ))

    merged["messages"] = results
    return merged


def should_continue(state: AgentState) -> str:
    messages = state.get("messages", [])

    if state.get("final_response"):
        return "end"

    if state.get("awaiting_user_input"):
        return "end"

    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return "end"

    last_msg = messages[-1] if messages else None
    if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"

    return "end"


def after_tools(state: AgentState) -> str:
    """工具执行后的路由。

    如果工具阶段已经得出最终答复，或者收集症状后需要等待用户补充信息，
    就直接结束本轮，避免把未闭合的 tool_call 状态继续带回 agent 节点。
    """
    if state.get("final_response"):
      return "end"

    if state.get("awaiting_user_input"):
      return "end"

    return "agent"


def after_triage(state: AgentState) -> str:
    """分诊后路由：er_now 直接进入急诊响应，其余进入 Agent 工具循环。"""
    if state.get("triage_level") == "er_now":
        return "er_response"
    return "agent"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("triage", triage_node)
    graph.add_node("er_response", er_response_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("triage")

    graph.add_conditional_edges(
        "triage",
        after_triage,
        {"er_response": "er_response", "agent": "agent"},
    )
    graph.add_edge("er_response", END)

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_conditional_edges(
        "tools",
        after_tools,
        {"agent": "agent", "end": END},
    )

    conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(checkpointer=checkpointer)  # type: ignore[return-value]


agent_graph = build_graph()
