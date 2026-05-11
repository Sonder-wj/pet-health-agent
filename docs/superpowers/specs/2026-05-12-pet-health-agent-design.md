# Pet Health Agent — 设计文档

## 一、项目概述

**定位：** 面向宠物主人的 AI 健康问诊 Agent。用户说"猫吐了"，Agent 自主判断需要追问什么、要不要分诊、该查什么资料、最后给什么建议。

**核心价值：** 解决宠物主人最焦虑的决策——"宠物不舒服时不知道该不该去医院、该怎么处理"。

**和 FitChef 的分工：**

| | FitChef | Pet Health Agent |
|---|---|---|
| 范式 | RAG 检索增强生成 | ReAct Agent 自主决策 |
| LLM 角色 | 只做生成 | 做决策 + 推理 + 生成 |
| 控制流 | 线性 13 步 | 循环，轮次不确定 |
| 检索 | 硬编码在流程里 | LLM 自主决定何时检索 |
| 工具 | 无（内部函数） | 6 个 Function Calling 工具 |
| 框架 | 纯手写 | LangChain + LangGraph |

---

## 二、核心架构：单 StateGraph ReAct 循环

```
                    ┌──────────┐
     ┌─────────────│   agent   │◄───────────────┐
     │             └─────┬─────┘                │
     │                   │                      │
     │          ┌────────▼────────┐             │
     │          │ should_continue?│             │
     │          └───┬─────────┬───┘             │
     │              │         │                 │
     │         ┌────▼──┐  ┌───▼──────────┐     │
     │         │  END  │  │    tools     │     │
     │         └───────┘  └──────┬───────┘     │
     │                           │             │
     └───────────────────────────┘             │
                                                 │
     Agent state 在循环间持续流转                │
```

### State 设计

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # LangGraph 自动追加
    pet_profile: dict  # {name, species, breed, age, weight}
    collected_symptoms: list  # 追问收集到的结构化症状
    tool_results: dict  # 各工具返回结果 {tool_name: result}
    triage_level: str | None  # home_care / schedule_visit / er_now
    pending_question: str | None  # 追问内容，前端展示
    awaiting_user_input: bool  # 是否在等用户回答
    visit_summary: str | None  # 就诊摘要
    iteration_count: int  # 当前循环轮次
    final_response: str | None  # 非空则结束
```

### 循环终止（三道闸门）

| 层级 | 条件 | 逻辑 |
|------|------|------|
| 正常出口 | LLM 选择 final_answer 工具 | Agent 自主判断信息够了 |
| 硬限制 | iteration_count >= 8 | 防止死循环 |
| 死循环保护 | 连续 2 轮选同一工具且无新信息 | 检测无效循环 |

### 不拆子图的理由

ReAct 循环本身就能处理"追问→回答→再追问"的循环模式。子图只在内部有独立循环或需要独立 LLM 配置时有价值，当前场景加子图只增加解释成本，没有实际收益。

---

## 三、6 个工具设计

### 1. 紧急分诊 `emergency_triage`

| 项目 | 内容 |
|------|------|
| 输入 | 症状描述 + 物种 |
| 输出 | `{level: "home_care"\|"schedule_visit"\|"er_now", confidence, reasons[], watch_signs[]}` |
| 实现 | LLM 结构化输出 + 内置分诊规则表 |
| 关键设计 | 规则表定义 red flags（持续呕吐>24h、便血、抽搐等），LLM 从自然语言中匹配危险信号。confidence 低时自动推高一级，宁可保守 |

### 2. 症状追问 `collect_symptoms`

| 项目 | 内容 |
|------|------|
| 输入 | 已收集的症状 + 缺失的信息字段 |
| 输出 | 追问文本，前端展示给用户 |
| 实现 | LangGraph interrupt 机制 |
| 关键设计 | 逐轮追问，每轮只问一个维度（先问频率→再问性状→再问伴随症状）。Agent 输出 `pending_question` 后暂停，用户回答后 resume，重复直到信息充足或达到 3 轮 |

### 3. 图片分析 `analyze_pet_image`

| 项目 | 内容 |
|------|------|
| 输入 | 图片 base64 + 症状上下文 |
| 输出 | `{body_part, findings, severity, possible_conditions[], needs_vet_attention}` |
| 实现 | 多模态 LLM（Qwen-VL 或 GPT-4V） |
| 关键设计 | 分析结果写回 state，后续检索和追问基于图片发现做更精准的定向 |

### 4. 知识库检索 `search_pet_knowledge`

| 项目 | 内容 |
|------|------|
| 输入 | 症状关键词 + 图片分析结果 + 品种年龄 |
| 输出 | 匹配的疾病文档列表 |
| 实现 | 同 FitChef（Ollama bge-m3 embedding + Milvus + BM25 + RRF） |
| 关键设计 | 作为 Tool 被 Agent 自主调用，Agent 决定什么时候搜、搜什么、搜完要不要再搜。知识库涵盖犬猫常见疾病、护理方案、营养指南 |

### 5. 药物指导 `medication_guide`

| 项目 | 内容 |
|------|------|
| 输入 | 药品名 + 宠物体重 + 品种 |
| 输出 | `{dosage, frequency, duration, warnings[], contraindications[]}` |
| 实现 | 结构化药物数据库查询 + LLM 格式化 |
| 关键设计 | 品种禁忌检查（如柯利犬对某些药物敏感），剂量根据体重自动计算。数据库覆盖常见宠物用药 |

### 6. 就诊摘要 `generate_visit_summary`

| 项目 | 内容 |
|------|------|
| 输入 | 对话历史 + 宠物资讯 + 所有工具调用结果 |
| 输出 | 结构化就诊摘要 Markdown |
| 实现 | LLM 按固定模板总结 |
| 关键设计 | 模板化输出包含：宠物信息、主诉、症状时间线、已做处理、图片分析摘要、Agent 判断倾向、就诊建议。用户直接出示给兽医 |

---

## 四、ReAct 行为示例（同一 Agent，不同路径）

### 场景 A：用户已确诊

```
用户: "猫确诊膀胱炎，医生开了恩诺沙星，忘了问用量，猫 4.5kg"

第1轮: medication_guide("恩诺沙星", 猫, 4.5kg) → 出结果 → 结束

工具链路: 药查 (1个工具，1轮)
```

### 场景 B：先发图后追问

```
用户: [猫皮肤红疹照片]

第1轮: analyze_pet_image(照片) → 环形脱毛斑，边缘红肿，疑似猫癣
第2轮: search_pet_knowledge("猫癣 治疗方案") → 猫癣治疗文档
第3轮: generate_visit_summary → 带去看兽医

工具链路: 图析→检索→摘要 (3个工具，3轮，无追问无分诊)
```

### 场景 C：模糊描述 + Agent 自己升级

```
用户: "狗这两天不太对劲，吃不进去东西"

第1轮: emergency_triage("狗 拒食") → watch
       collect_symptoms → "不吃是完全没有食欲，还是吃了吐？精神怎么样？"
用户: "完全不吃，趴着不动"

第2轮: emergency_triage 重新调 → er_now（拒食+精神萎靡=危险组合）
       generate_visit_summary → "立即就医，不要拖"

工具链路: 分诊→追问→分诊升级→摘要 (4个工具，2轮，跳过检索和图析)
```

### 场景 D：Agent 推翻用户假设

```
用户: "猫吐了，是不是毛球？我想买化毛膏"

第1轮: collect_symptoms → "吐的是什么东西？有没有血丝？几次了？"
用户: "三次了，刚才吐的有血丝"

第2轮: emergency_triage → er_now
       generate_visit_summary → "不是毛球，血性呕吐需立即就医"

Agent 没有跟着用户的"毛球"假设走，追问后发现危险信号，推翻了用户的判断
```

---

## 五、技术栈

| 层 | 技术 |
|----|------|
| Agent 框架 | LangChain + LangGraph |
| 文本 LLM | DeepSeek API |
| 多模态 LLM | Qwen-VL（图片分析） |
| Embedding | Ollama bge-m3 |
| 向量数据库 | Milvus |
| RAG 融合 | BM25 + 向量 RRF 融合 |
| 后端 | FastAPI + SSE 流式 |
| 部署 | Docker Compose |

---

## 六、目录结构

```
pet-health-agent/
├── src/
│   ├── graph.py              # StateGraph 构建（节点+边+条件路由）
│   ├── state.py              # AgentState 定义
│   ├── tools/
│   │   ├── __init__.py       # 工具注册表
│   │   ├── triage.py         # 1. 紧急分诊
│   │   ├── symptom_collect.py # 2. 症状追问（含 interrupt）
│   │   ├── image_analysis.py # 3. 图片分析（多模态 LLM）
│   │   ├── knowledge.py      # 4. 知识库检索（RAG Tool）
│   │   ├── medication.py     # 5. 药物指导
│   │   └── visit_summary.py  # 6. 就诊摘要
│   ├── prompts/
│   │   ├── system.py         # Agent system prompt
│   │   └── tools.py          # 各工具 prompt 模板
│   └── rag/
│       ├── loader.py         # 宠物疾病知识库加载
│       ├── retriever.py      # 向量 + BM25 混合检索
│       └── embeddings.py     # Ollama embedding
├── data/
│   ├── pet_diseases.json     # 宠物疾病知识库
│   └── medications.json      # 宠物药物数据库
├── app.py                    # FastAPI 入口 + SSE 流式
├── docker-compose.yml
└── requirements.txt
```

---

## 七、后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 对话入口，SSE 流式。Agent 自主决策 → 需要追问时返回 question 事件并等待 resume |
| POST | `/chat/{session_id}/resume` | 用户回答追问后 resume Agent 循环 |
| POST | `/chat/{session_id}/upload` | 上传宠物图片 |

### SSE 事件类型

| 事件 | 含义 |
|------|------|
| `tool_call` | Agent 正在调用工具（含工具名和参数） |
| `tool_result` | 工具返回结果摘要 |
| `question` | Agent 追问用户（前端显示追问，等待输入） |
| `thinking` | Agent 正在推理（可选，展示思考过程） |
| `token` | LLM 生成文本 token |
| `visit_summary` | 就诊摘要已生成 |
| `done` | 对话结束 |
| `error` | 异常 |

---

## 八、数据准备

### 宠物疾病知识库

覆盖犬猫常见疾病，每篇包含：
- 疾病名称、病因、典型症状、鉴别诊断
- 居家护理方案、需就医指征
- 数据来源：《宠物常见疾病诊疗手册》等公开资料

### 宠物用药数据库

结构化数据，每条包含：
- 药品名称、适用物种、剂量公式
- 禁忌品种、药物相互作用
- 数据来源：《兽药典》《宠物用药指南》
