"""Pet Nutrition Agent — LangGraph ReAct StateGraph(精简版)。

结构: agent_node ⇄ tool_node
- 入口直接进 agent_node(无独立分诊节点)
- 终止条件: final_response 被设置 / 达到 MAX_ITERATIONS / 检测到工具循环

Checkpointer 由调用方注入(production 走 AsyncSqliteSaver,测试走 MemorySaver),
本模块不持有任何 DB connection — 全部生命周期管理交给 FastAPI lifespan。
"""
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from app.agent.prompts.system import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools.registry import ALL_TOOLS, TOOL_BY_NAME
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="agent")

MAX_ITERATIONS = 8
LOOP_DETECTION_WINDOW = 2

# 长对话压缩阈值:超过 SUMMARIZE_THRESHOLD 条消息时,
# 把前面的合并成 1 条 system 摘要,保留最后 SUMMARIZE_KEEP_RECENT 条原样。
SUMMARIZE_THRESHOLD = 30
SUMMARIZE_KEEP_RECENT = 10


def _build_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
        streaming=True,
        # DeepSeek V4-Flash 默认开 thinking 模式,会把大量 token 花在内部推理上。
        # 营养评估 + 工具决策是模式化任务,不需要数学竞赛级推理,关掉以省 token + 加快首 token。
        extra_body={"enable_thinking": False},
    )


def _build_summarizer_llm():
    """专用于历史压缩的小温度 LLM,不绑工具、不流式 — 一次性出摘要文本。"""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3,
        streaming=False,
        extra_body={"enable_thinking": False},
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
    # 同时剥 AI 的 tool_calls 消息 + 对应的 ToolMessage 响应。
    # 只剥前者会留下"孤儿 tool 消息",DeepSeek 严格校验会报
    # "Messages with role 'tool' must be a response to a preceding tool_calls"。
    safe_msgs = [
        m for m in messages
        if not (hasattr(m, "tool_calls") and m.tool_calls)
        and not isinstance(m, ToolMessage)
    ]
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


def _stringify_messages_for_summary(messages: list) -> str:
    """把 LangChain 消息对象拍平成可读字符串(给 summarizer LLM 看)。"""
    parts = []
    for m in messages:
        if isinstance(m, HumanMessage):
            role = "用户"
        elif isinstance(m, AIMessage):
            role = "助手"
        elif isinstance(m, ToolMessage):
            role = "工具"
        elif isinstance(m, SystemMessage):
            role = "系统"
        else:
            role = "其他"
        content = getattr(m, "content", "") or ""
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False)[:200]
        elif len(content) > 400:
            content = content[:400] + "..."
        # AI tool_calls 也展示一下,让摘要包含"调了哪个工具"
        tcs = getattr(m, "tool_calls", None) or []
        if tcs:
            tc_names = ", ".join(tc.get("name", "?") for tc in tcs)
            content = (content + f" [调用工具: {tc_names}]").strip()
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


def _maybe_summarize_history(messages: list) -> list:
    """长对话压缩 — 仅在 messages 长度超过阈值时调一次 LLM 把老消息合并。

    返回的列表 = [1 条 SystemMessage 摘要] + [最近 SUMMARIZE_KEEP_RECENT 条原样]。
    短对话直接原样返回,不消耗任何 token。
    """
    if len(messages) <= SUMMARIZE_THRESHOLD:
        return messages

    to_summarize = messages[:-SUMMARIZE_KEEP_RECENT]
    keep_recent = messages[-SUMMARIZE_KEEP_RECENT:]
    logger.info(
        f"Summarizing {len(to_summarize)} old messages, keeping {len(keep_recent)} recent"
    )

    summarizer = _build_summarizer_llm()
    summary_request = [
        {
            "role": "system",
            "content": (
                "你是对话压缩器。把下面的对话历史压成不超过 300 字的中文摘要。\n"
                "**必须保留**:宠物档案要点(名字/体重/疾病/过敏)、所有评估结论"
                "(critical/warning findings)、给出过的关键建议、用户提到的约束/偏好。\n"
                "**可省略**:寒暄、思考链、工具调用的中间参数细节。\n"
                "输出格式:直接给摘要正文,不要前缀'摘要:'之类的字样。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"以下是 {len(to_summarize)} 条早期对话:\n\n"
                f"{_stringify_messages_for_summary(to_summarize)}"
            ),
        },
    ]
    try:
        summary_text = summarizer.invoke(summary_request).content
    except Exception as e:
        # 总结失败时降级:截掉老消息,保留 recent,避免堵塞主流程
        logger.warning(f"History summarization failed, falling back to truncation: {e}")
        return keep_recent

    summary_msg = SystemMessage(
        content=f"【早期对话压缩摘要(原 {len(to_summarize)} 条已合并)】\n{summary_text}"
    )
    return [summary_msg, *keep_recent]


def _sanitize_message_history(messages: list) -> list:
    """剔除孤儿 ToolMessage(没有匹配的前置 tool_call_id)。

    Checkpoint state 在历史故障路径里可能留下"孤儿":比如旧版 _force_final_answer
    剥了 AI 的 tool_calls 但保留了 ToolMessage 响应。DeepSeek 严格校验消息顺序,
    会直接报 400。本函数在 agent_node 入口做兜底,保证发给 LLM 的历史干净。
    """
    valid_call_ids: set[str] = set()
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                if tc_id:
                    valid_call_ids.add(tc_id)

    cleaned: list = []
    for m in messages:
        if isinstance(m, ToolMessage):
            if getattr(m, "tool_call_id", None) in valid_call_ids:
                cleaned.append(m)
            # else 孤儿,丢弃
        else:
            cleaned.append(m)
    return cleaned


def agent_node(state: AgentState) -> dict:
    """Agent 决策节点:LLM 看到上下文,决定调下一工具或终结。"""
    llm = _build_llm().bind_tools(ALL_TOOLS)
    # 顺序:先压缩老消息(节省 token + 防上下文爆炸),再 sanitize(防止压缩边界切到 tool 对)
    raw_messages = state.get("messages", [])
    messages = _maybe_summarize_history(raw_messages)
    messages = _sanitize_message_history(messages)
    iteration = state.get("iteration_count", 0)

    if _detect_loop(messages):
        logger.warning(f"Loop detected at iteration {iteration}, forcing final answer")
        return _force_final_answer(messages, llm)

    if iteration >= MAX_ITERATIONS:
        logger.warning(f"Max iterations reached ({MAX_ITERATIONS}), forcing final answer")
        return _force_final_answer(messages, llm)

    full_messages: list = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)

    # 跨 thread 持久化的宠物档案(API 在 chat 启动时预查 DB 注入)。
    # 让 Agent 直接知道用户已有哪些宠物,不必每轮重新追问。
    user_pets = state.get("user_pets") or []
    if user_pets:
        full_messages.append({
            "role": "system",
            "content": (
                f"该用户已保存的宠物档案 (共 {len(user_pets)} 只): "
                f"{json.dumps(user_pets, ensure_ascii=False)}。"
                "如用户提到具体名字,直接用这里的档案,不要重复追问;"
                "如档案有更新(体重变化、新发现疾病等),用 save_pet_profile 工具覆盖。"
            ),
        })

    # 跨 thread 的用户长期记忆(偏好、约束、兽医指示等)
    user_memories = state.get("user_memories") or []
    if user_memories:
        full_messages.append({
            "role": "system",
            "content": (
                f"该用户的长期记忆 (共 {len(user_memories)} 条): "
                f"{json.dumps(user_memories, ensure_ascii=False)}。"
                "在给建议时把这些事实纳入考虑(如预算限制、过敏严重程度、兽医叮嘱);"
                "对话中若发现新的值得长期记住的事实,用 remember 工具保存。"
            ),
        })

    if state.get("pet_profile"):
        full_messages.append({
            "role": "system",
            "content": f"本轮对话累积的宠物档案: {json.dumps(state['pet_profile'], ensure_ascii=False)}",
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


async def tool_node(state: AgentState, config: RunnableConfig) -> dict:
    """工具执行节点:执行 LLM 选中的工具,merge 结果到 state。

    config 透传给所有工具(save_pet_profile / list_pets 等通过 config.configurable.user_id
    拿用户身份);LLM 看不到 config 这一层,只组装业务参数。
    """
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
            result = await tool.ainvoke(tool_args, config=config)
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


def build_graph(checkpointer: BaseCheckpointSaver):
    """编译并返回 ReAct graph;checkpointer 由调用方注入。

    生产用 AsyncSqliteSaver(由 main.py lifespan 在异步上下文里管理),
    测试用 MemorySaver。本函数本身保持同步 — 仅做图结构编译。
    """
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_conditional_edges("tools", after_tools, {"agent": "agent", "end": END})
    return graph.compile(checkpointer=checkpointer)
