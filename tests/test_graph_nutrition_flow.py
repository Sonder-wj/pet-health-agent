"""营养 Agent graph 结构 + 路由逻辑 smoke 测试。

不发真实 LLM 请求 — 只验:
- graph 编译成功 + 节点拓扑正确
- 循环检测、终止条件、工具→agent 路由的纯函数行为
"""
import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import (
    MAX_ITERATIONS,
    _detect_loop,
    after_tools,
    build_graph,
    should_continue,
)
from app.agent.tools.registry import ALL_TOOLS, TOOL_BY_NAME


@pytest.fixture(scope="module")
def agent_graph():
    """编译一个测试用 graph(MemorySaver,完全同步,无 IO)。

    与 production main.py 的 AsyncSqliteSaver 路径解耦 — 测试不依赖
    aiosqlite/异步上下文,但走相同的 build_graph() 拓扑组装代码。
    """
    return build_graph(MemorySaver())

# ---------- 1. 拓扑结构 ----------

class TestGraphTopology:
    def test_graph_compiled(self, agent_graph):
        assert agent_graph is not None

    def test_nodes_simplified(self, agent_graph):
        # LangGraph compiled graph exposes nodes dict
        node_names = set(agent_graph.nodes.keys())
        assert "agent" in node_names
        assert "tools" in node_names
        # 旧医疗节点必须已删
        assert "triage" not in node_names
        assert "er_response" not in node_names

    def test_registry_has_5_nutrition_tools(self):
        assert len(ALL_TOOLS) == 5
        expected = {
            "extract_label_nutrition",
            "lookup_ingredient",
            "compute_energy_requirement",
            "assess_nutrition",
            "final_answer",
        }
        assert set(TOOL_BY_NAME.keys()) == expected


# ---------- 2. 循环检测 ----------

class _Tool:
    def __init__(self, name: str):
        self.tool_calls = [{"name": name}]


class _Text:
    def __init__(self, content: str = ""):
        self.tool_calls = None
        self.content = content


class TestLoopDetection:
    def test_empty_messages(self):
        assert _detect_loop([]) is False

    def test_single_tool_call(self):
        assert _detect_loop([_Tool("assess_nutrition")]) is False

    def test_two_different_tools(self):
        assert _detect_loop([_Tool("lookup_ingredient"), _Tool("assess_nutrition")]) is False

    def test_two_same_tools_consecutive(self):
        assert _detect_loop([_Tool("lookup_ingredient"), _Tool("lookup_ingredient")]) is True

    def test_text_between_tools_breaks_window(self):
        # _detect_loop 只看末尾连续工具调用,中间有文本会切断
        msgs = [_Tool("lookup_ingredient"), _Text("好的"), _Tool("lookup_ingredient")]
        assert _detect_loop(msgs) is False


# ---------- 3. should_continue ----------

class TestShouldContinue:
    def test_final_response_ends(self):
        assert should_continue({"messages": [], "final_response": "done", "iteration_count": 0}) == "end"

    def test_max_iterations_ends(self):
        assert should_continue({"messages": [], "iteration_count": MAX_ITERATIONS}) == "end"

    def test_no_tool_calls_ends(self):
        assert should_continue({"messages": [_Text("hi")], "iteration_count": 0}) == "end"

    def test_empty_messages_ends(self):
        assert should_continue({"messages": [], "iteration_count": 0}) == "end"

    def test_tool_call_routes_to_tools(self):
        state = {"messages": [_Tool("assess_nutrition")], "iteration_count": 0}
        assert should_continue(state) == "tools"

    def test_no_awaiting_user_input_field_check(self):
        """旧字段 awaiting_user_input 不应再影响路由。"""
        state = {"messages": [_Tool("assess_nutrition")], "iteration_count": 0,
                 "awaiting_user_input": True}  # 即使误传也应被忽略
        assert should_continue(state) == "tools"


# ---------- 4. after_tools ----------

class TestAfterTools:
    def test_final_response_ends(self):
        assert after_tools({"final_response": "done"}) == "end"

    def test_no_final_returns_to_agent(self):
        assert after_tools({"final_response": None}) == "agent"

    def test_empty_state_returns_to_agent(self):
        assert after_tools({}) == "agent"
