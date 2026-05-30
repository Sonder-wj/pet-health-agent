# 🐾 小宠营养师 — AI 宠物营养评估管家

> **基于 LangGraph ReAct + 确定性 Python 营养引擎的垂直评估系统** — Agent 只调工具不算数,所有数值计算由独立可单测的引擎完成,每条 finding 带 `source`/`version`/`review_date` 出处。

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.3-ff6600)](https://github.com/langchain-ai/langgraph)
[![Vue](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js)](https://vuejs.org/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek_V4-purple)](https://platform.deepseek.com/)
[![Tests](https://img.shields.io/badge/tests-119_passing-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

---

## 📋 目录

- [项目简介](#-项目简介)
- [系统架构](#%EF%B8%8F-系统架构)
- [核心特性](#-核心特性)
- [技术栈](#%EF%B8%8F-技术栈)
- [快速开始](#-快速开始)
- [项目结构](#-项目结构)
- [对话示例](#-对话示例)
- [License](#-license)

---

## 🎯 项目简介

小宠营养师是面向宠物主人的 **AI 饮食评估系统**。LangGraph ReAct Agent 负责理解 / 追问 / 调度 / 解释;纯 Python 营养引擎(零 LLM)完成 RER/MER、修正 Atwater、AAFCO 查表、Ca:P、疾病约束、过敏原冲突等所有计算,引擎数据带可追溯的出处。

**这个项目能展示什么?**

- ✅ **Agent / Engine 分层**:LLM 不碰算数,所有数字可单测可追溯
- ✅ **完整 ReAct 工程化**:LangGraph + 8 工具 + 循环检测 + 强制收尾 + 孤儿消息清洗
- ✅ **3 层记忆**:LangGraph SQLite checkpoint + MySQL 跨 thread 档案/长事实 + 30 条超阈值 LLM 摘要压缩
- ✅ **多模态商品粮 OCR**:Qwen3-VL 提取包装保证成分分析
- ✅ **生产级异步持久化**:`AsyncSqliteSaver` 由 FastAPI lifespan 异步上下文管理
- ✅ **强制鉴权 + 数据隔离**:JWT + `require_user`,无匿名 fallback

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend  Vue 3 + Pinia + Vite                              │
│  SSE: thinking / token / tool_call / tool_result /          │
│       assessment / report / done                             │
└──────────────────────┬──────────────────────────────────────┘
                       │ multipart + JWT Bearer
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI  (lifespan: AsyncSqliteSaver → app.state)          │
│  /api/auth · /api/chat · /api/chat/{id}/resume · /api/history│
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent 层 (app/agent/) — LangGraph ReAct                    │
│  agent_node ⇄ tool_node                                      │
│  注入 system + user_pets + user_memories + pet_profile      │
│  历史压缩(>30 条)+ sanitize 孤儿 ToolMessage               │
│  防护: MAX_ITERATIONS=8 + 同工具连调 2 次 → 强制收尾         │
└──────────────────────┬──────────────────────────────────────┘
                       │ 8 个工具
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Engine 层 (app/engine/) — 纯 Python、零 LLM、独立可单测     │
│  energy · nutrient_analysis · requirements · constraints ·  │
│  allergens · evaluate                                        │
│  data/*.json (含 source/version/review_date)                │
└─────────────────────────────────────────────────────────────┘

存储: MySQL 8.0(users/conversations/messages/pets/user_memories)
      SQLite WAL(nutrition_checkpoints.db,LangGraph thread state)
```

---

## ✨ 核心特性

### 1. Agent / Engine 严格分层

LLM 算数会错——把 12kg 狗的 RER 算成 504(实际 477)、Ca:P 比例倒着算。营养评估涉及健康,**必须可单测、可追溯**。所有计算搬到独立 Python 引擎,system prompt 硬约束 `❌ 不要自己估算 kcal/营养素/Ca:P 比/MER`,`data/*.json` 必须带 `source`/`version`/`review_date`,loader 强校验。

### 2. 8 个职责单一的工具

| 工具 | 作用 |
|------|------|
| `lookup_ingredient` · `compute_energy_requirement` · `assess_nutrition` | USDA 查表 / RER+MER / 综合评估(唯一入口) |
| `extract_label_nutrition` | Qwen3-VL 识别商品粮包装的保证成分分析 |
| `save_pet_profile` · `list_pets` · `remember` | 宠物档案 CRUD + 长记忆写入 |
| `final_answer` | 终结 + Markdown 报告 |

`save_pet_profile` / `list_pets` / `remember` 的 `user_id` 通过 LangChain `RunnableConfig` 注入,**LLM 看不到该参数**,无法伪造他人身份。

### 3. 3 层记忆系统

| 层 | 存储 | 职责 |
|----|------|------|
| **MySQL** | `pets` / `user_memories` | 跨 thread 持久化(档案、预算、兽医叮嘱、品牌偏好) |
| **SQLite Checkpoint** | `nutrition_checkpoints.db`(WAL) | 单 thread 完整 AgentState 自动快照,续接不失忆 |
| **历史压缩** | LLM 摘要 | `messages > 30` 时把老消息合并成 1 条 system 摘要,保留最近 10 条 |

API 在 chat 启动 + 每次 resume 时把 `pets` / `user_memories` 重查刷新注入,跨 thread 数据立刻可见。`iteration_count` / `final_response` / `report_md` 续接时必须重置,否则会撞 `MAX_ITERATIONS` 或让 Agent 不开口(踩过坑)。

### 4. 多模态商品粮解析

用户上传一张包装照,`extract_label_nutrition` 调 Qwen3-VL-Flash 识别"保证成分分析"区域,返回结构化 JSON(粗蛋白/脂肪/纤维/水分/kcal)。失败时(图片模糊)Agent 自动改请用户文字输入。

### 5. 强制鉴权 + 数据隔离

`require_user` 依赖:无 token / token 无效一律 **401**,删除所有匿名 fallback。`/api/history/{thread_id}` 加防越权检查,他人对话拒绝。前端 401 自动 `auth.logout()` → 跳 `/login`,JWT 默认 7 天。

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **Agent** | LangGraph 0.3 (ReAct) + AsyncSqliteSaver |
| **LLM** | DeepSeek V4-Flash(主对话) + Qwen3-VL-Flash(视觉,via 阿里百炼) |
| **后端** | FastAPI 0.115 + SQLAlchemy 2.0 async + aiomysql |
| **前端** | Vue 3 + Pinia + vue-router + Vite 6 + marked |
| **DB** | MySQL 8.0(Docker) + SQLite WAL(checkpoint) |
| **鉴权** | JWT (python-jose) + bcrypt,7 天 |
| **测试** | pytest + pytest-asyncio,119 用例;ruff + mypy |

---

## 🚀 快速开始

### 前置条件

Python 3.13 · Node.js 20+ · Docker Desktop · DeepSeek API Key · 阿里百炼 API Key

### 启动步骤

```bash
# 1. 起 MySQL 容器(映射到 3307 避开本地 3306)
docker run -d --name pet-health-mysql \
  -p 3307:3306 -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=pet_health_agent --restart unless-stopped mysql:8.0

# 2. Python 环境 + 配置
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # 填 OPENAI_API_KEY + VISION_API_KEY

# 3. 起后端
uvicorn main:app --host 127.0.0.1 --port 8000

# 4. 起前端(新终端)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

打开 `http://localhost:5173` 注册账号即可。API 文档:`http://localhost:8000/docs`。


---

## 📁 项目结构

```
pet-health-agent/
├── 📂 frontend/              Vue 3 + Pinia + Vite
├── 📂 app/
│   ├── core/                 config · database · auth · deps · logger
│   ├── api/                  auth · chat (SSE)
│   ├── models/               user · conversation · message · pet · user_memory
│   ├── agent/                ← LangGraph 层
│   │   ├── graph.py          StateGraph + 历史压缩 + sanitize + 循环检测
│   │   ├── state.py          AgentState
│   │   ├── prompts/system.py
│   │   └── tools/            8 个工具(每个独立文件)
│   └── engine/               ← 纯 Python 营养引擎(零 LLM)
│       ├── energy · nutrient_analysis · requirements
│       ├── constraints · allergens · evaluate
│       └── data_loader (provenance 强校验)
├── 📂 data/                  USDA · AAFCO · disease · allergens (JSON)
├── 📂 tests/                 119 用例(engine 单元 + 工具签名 + graph smoke)
├── main.py                   FastAPI 入口 + lifespan
└── requirements.txt
```

---

## 💬 对话示例

**自制饮食评估**
```
我家狗叫旺财,3 岁绝育金毛 12kg,每天喂 200g 鸡胸 + 150g 米饭,合适吗?
```
> Agent: `lookup_ingredient` → `save_pet_profile` → `compute_energy_requirement` → `assess_nutrition` → `final_answer`

**商品粮包装解析**
```
[上传包装照] 我家猫 4 岁绝育英短 4kg,每天吃 60g 这款,可以吗?
```
> Agent: `extract_label_nutrition`(Qwen3-VL OCR)→ `assess_nutrition`(商品粮路径)→ `final_answer`

**跨对话档案复用**
```
对话 1: "旺财 12kg,有肾病史"     → save_pet_profile 落库
对话 2: "旺财今天 13.5kg 了"     → API 预注入 user_pets,Agent 不重问,直接覆盖
```

**长记忆 + 多轮追问**
```
"我每月狗粮预算 500 元"           → remember(category=constraint)
[评估报告后] "为什么钙不够?"      → 不再调工具,基于 state.assessment 直接解释
```

---

## 📄 License

[MIT License](./LICENSE) — 自由使用、修改、分发,保留版权声明即可。
