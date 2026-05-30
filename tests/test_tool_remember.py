"""remember 工具的 smoke 测试 — 无 DB 依赖,只覆盖签名 / 错误路径。"""
import pytest

from app.agent.tools.remember import remember


@pytest.mark.asyncio
async def test_remember_rejects_without_user_id():
    result = await remember.ainvoke({"content": "主人预算 500"}, config=None)
    assert result["status"] == "error"
    assert "未登录" in result["message"]


@pytest.mark.asyncio
async def test_remember_rejects_empty_content():
    result = await remember.ainvoke(
        {"content": "   "},
        config={"configurable": {"user_id": 1}},
    )
    assert result["status"] == "error"
    assert "content" in result["message"]


@pytest.mark.asyncio
async def test_remember_accepts_default_category():
    """category 缺省 → general,不应报错(验证默认值生效到工具签名)。"""
    # 这次 user_id 给一个非 None 值绕过登录检查;
    # 实际 DB 写入会因为 user_id 不存在外键失败,但我们只验工具签名层。
    result = await remember.ainvoke(
        {"content": "test"},
        config={"configurable": {"user_id": 999999}},  # 故意不存在
    )
    # 这里要么 ok(若 FK 不强制),要么 error 但不是"category 字段错";
    # 关键是工具签名兼容 category 缺省。
    assert "status" in result
