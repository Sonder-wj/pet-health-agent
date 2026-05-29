"""extract_label_nutrition 测试 — LLM 通过 monkeypatch 替换,不发真实请求。"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.agent.tools.extract_label as el_mod
from app.agent.tools.extract_label import extract_label_nutrition


class _FakeLLM:
    """模拟 ChatOpenAI 的 ainvoke,返回预设响应。"""

    def __init__(self, content: str):
        self._content = content

    async def ainvoke(self, messages):
        return SimpleNamespace(content=self._content)


@pytest.fixture(autouse=True)
def _reset_llm_cache(monkeypatch):
    """每个测试前重置模块级 LLM 缓存,避免相互污染。"""
    monkeypatch.setattr(el_mod, "_vision_llm", None)
    yield


@pytest.fixture
def fake_image(tmp_path: Path) -> Path:
    p = tmp_path / "label.jpg"
    # 一个最小化的 JPEG 头 + 终止符;内容随意,只要文件存在 + 能 base64
    p.write_bytes(b"\xff\xd8\xff\xe0fake_image_bytes\xff\xd9")
    return p


async def test_missing_file_returns_error():
    out = await extract_label_nutrition.ainvoke({"image_path": "/no/such/file.jpg"})
    assert out["status"] == "error"
    assert "不存在" in out["message"] or "存在" in out["message"]


async def test_successful_parse(monkeypatch, fake_image):
    fake_resp = json.dumps({
        "crude_protein_pct": 30,
        "crude_fat_pct": 12,
        "crude_fiber_pct": 4,
        "moisture_pct": 10,
        "kcal_per_kg": 3800,
    })
    monkeypatch.setattr(el_mod, "_get_vision_llm", lambda: _FakeLLM(fake_resp))

    out = await extract_label_nutrition.ainvoke({"image_path": str(fake_image)})
    assert out["status"] == "ok"
    assert out["label"]["crude_protein_pct"] == 30
    assert out["label"]["kcal_per_kg"] == 3800


async def test_markdown_wrapped_json_parse(monkeypatch, fake_image):
    wrapped = "```json\n" + json.dumps({
        "crude_protein_pct": 25, "crude_fat_pct": 10,
        "crude_fiber_pct": 3, "moisture_pct": 12, "kcal_per_kg": None,
    }) + "\n```"
    monkeypatch.setattr(el_mod, "_get_vision_llm", lambda: _FakeLLM(wrapped))

    out = await extract_label_nutrition.ainvoke({"image_path": str(fake_image)})
    assert out["status"] == "ok"
    assert out["label"]["crude_protein_pct"] == 25
    assert out["label"]["kcal_per_kg"] is None


async def test_invalid_json_response_returns_error(monkeypatch, fake_image):
    monkeypatch.setattr(el_mod, "_get_vision_llm", lambda: _FakeLLM("not json at all"))

    out = await extract_label_nutrition.ainvoke({"image_path": str(fake_image)})
    assert out["status"] == "error"
    assert "raw" in out  # 原始响应被回传供调试


async def test_llm_raises_returns_error(monkeypatch, fake_image):
    class _RaisingLLM:
        async def ainvoke(self, messages):
            raise RuntimeError("network down")

    monkeypatch.setattr(el_mod, "_get_vision_llm", lambda: _RaisingLLM())

    out = await extract_label_nutrition.ainvoke({"image_path": str(fake_image)})
    assert out["status"] == "error"
    assert "LLM" in out["message"] or "network" in out["message"]
