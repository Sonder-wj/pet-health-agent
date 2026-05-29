"""Pet Nutrition Agent — LangGraph ReAct StateGraph(精简版)。

结构: agent_node ⇄ tool_node
- 入口直接进 agent_node(无独立分诊节点)
- 终止条件: final_response 被设置 / 达到 MAX_ITERATIONS / 检测到工具循环
"""
import json
import sqlite3

from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from app.agent.prompts.system import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools.registry import ALL_TOOLS, TOOL_BY_NAME
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
    safe_msgs = [m for m in messages if not (hasattr(m, "tool_calls") and m.tool_calls)]
    system_msg = {
        "role": "system",
        "content": (
            "请基于已有的信息,给用户输出一份简短的中文营养评估总结(无需再调工具)。"
            "包含:能量平衡、关键 findings(若有)、给主人的两三条建议、必要的兽医提醒。"
        ),
    }
    msgs = [system_msg] + safe_msgs
    response = llm.invoke(msgs)
    return {"messages": [response], "iteration_count": MAX_ITERATIONS}


def agent_node(state: AgentState) -> dict:
    """Agent 决策节点:LLM 看到上下文,决定调下一工具或终结。"""
    llm = _build_llm().bind_tools(ALL_TOOLS)
    messages = state.get("messages", [])
    iteration = state.get("iteration_count", 0)

    if _detect_loop(messages):
        logger.warning(f"Loop detected at iteration {iteration}, forcing final answer")
        return _force_final_answer(messages, llm)

    if iteration >= MAX_ITERATIONS:
        logger.warning(f"Max iterations reached ({MAX_ITERATIONS}), forcing final answer")
        return _force_final_answer(messages, llm)

    full_messages: list = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)

    if state.get("pet_profile"):
        full_messages.append({
            "role": "system",
            "content": f"当前已收集的宠物档案: {json.dumps(state['pet_profile'], ensure_ascii=False)}",
        })

    if state.get("assessment"):
        full_messages.append({
            "role": "system",
            "content": (
                "engine.assess() 已返回评估结果(供你渲染最终报告): "
                f"{json.dumps(state['assessment'], ensure_ascii=False)}"
            ),
        })

    if state.get("label_image_path"):
        full_messages.append({
            "role": "system",
            "content": (
                f"用户上传了商品粮包装照(路径: {state['label_image_path']}),"
                "你可以调用 extract_label_nutrition 工具解析其保证成分分析。"
            ),
        })

    response = llm.invoke(full_messages)
    return {"messages": [response], "iteration_count": iteration + 1}


async def tool_node(state: AgentState) -> dict:
    """工具执行节点:执行 LLM 选中的工具,merge 结果到 state。"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    if not tool_calls:
        return {}

    results: list = []
    merged: dict = {
        "tool_results": dict(state.get("tool_results", {})),
    }

    for tc in tool_calls:
        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {})
        tool_call_id = tc.get("id", "")

        tool = TOOL_BY_NAME.get(tool_name)
        if tool is None:
            results.append(ToolMessage(
                content=json.dumps({"error": f"Unknown tool: {tool_name}"}),
                tool_call_id=tool_call_id,
            ))
            continue

        try:
            result = await tool.ainvoke(tool_args)
        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}")
            result = {"error": str(e)}

        merged["tool_results"][tool_name] = result

        # 工具结果到 state 的副作用映射
        if tool_name == "assess_nutrition" and result.get("status") == "ok":
            merged["assessment"] = {
                "energy": result.get("energy"),
                "nutrients": result.get("nutrients"),
                "findings": result.get("findings"),
            }

        if tool_name == "final_answer":
            response_text = result.get("response", "")
            merged["final_response"] = response_text
            merged["report_md"] = response_text

        results.append(ToolMessage(
            content=json.dumps(result, ensure_ascii=False),
            tool_call_id=tool_call_id,
        ))

    merged["messages"] = results
    return merged


def should_continue(state: AgentState) -> str:
    if state.get("final_response"):
        return "end"
    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return "end"
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "end"


def after_tools(state: AgentState) -> str:
    if state.get("final_response"):
        return "end"
    return "agent"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_conditional_edges("tools", after_tools, {"agent": "agent", "end": END})

    conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(checkpointer=checkpointer)  # type: ignore[return-value]


agent_graph = build_graph()
