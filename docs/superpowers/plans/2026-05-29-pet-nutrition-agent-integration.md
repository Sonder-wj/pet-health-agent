# 宠物营养 Agent 集成 — 纲要(Plan 2 / 3)

> 轻量纲要,只锁**结构决策、文件清单、依赖顺序**。不写 verbatim 代码 — 实现时再决定细节。Plan 1(`docs/superpowers/plans/2026-05-29-pet-nutrition-engine.md`)已落地 `app/engine/`,本计划直接 `from app.engine import assess` 等真实 API。

**Goal:** 把 `app/engine/` 包装成 LangGraph ReAct Agent 工具链,删除全部旧医疗代码,产出"宠物营养配餐管家"可用的后端(POST `/api/chat` → SSE 流出评估报告)。

**核心思路:** Agent 只做"理解 / 追问 / 编排 / 解释",所有数值计算都通过工具调用引擎完成。一个图(ReAct 循环)、四个新工具、一份新 system prompt。

---

## 范围

**In:** 新工具(4 个)、AgentState 重构、graph 简化、system prompt 重写、config 清理、删除旧医疗代码、新工具测试 + smoke graph test。

**Out:** 前端 UI(Plan 3);CRUD 持久化 `PetProfile`(后续可加,这次先放 state 字段)。

---

## 新增文件(`app/agent/tools/`)

| 文件 | 工具 | 单行职责 |
|------|------|----------|
| `extract_label.py` | `extract_label_nutrition(image_path?)` | 多模态:从商品粮包装照片提取 `{crude_protein_pct, crude_fat_pct, crude_fiber_pct, moisture_pct, kcal_per_kg?}`(GPT-4o vision 一次调用 + JSON schema)。无 image 时返回错误 — 让 Agent 改走纯文本路径。 |
| `lookup_ingredient.py` | `lookup_ingredient(query)` | 在 `data/ingredients.json` 中按英文键或中文 `name_zh` 子串查找。返回 hit 列表(name + per-100g 数据)或 [] 让 Agent 追问澄清。 |
| `compute_energy.py` | `compute_energy_requirement(profile)` | 包装 `engine.energy.compute_rer/compute_mer/resolve_life_stage`,返回 `{rer, mer, life_stage}`。 |
| `assess_nutrition.py` | `assess_nutrition(profile, diet_input)` | 主工具:接受 `profile` + `diet_input`(自制食材列表 OR 商品粮 label OR 已聚合 `DietTotals` 字典)→ 调 `engine.assess` → 返回 `NutritionAssessment` 序列化字典。所有 finding/severity 都来自引擎。 |

**保留:** `app/agent/tools/final_answer.py`(终结工具)、`registry.py`(改导入)。

---

## 修改文件

### `app/agent/state.py` — 重构
**删除字段:** `triage_level`, `already_triaged`, `awaiting_user_input`, `image_path`(改名)、`visit_summary`、其余医疗专用字段。

**新增字段:**
- `pet_profile: dict | None` — `{species, weight_kg, age_months, neutered, conditions[], allergens[]}`
- `diet_input: dict | None` — 用户提供的饮食描述(原样)
- `assessment: dict | None` — `engine.assess()` 返回的序列化结果(供前端/报告用)
- `report_md: str | None` — `final_answer` 生成的最终 Markdown 报告
- `label_image_path: str | None` — 用户上传的包装照片(替代旧 `image_path`)

### `app/agent/graph.py` — 简化
- **删除:** `triage_node`, `er_response_node`, 以及 `er_now` 路由分支。
- **新结构:** 标准 ReAct 二节点循环:
  ```
  agent_node ⇄ tool_node  (最多 8 轮,终结条件: final_response 被设置)
  ```
- 保留: max_iterations=8、相同工具连续 2 次触发强制终结(防呆)、SqliteSaver checkpoint。

### `app/agent/prompts/system.py` — 重写
**核心指令:**
- 角色:宠物营养评估师。**绝不自己算 kcal/营养密度** — 一律调 `assess_nutrition`。
- 工作流:① 收集 profile(物种/体重/月龄/绝育/疾病/过敏原)→ 缺啥追问啥;② 解析 diet_input(自制 → `lookup_ingredient` 逐项确认 + 量;商品粮 → 让用户文字输入 GA 或上传包装照走 `extract_label_nutrition`);③ 调 `assess_nutrition`;④ 用 `final_answer` 渲染中文报告。
- 报告模板:能量平衡、关键营养素状态(用引擎的 status/severity)、findings 分级展示、建议(数据驱动 + 安全声明)。
- 安全免责:不替代兽医、不开药、CRITICAL 级建议就医。

### `app/agent/tools/registry.py` — 重写
绑定 5 个工具:`extract_label_nutrition`, `lookup_ingredient`, `compute_energy_requirement`, `assess_nutrition`, `final_answer`。

### `app/api/chat.py` — 适配
- 删除事件类型:`triage`, `question`, `visit_summary`。
- 新增事件类型:`profile_update`, `assessment`(序列化 `NutritionAssessment`)、`report`。
- 保留:`thinking`, `token`, `tool_call`, `tool_result`, `done`, `error`。
- 删除 `/api/chat/{id}/resume` 的 `already_triaged` 短路逻辑 — Resume 走标准 ReAct。

### `app/core/config.py` — 清理
**删除:** `MILVUS_HOST/PORT/COLLECTION`, `OLLAMA_BASE_URL`, `OLLAMA_EMBEDDING_MODEL`。
**保留:** `OPENAI_*`, `DB_*`, `SECRET_KEY`, `CHECKPOINT_DB_PATH`。
同步删 `.env.example` 对应行。

---

## 删除文件(批量)

**工具层(旧医疗):**
- `app/agent/tools/triage.py`
- `app/agent/tools/medication.py`
- `app/agent/tools/symptom_collect.py`
- `app/agent/tools/symptom_track.py`
- `app/agent/tools/knowledge.py`
- `app/agent/tools/visit_summary.py`
- `app/agent/tools/image_analysis.py` — 被 `extract_label.py` 替代

**RAG 整个目录(改用确定性查表):**
- `app/rag/` 全删 → `__init__.py`, `embeddings.py`, `loader.py`, `retriever.py`

**模型:**
- `app/models/symptom_log.py`

**数据:**
- `data/medications.json`
- `data/pet_diseases.json`

**脚本:**
- `scripts/expand_diseases.py`

**旧测试:**
- `tests/test_triage.py`
- `tests/test_medication.py`
- `tests/test_knowledge.py`
- `tests/test_symptom_collect.py`
- `tests/test_visit_summary.py`
- `tests/test_graph.py` — 改写为新的营养流(不是单删)

**依赖清理(`requirements.txt`):** 移除 `pymilvus`。

---

## 集成顺序(关键依赖图)

```
1. 4 个新工具(并行可写,只依赖 engine 已落地)
   ├─ extract_label.py    需 OPENAI_API_KEY(已有)
   ├─ lookup_ingredient.py 纯查表
   ├─ compute_energy.py   纯包装
   └─ assess_nutrition.py 纯包装
2. AgentState 重构(依赖 1 — 字段呼应新工具的入参/出参)
3. system prompt 重写(依赖 1+2)
4. graph 简化(依赖 1+2+3)
5. API 适配(依赖 4 — SSE 事件依赖新 state)
6. 删除旧代码(放最后 — 让新代码先证明能跑,旧代码作为回退参考)
7. config + .env.example 清理(可与 6 同步)
8. 全量回归 + ruff/mypy + 一次手动 smoke
```

**为什么删除放最后:** 中途删旧代码会让 lint/import 一片红、混淆"是不是真坏了"。新代码绿了再扫一遍 import,删起来心里有数。

---

## 测试策略

**新增单测(逐工具一文件):**
- `tests/test_tool_lookup_ingredient.py` — hit / 中文别名 hit / miss 返空。
- `tests/test_tool_compute_energy.py` — 一个 fixture profile → RER/MER 与引擎自身测试匹配。
- `tests/test_tool_assess_nutrition.py` — fixture profile + DietTotals dict → assessment 结构正确、引擎 findings 透传。
- `tests/test_tool_extract_label.py` — **mock 掉 LLM 调用**(`monkeypatch` `ChatOpenAI.invoke`),只验 JSON schema 解析与 fallback。
- `tests/test_state_nutrition.py` — 新字段默认值。
- `tests/test_graph_nutrition_flow.py` — mock LLM,验证 ReAct 循环在两轮内调到 `assess_nutrition` 并以 `final_answer` 终结。

**不测的:** 真实 LLM 端到端(留给 manual smoke);多模态真实图像(留给 manual)。

**回归门:**
- `pytest` 引擎 46 测试继续全绿。
- 新增 agent 测试全绿。
- `ruff check app/ tests/` 无报错。
- `mypy app/agent/ app/engine/` 无错。
- Manual smoke:启动 `uvicorn main:app`, POST 一个 profile + 自制饮食 → SSE 流出包含 `assessment` 与 `report` 事件、报告含 critical/warning findings。

---

## 风险与决策(已锁)

| 风险 | 决策 |
|------|------|
| 多模态 label OCR 不准 | 工具失败时让 Agent fallback 到"请用户文字输入 GA 数据"分支。**不**做 fancy OCR 兜底。 |
| LLM 漏调 `assess_nutrition` 自己估算 | system prompt 用"硬约束 + 错误示范"显式禁止;`compute_energy` 也作为提示让 LLM 习惯调工具。 |
| 删除旧医疗代码可能破坏 import 链 | 删除前跑 `ruff check` 找未引用导入;每删一个模块跑一次 `pytest --co -q` 确保收集仍 0 错。 |
| 历史会话(checkpoint.db)结构不兼容 | Demo 项目,直接删 `checkpoints.db`(已 gitignore)。新结构从零开始。 |
| Milvus/Ollama 配置移除后部署文档要更新 | `CLAUDE.md` 的 Architecture 节同步重写(Plan 2 收尾时一起改)。 |

---

## 任务划分(给 SDD 执行用)

按集成顺序 6 个任务,每个任务自包含一个 commit 单元。具体 step 留给 implementer:

- **T1** — 4 个新工具(`extract_label / lookup_ingredient / compute_energy / assess_nutrition`)+ 对应 4 个测试。**1 个 commit**(或拆 2 个,取决于规模)。
- **T2** — `AgentState` 重构 + state 测试。**1 个 commit**。
- **T3** — `system.py` 重写 + `registry.py` 重写。**1 个 commit**(prompt + registry 联动)。
- **T4** — `graph.py` 简化 + smoke graph 测试。**1 个 commit**。
- **T5** — `app/api/chat.py` SSE 事件适配。**1 个 commit**。
- **T6** — 批量删除旧医疗代码 + `config.py` / `requirements.txt` 清理 + `CLAUDE.md` 更新。**1 个 commit**(必要时拆成"删工具/RAG/测试/删配置"两次)。
- **T7** — 全量回归 + ruff + mypy + manual smoke。**0~1 commit**(只在 lint 修复时)。

---

## 衔接

完成后引擎 + Agent 后端均可运行。**Plan 3 — 前端 Vue 适配:**
- 表单收集 profile / diet_input、上传包装照
- 接 SSE 渲染 `assessment` 事件为雷达图 + 营养卡片
- `report` 事件渲染为 Markdown,支持 PDF 导出
- 清理掉历史医疗向 UI(triage 气泡、症状追问 UI 等)
