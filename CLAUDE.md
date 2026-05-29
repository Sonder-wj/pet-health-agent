# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pet Health Agent — AI 宠物健康问诊平台。后端 FastAPI + LangGraph ReAct Agent，前端 Vue 3 SPA 构建后由 FastAPI 静态服务。

## Commands

**Setup**
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Copy .env.example and fill in values
cp .env.example .env

# Install dependencies
pip install -r requirements.txt
```

**Run server**
```powershell
uvicorn main:app --reload
```

**Run tests**
```powershell
pytest                                          # all tests
pytest tests/test_triage.py                    # single file
pytest tests/test_triage.py -k test_seizure    # single test by name
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
npm run dev      # dev server (port 5173)
npm run build    # build → frontend/dist/ (then copy to static/)
```

## Architecture

### LangGraph Agent Flow

```
triage_node
  ├─ er_now ──→ er_response_node ──→ END
  └─ else  ──→ agent_node
                  ├─ has tool_calls ──→ tool_node ──→ (final_response/awaiting_input → END | else → agent_node)
                  └─ no tool_calls ──→ END
```

- Max iterations: 8, loop detection window: 2 (same tool called twice in a row → force final answer)
- Checkpoint: SQLite via `langgraph.checkpoint.sqlite.SqliteSaver` (file path from `settings.CHECKPOINT_DB_PATH`)
- `already_triaged: True` is set after first triage to prevent re-triage on `/chat/{id}/resume`

### Triage Logic (`app/agent/tools/triage.py`)

Two-stage: hard keyword list (抽搐/便血/呼吸困难/中毒 etc.) short-circuits to `er_now` before calling LLM. LLM returns one of: `home_care | schedule_visit | er_now`. Falls back to `schedule_visit` on parse error.

### Tools Registry (`app/agent/tools/registry.py`)

7 tools bound to `agent_node` via `.bind_tools()`:
| Tool | Purpose |
|------|---------|
| `collect_symptoms` | Multi-turn symptom collection; sets `awaiting_user_input` when more info needed |
| `analyze_pet_image` | Multimodal image analysis from `state.image_path` |
| `search_pet_knowledge` | Milvus vector search (bge-m3, IP metric) |
| `medication_guide` | Drug dosage and contraindication lookup |
| `track_symptoms` | Persist/retrieve cross-session symptom history |
| `generate_visit_summary` | Structured vet-visit summary → `state.visit_summary` |
| `final_answer` | Terminal tool; sets `state.final_response`, ending the loop |

### AgentState (`app/agent/state.py`)

Key fields that drive routing:
- `triage_level`: `home_care | schedule_visit | er_now | None`
- `awaiting_user_input`: pauses loop for user response; resume via `POST /api/chat/{session_id}/resume`
- `final_response`: signals end of loop from either `final_answer` tool or `er_response_node`
- `already_triaged`: skips triage on resume

### Chat API (`app/api/chat.py`)

- `POST /api/chat` — multipart form (`query`, `session_id?`, `image?`); returns SSE stream
- `POST /api/chat/{session_id}/resume` — continue after `awaiting_user_input`; skips re-triage
- `GET /api/history` — list conversations for current user
- `GET /api/history/{thread_id}` — messages for a conversation

SSE event types: `thinking | token | tool_call | tool_result | triage | question | visit_summary | done | error`

### Data Layer

- **MySQL** (aiomysql + SQLAlchemy async): `User`, `Conversation`, `Message`, `SymptomLog`. Chat history persistence is best-effort (failures are silent — `_save_chat_history` catches all exceptions).
- **Milvus**: collection `pet_knowledge`, bge-m3 1024-dim embeddings, IVF_FLAT / IP metric, top-k=3. `app/rag/retriever.py` auto-creates the collection if absent.
- **Ollama**: local embedding service for bge-m3 (`OLLAMA_BASE_URL`).

### Config (`app/core/config.py`)

All settings via `.env` loaded with `pydantic-settings`. Key vars: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OLLAMA_BASE_URL`, `DB_*`, `MILVUS_*`, `SECRET_KEY`.

### Frontend → Backend Integration

Frontend (`frontend/`) is a Vue 3 + Vite SPA. After `npm run build`, copy `frontend/dist/*` to `static/`. FastAPI mounts `static/` and has a catch-all SPA fallback at `GET /{full_path}`.
