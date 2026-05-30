"""长对话压缩(_maybe_summarize_history)的纯函数测试 — 不发真实 LLM 请求。

只验:
- 短对话(<= 阈值)原样返回,不调 LLM
- 长对话(> 阈值)触发压缩,返回 [summary, *recent]
- summarizer 抛异常时降级为只保留 recent(不阻塞主流程)
- _stringify_messages_for_summary 能拍平各种消息类型
"""
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.graph import (
    SUMMARIZE_KEEP_RECENT,
    SUMMARIZE_THRESHOLD,
    _maybe_summarize_history,
    _stringify_messages_for_summary,
)


def _make_msgs(n: int) -> list:
    """生成 n 条简单的 user/ai 交替消息。"""
    out = []
    for i in range(n):
        if i % 2 == 0:
            out.append(HumanMessage(content=f"用户消息 {i}"))
        else:
            out.append(AIMessage(content=f"助手回复 {i}"))
    return out


class TestMaybeSummarize:
    def test_short_history_returns_unchanged(self):
        """阈值以下原样返回,LLM 不被调。"""
        msgs = _make_msgs(SUMMARIZE_THRESHOLD)  # exactly threshold
        with patch("app.agent.graph._build_summarizer_llm") as mock_llm:
            result = _maybe_summarize_history(msgs)
            assert result == msgs
            mock_llm.assert_not_called()

    def test_long_history_triggers_summary(self):
        """超阈值时调 summarizer,返回 [summary, ...recent]。"""
        msgs = _make_msgs(SUMMARIZE_THRESHOLD + 5)

        class _FakeResponse:
            content = "这是压缩后的中文摘要,保留了关键事实"

        class _FakeLLM:
            def invoke(self, _msgs):
                return _FakeResponse()

        with patch("app.agent.graph._build_summarizer_llm", return_value=_FakeLLM()):
            result = _maybe_summarize_history(msgs)

        # 期望:1 条 system 摘要 + 最近 SUMMARIZE_KEEP_RECENT 条
        assert len(result) == 1 + SUMMARIZE_KEEP_RECENT
        assert isinstance(result[0], SystemMessage)
        assert "压缩后的中文摘要" in result[0].content
        # 保留的尾部应该和原始 messages 的尾部一致
        assert result[1:] == msgs[-SUMMARIZE_KEEP_RECENT:]

    def test_summarizer_failure_falls_back_to_truncation(self):
        """LLM 总结失败时不应阻塞,降级为只保留 recent。"""
        msgs = _make_msgs(SUMMARIZE_THRESHOLD + 5)

        class _BrokenLLM:
            def invoke(self, _msgs):
                raise RuntimeError("LLM down")

        with patch("app.agent.graph._build_summarizer_llm", return_value=_BrokenLLM()):
            result = _maybe_summarize_history(msgs)

        assert len(result) == SUMMARIZE_KEEP_RECENT
        assert result == msgs[-SUMMARIZE_KEEP_RECENT:]


class TestStringifyMessages:
    def test_handles_all_message_types(self):
        """user / ai / tool / system 都该被识别成对应角色。"""
        msgs = [
            HumanMessage(content="你好"),
            AIMessage(content="嗨"),
            ToolMessage(content="result", tool_call_id="abc"),
            SystemMessage(content="system note"),
        ]
        out = _stringify_messages_for_summary(msgs)
        assert "用户: 你好" in out
        assert "助手: 嗨" in out
        assert "工具: result" in out
        assert "系统: system note" in out

    def test_ai_with_tool_calls_shows_tool_names(self):
        """带 tool_calls 的 AI 消息应在末尾标注调用的工具名。"""
        ai = AIMessage(
            content="我需要查一下",
            tool_calls=[{"name": "lookup_ingredient", "args": {}, "id": "t1"}],
        )
        out = _stringify_messages_for_summary([ai])
        assert "lookup_ingredient" in out

    def test_truncates_long_content(self):
        """单条超过 400 字符的内容会被截断,避免摘要 prompt 撑爆上下文。"""
        long_text = "x" * 1000
        out = _stringify_messages_for_summary([HumanMessage(content=long_text)])
        assert "..." in out
        assert len(out) < 600  # 截到 400 + "用户: " + "..." 之类
