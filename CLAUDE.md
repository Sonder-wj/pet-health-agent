# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pet Nutrition Agent — AI 宠物营养配餐管家。后端 FastAPI + LangGraph ReAct Agent + 纯 Python 营养引擎；前端 Vue 3 SPA 构建后由 FastAPI 静态服务。

核心定位：**Agent 只做理解 / 追问 / 编排 / 解释，所有营养数值计算由确定性引擎完成、可独立单测证明正确。**

## Commands

**Setup**
```powershell
.\.venv\Scripts\Activate.ps1
cp .env.example .env       # 填入真实值
pip install -r requirements.txt
```

**Run server**
```powershell
uvicorn main:app --reload
```

**Run tests**
```powershell
pytest                                                # all tests
pytest tests/test_engine_evaluate.py                  # 引擎集成测试
pytest tests/test_tool_assess_nutrition.py            # Agent 工具测试
pytest tests/test_graph_nutrition_flow.py             # graph smoke
```

**Lint & type check**
```powershell
ruff check .
mypy app/
```

**Frontend**
```powershell
cd frontend
npm install
npm run dev      # dev server (5173)
npm run build    # build → frontend/dist/ (copy to static/)
```

## Architecture

### 两层分工

```
┌─────────────────────────────────────────────────────────┐
│  Agent 层 (app/agent/)                                  │
│  - LangGraph ReAct: agent_node ⇄ tool_node              │
│  - 工具调度、用户对话、报告渲染                          │
│  - 严禁自算 kcal/营养密度(system prompt 硬约束)          │
└────────────┬────────────────────────────────────────────┘
             │ 5 个工具调用
             ▼
┌─────────────────────────────────────────────────────────┐
│  Engine 层 (app/engine/) — 纯 Python、零 LLM、可单测     │
│  - assess() 主入口 → NutritionAssessment                │
│  - energy / nutrient_analysis / requirements /          │
│    constraints / allergens 六模块                       │
│  - data/*.json 带 provenance(source/version/review_date) │
└─────────────────────────────────────────────────────────┘
```

### LangGraph Agent Flow

```
agent_node
  ├─ has tool_calls ──→ tool_node ──→ (final_response → END | else → agent_node)
  └─ no tool_calls ──→ END
```

- Max iterations: 8；同一工具连续 2 次 → 强制终结，防止死循环。
- Checkpoint：SQLite via `langgraph.checkpoint.sqlite.SqliteSaver`（`settings.CHECKPOINT_DB_PATH`）。
- 没有独立分诊节点，没有 ER 通道。所有"严重程度"判断都来自引擎 `Finding.severity`（info/warning/critical）。

### Tools Registry (`app/agent/tools/registry.py`)

5 个工具：

| Tool | Purpose |
|------|---------|
| `extract_label_nutrition(image_path)` | 多模态：从商品粮包装照片提取保证成分分析（GPT-4o vision） |
| `lookup_ingredient(query, max_results=5)` | 在 USDA 子集中按英文键 / 中文片段查食材每 100g 营养 |
| `compute_energy_requirement(species, weight_kg, age_months?, neutered, conditions?)` | 包装引擎 RER/MER + 生命阶段 |
| `assess_nutrition(profile, diet_input)` | **唯一**综合评估入口，调引擎 `assess()` 返回 NutritionAssessment |
| `final_answer(message)` | 终结工具；设 `state.final_response` + `state.report_md` |

### AgentState (`app/agent/state.py`)

```python
class AgentState(TypedDict, total=False):
    messages          # LangGraph 消息历史
    pet_profile       # {species, weight_kg, age_months, neutered, conditions, allergens, name?, breed?}
    diet_input        # {items?: [...], label?: {...}, amount_g?, kcal?, nutrients?, ingredient_names?}
    label_image_path  # 用户上传的包装照,由 extract_label_nutrition 消费
    assessment        # engine.assess() 序列化结果
    tool_results      # 工具调用日志
    iteration_count   # ReAct 循环计数
    final_response    # final_answer 设置后结束循环
    report_md         # 最终 Markdown 报告
```

### Engine 层 (`app/engine/`)

详见 `docs/superpowers/specs/2026-05-29-pet-nutrition-agent-design.md` 与 `docs/superpowers/plans/2026-05-29-pet-nutrition-engine.md`。

| 模块 | 职责 |
|------|------|
| `models.py` | 数据结构：`Severity` / `Finding` / `NutrientResult` / `EnergyResult` / `DietTotals` / `NutritionAssessment` |
| `data_loader.py` | 读 `data/*.json` + provenance 校验 + 模块级缓存 |
| `energy.py` | `compute_rer/compute_mer/resolve_life_stage` |
| `nutrient_analysis.py` | `to_dmb` / `atwater_kcal` / `analyze_homemade` / `analyze_label` |
| `requirements.py` | `resolve_stage(adult/growth)` / `get_requirements` |
| `constraints.py` | `apply_constraints`（疾病覆盖需求目标） |
| `allergens.py` | `check_allergens`（食材名 vs 已知过敏原） |
| `evaluate.py` | `assess` 主入口（编排上述 → NutritionAssessment） |

数据文件均含 `source` / `version` / `review_date` provenance；loader 强校验。

### Chat API (`app/api/chat.py`)

- `POST /api/chat` — multipart form（`query`, `session_id?`, `image?`）；返回 SSE 流。
- `POST /api/chat/{session_id}/resume` — 标准 ReAct 续接，无医疗向短路。
- `GET /api/history` — 当前用户的对话列表。
- `GET /api/history/{thread_id}` — 单条对话的消息记录。

SSE 事件类型：`thinking | token | tool_call | tool_result | assessment | report | done | error`。

### Data Layer

- **MySQL**（aiomysql + SQLAlchemy async）：`User`, `Conversation`, `Message`。聊天历史持久化是 best-effort（异常被静默吞掉，不阻塞主流程）。
- **不再使用** Milvus / Ollama / pymilvus — 营养评估走确定性查表，不需要向量检索。

### Config (`app/core/config.py`)

所有设置通过 `.env` 加载（pydantic-settings）。关键变量：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`DB_*`、`SECRET_KEY`、`CHECKPOINT_DB_PATH`。

### Frontend → Backend Integration

Frontend（`frontend/`）是 Vue 3 + Vite SPA。`npm run build` 后将 `frontend/dist/*` 复制到 `static/`。FastAPI 挂载 `static/` 并对 `GET /{full_path}` 做 SPA catch-all 兜底。

> ⚠️ 当前 `static/` 中的资源是旧医疗版前端构建产物，Plan 3 将完整重做 Vue UI（采集 profile / 渲染 assessment / report）。
