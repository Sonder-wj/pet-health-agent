"""save_pet_profile / list_pets 工具的 smoke 测试。

不连真实 DB(避免在 CI/单测里依赖 MySQL),只覆盖:
- 无 user_id(config 缺失或不带 configurable)→ 友好 error
- 工具能被 import + 调用,无语法/签名问题
真实 DB 行为由集成测试在 manual smoke 阶段覆盖。
"""
import pytest

from app.agent.tools.list_pets import list_pets
from app.agent.tools.save_pet_profile import save_pet_profile


@pytest.mark.asyncio
async def test_save_pet_profile_rejects_without_user_id():
    """无 user_id 时 save 必须拒,不能落库 user_id=NULL。"""
    result = await save_pet_profile.ainvoke({
        "name": "旺财",
        "species": "dog",
        "weight_kg": 12.0,
    }, config=None)
    assert result["status"] == "error"
    assert "未登录" in result["message"]


@pytest.mark.asyncio
async def test_list_pets_rejects_without_user_id():
    """无 user_id 时 list 返回空,不能跨用户漏数据。"""
    result = await list_pets.ainvoke({}, config=None)
    assert result["status"] == "error"
    assert result["pets"] == []


@pytest.mark.asyncio
async def test_save_pet_profile_rejects_with_empty_configurable():
    """config 存在但 configurable 缺 user_id 也要拒,不能 fallback。"""
    result = await save_pet_profile.ainvoke({
        "name": "喵喵",
        "species": "cat",
        "weight_kg": 4.0,
    }, config={"configurable": {}})
    assert result["status"] == "error"
