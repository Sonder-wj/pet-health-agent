# 宠物营养配餐管家 — 设计文档

> 状态:设计已确认,待写实现计划
> 日期:2026-05-29
> 性质:对现有 `pet-health-agent` 的重构

---

## 1. 背景与目标

### 1.1 问题

现有 `pet-health-agent` 是单 ReAct Agent + 7 个工具。问题在于:**多数工具本质是"换了 prompt 的 LLM 调用"**(症状追问、图片分析、就诊摘要、final_answer),只有 3 个是真实工具(Milvus 检索、药物 JSON 查询+剂量计算、DB 症状记录)。因此整个系统"一个大模型 + 好的 system prompt 就能解决",体现不出 Agent 的价值。

### 1.2 重构方向

转向**宠物营养配餐管家**,核心场景是**评估现有饮食**。选择这个方向的理由:

1. **不是 LLM 能可靠完成的** —— 营养学计算(能量需求、营养素加总、达标判断)需要精确数值,LLM 估算不稳定。
2. **不是单纯记忆/数据库** —— 是真计算,不是把对话历史塞回上下文。
3. **数据可证明** —— 基于 NRC/AAFCO/FEDIAF/USDA 等**公开权威标准**,且核心是"执行标准算法"而非"编纂事实库",实现对了输出就天然正确。
4. **补齐作品集缺口** —— 引入多模态(标签识别);现有两个项目(FitChef RAG、灵犀智购多 Agent)都没有视觉能力。

### 1.3 核心设计原则

**把"只有 LLM 能做的"和"必须可靠计算的"彻底分离:**
- LLM(Agent 层):理解杂乱自然语言输入、信息不足时追问、动态编排、把结构化结果讲成人话。
- 纯 Python(营养引擎):所有营养学数学,零 LLM 依赖,可独立穷举单测,结果确定、可复现、可证明。

---

## 2. 产品范围

### 2.1 In Scope

| 维度 | 范围 |
|------|------|
| 核心场景 | 评估用户现有饮食 |
| 饮食类型 | 商品粮(份量/热量评估)+ 自制鲜食(全营养素分析) |
| 物种 | 猫 + 狗 |
| 疾病约束 | 肾病(CKD)、肥胖、糖尿病、食物过敏 |
| 多模态 | 拍商品粮标签 → 视觉提取保证成分分析数据 |
| 交付物 | 结构化营养评估报告(含改进建议) |

### 2.2 Out of Scope(非目标)

- 从零生成自制食谱(约束优化求解)—— 列为未来扩展。
- 商品粮品牌数据库 —— 不维护,商品粮数据来自用户拍的标签。
- 急诊/疾病诊断 —— 删除原医疗问诊能力。
- 营养知识问答 RAG —— 列为未来可选模块。
- 自动下单/购买推荐 —— 不做。

### 2.3 边界声明

本系统是**决策支持 Demo,非医疗器械**。只精选常见食材/标准子集(约 100–200 种食材),不声称全面。所有输出附数据来源与免责声明,提示最终应咨询执业兽医/宠物营养师。

---

## 3. 架构总览

```
┌─────────────────────────────────────────────┐
│  ReAct Agent 层(LLM)                         │
│  职责:理解输入、追问、编排、解释结果             │
│  - 解析自然语言/标签图 → 结构化饮食              │
│  - 检查档案完整性 → 缺啥追问啥                   │
│  - 决定走商品粮/自制路径、按疾病触发检查           │
└───────────────────┬─────────────────────────┘
                    │ 传入结构化数据,调用工具
                    ▼
┌─────────────────────────────────────────────┐
│  营养引擎(纯 Python,零 LLM,可独立单测)         │
│  energy → nutrient_analysis → requirements    │
│         → constraints → allergens → evaluate   │
│  输入:结构化档案 + 结构化饮食                    │
│  输出:结构化评估结果(NutritionAssessment)      │
└─────────────────────────────────────────────┘
```

**硬约束:营养引擎不依赖任何 LLM,输入输出都是结构化数据。** LLM 只出现在引擎的上游(理解输入)和下游(解释结果)。

---

## 4. 营养引擎设计(`app/engine/`)

纯 Python 包,6 个模块。每个模块职责单一、可独立测试。

### 4.1 `energy.py` — 能量需求

```
RER(静息能量需求)= 70 × (体重_kg)^0.75      # 猫狗同构
MER(维持能量需求)= RER × 系数              # 系数按物种/生理状态查表
```

MER 系数(来源 FEDIAF / WSAVA / NRC,精选常用项):

| 状态 | 狗 | 猫 |
|------|-----|-----|
| 绝育成年 | 1.6 | 1.2 |
| 未绝育成年 | 1.8 | 1.4 |
| 减重(按目标体重算) | 1.0 | 0.8 |
| 幼年(断奶后) | 2.0 | 2.5 |
| 老年 | 1.4 | 1.1 |

疾病覆盖:肥胖 → 强制用减重系数;输出每日推荐 kcal 区间。

### 4.2 `nutrient_analysis.py` — 营养素分析

- **自制路径**:对每个食材 → 查 USDA 子集得每 100g 营养谱 → 按份量缩放 → 跨食材加总。
- **商品粮路径**:用标签的保证成分分析 + kcal;若标签无 kcal,用修正 Atwater 系数从三大营养素反推。
- **湿重→干物质换算(DMB)**:`干物质营养% = 营养% / (100 − 水分%) × 100`,统一到干物质基础后才能与标准对比。
- 输出:总 kcal + 关键营养素总量。

跟踪的关键营养素(精选临床最相关的,非穷举):
- 能量(kcal)、粗蛋白、粗脂肪
- 钙、磷、**Ca:P 比值**(自制全肉饮食经典失败点 → 继发性甲旁亢)
- **牛磺酸**(猫专项,自制猫饭经典失败点 → 扩张型心肌病)
- 钠(肾病相关)、粗纤维、碳水(NFE)

### 4.3 `requirements.py` — 营养需求标准

- 来源:AAFCO 营养标准 + FEDIAF 指南,按**物种 × 生理阶段**(生长/繁殖 vs 成年维持)给出每单位能量的推荐摄入(RA)与最低需求。
- 输出:该宠物各营养素的目标范围。

### 4.4 `constraints.py` — 疾病约束

按疾病覆盖/收紧目标值:

| 疾病 | 约束 | 来源 |
|------|------|------|
| 肾病 CKD | 限磷(按 IRIS 分期给目标)、中等优质蛋白、限钠 | IRIS / WSAVA |
| 肥胖 | 强制减重热量、提高纤维、降低脂肪 | WSAVA |
| 糖尿病 | 猫:高蛋白低碳水;狗:复合碳水高纤维、定时定量 | WSAVA |
| 食物过敏 | 成分排除检查(非营养素目标) | 见 4.5 |

输出:调整后的目标 + 触发的约束标记。

### 4.5 `allergens.py` — 过敏原检查

- 常见食物过敏原表:鸡、牛、乳制品、蛋、小麦/麸质、大豆、羊、鱼、玉米。
- 比对饮食成分 vs 宠物已知过敏原 → 返回冲突项。

### 4.6 `evaluate.py` — 综合评估

- 实际摄入 vs 目标 → 计算每项营养素的缺口/超标百分比。
- 汇总结构化发现:能量平衡(过/欠喂 %)、营养素缺超、Ca:P 失衡、牛磺酸缺乏(猫)、疾病约束违规、过敏原冲突。
- 每条发现带严重度(info / warning / critical)。
- 返回 `NutritionAssessment` 结构化对象。

---

## 5. Agent 工具层(`app/agent/tools/`)

工具只做两件事:**取 LLM 没有的数据**,或**调用确定性引擎**。解析饮食这类"理解类"工作是 Agent 自身推理,不设工具。

| 工具 | 类型 | 职责 | 关键点 |
|------|------|------|--------|
| `extract_label_nutrition(image)` | 视觉/取数据 | 拍商品粮标签 → 提取粗蛋白/脂肪/纤维/水分/kcal/成分表 | 多模态入口 |
| `lookup_ingredient(name)` | USDA 查询/取数据 | 食材名 → USDA 每 100g 营养谱;查不到返回 `not_found` | not_found 触发追问循环 |
| `compute_energy_requirement(profile)` | 引擎/计算 | → RER、MER、每日推荐 kcal | 确定性 |
| `assess_nutrition(profile, diet, conditions, allergens)` | 引擎/计算 | 跑完整 6 模块 → 结构化评估 | 引擎主入口,确定性 |
| `final_answer(report)` | 终止 | 把结构化评估讲成人话报告 | 复用现有 |

---

## 6. 状态与编排流程

### 6.1 AgentState(`app/agent/state.py`)

```python
class PetProfile(TypedDict, total=False):
    species: str              # cat / dog
    breed: str
    weight_kg: float
    age_months: int
    neutered: bool
    activity_level: str       # sedentary / normal / active
    conditions: list[str]     # ["kidney", "diabetes", "obesity", ...]
    allergens: list[str]      # ["chicken", "beef", ...]

class DietItem(TypedDict, total=False):
    name: str
    amount_g: float
    kind: str                 # ingredient / commercial

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    pet_profile: PetProfile
    parsed_diet: list[DietItem]
    diet_kind: str                   # commercial / homemade / mixed
    label_data: dict | None          # 视觉提取结果
    unresolved_ingredients: list     # 查不到的食材 → 追问
    missing_profile_fields: list     # 还缺的档案字段 → 追问
    assessment: dict | None          # 引擎输出
    awaiting_user_input: bool
    pending_question: str | None
    final_response: str | None
```

### 6.2 编排流程

```
1. 用户输入(文本 + 可选图片)
2. [有图] extract_label_nutrition → 商品粮数据
3. Agent 自行解析饮食 → 结构化 DietItem[],判断 diet_kind
4. [自制] 对每个食材 lookup_ingredient
       └─ 查不到 → awaiting_user_input,追问("鸡肉是鸡胸还是鸡腿?")
5. Agent 检查档案完整性(体重/年龄/活动量/疾病/过敏)
       └─ 缺关键字段 → awaiting_user_input,追问
6. 数据齐 → compute_energy_requirement + assess_nutrition
7. final_answer → 分级报告
```

**步骤 4、5 的两个追问循环是 Agent 真正"动态"之处**:要补几轮信息、走哪条路径,开跑前不可知,无法写成固定流水线 —— 这是 ReAct 不可替代的理由。

### 6.3 图改动

复用现有 LangGraph ReAct 骨架,但:
- **删除** `triage_node`、`er_response_node` 及其分支。
- 入口直接进 `agent` 节点。
- 保留 `agent ↔ tools` 循环、`awaiting_user_input` 暂停机制、SqliteSaver checkpointer。

---

## 7. 多模态:标签识别

- 用户上传商品粮包装照片(保证成分分析面板)。
- `extract_label_nutrition` 用视觉模型读取面板 → 结构化 `{crude_protein_pct, crude_fat_pct, crude_fiber_pct, moisture_pct, kcal_per_kg?, ingredients[]}`。
- 标签常不印 kcal → 引擎用修正 Atwater 系数从三大营养素反推。
- 复用 `chat.py` 中已有的 SSE 多模态消息构建逻辑(base64 image_url)。
- **定位**:视觉只做"数据提取",核心计算仍是确定性引擎 —— 不掉进"这不就是模型调用"的质疑。

---

## 8. 数据来源与可证明性

全部使用**免费可下载、权威可引用**的来源,避开网络搜索的质量问题:

| 数据 | 来源 | 性质 |
|------|------|------|
| 食材成分(自制) | USDA FoodData Central | 美国政府库,免费,每条带 FDC ID |
| 营养需求标准 | AAFCO 营养标准 + FEDIAF 指南 | 免费可下;AAFCO 是美国宠粮标签事实标准 |
| 能量系数(MER) | FEDIAF / WSAVA | 免费公开 |
| 疾病约束 | IRIS(肾病分期)+ WSAVA 营养指南 | 免费在线 |
| 过敏原表 | 兽医皮肤病学常见过敏原 | 文献整理 |

**provenance 设计**:每个数据文件(`data/*.json`)带 `source / version / review_date` 元信息,逐条记录来源 ID(如 USDA FDC ID)。Agent 回答时附上出处。

---

## 9. 评估报告结构(交付物)

```
① 宠物档案摘要
② 能量评估     当前摄入 vs MER,过/欠喂百分比
③ 营养素评估    表格:营养素 | 当前 | 目标 | 状态(达标/缺/超)
④ 疾病约束检查  如肾病猫 → 磷是否超标
⑤ 过敏原检查    饮食成分 vs 已知过敏原冲突
⑥ 风险提示 + 改进建议(按优先级 critical → warning → info)
⑦ 数据来源 + 免责声明
```

②③④⑤ 全部来自引擎结构化输出,LLM 只负责通俗化表达。

---

## 10. 从现有代码迁移

**复用(骨架基本不动):**
- FastAPI / SSE 流式 / 中间件 / 日志
- JWT 鉴权 / MySQL 持久化(Conversation、Message)/ 前端壳
- LangGraph ReAct 骨架(图结构、checkpointer)、SSE 多模态消息构建
- `medication_guide` 的"读 JSON + 确定性计算"实现**模式**作为新引擎工具的范本(借鉴写法,文件本身在"删除"项中移除)

**删除:**
- 医疗工具:triage、collect_symptoms、analyze_pet_image、search_pet_knowledge、medication_guide、track_symptoms、generate_visit_summary
- `triage_node` / `er_response_node` 及分支
- **Milvus / Ollama embedding / `app/rag/`**(核心流程是结构化查表+计算,不需要向量检索)
- `SymptomLog` 模型(改用营养评估相关持久化,或暂不持久化结构化结果)

**新增:**
- `app/engine/` — 营养引擎 6 模块
- `data/` — USDA 子集 / AAFCO-FEDIAF 需求 / MER 系数 / 疾病约束 / 过敏原(均带 provenance)
- 新工具:extract_label_nutrition、lookup_ingredient、compute_energy_requirement、assess_nutrition
- 新 system prompt(营养领域)

**配置变更:** 移除 `MILVUS_*`、`OLLAMA_*`、`EMBEDDING_THRESHOLD`;保留 `OPENAI_*`、`DB_*`、`SECRET_KEY`、`CHECKPOINT_DB_PATH`。

---

## 11. 测试策略(可证明性的兑现)

**引擎黄金测试** —— 用教科书算例做断言:

```python
def test_rer_neutered_cat_5kg():
    assert compute_rer(5.0) == pytest.approx(234, abs=1)
    assert compute_mer(5.0, "cat", state="neutered_adult") == pytest.approx(281, abs=2)

def test_dmb_conversion():
    # 粗蛋白 10% as-fed,水分 78% → 干物质蛋白 45.5%
    assert to_dmb(10.0, moisture_pct=78.0) == pytest.approx(45.5, abs=0.1)

def test_homemade_allmeat_low_calcium_flagged():
    result = assess(profile_adult_dog, diet_all_chicken_breast)
    assert any(f.nutrient == "calcium" and f.severity == "critical" for f in result.findings)
    assert any(f.code == "ca_p_ratio_inverted" for f in result.findings)

def test_kidney_cat_high_phosphorus_flagged():
    result = assess(profile_kidney_cat, diet_high_phosphorus)
    assert any(f.nutrient == "phosphorus" and f.severity == "critical" for f in result.findings)

def test_homemade_cat_taurine_deficiency_flagged():
    result = assess(profile_adult_cat, diet_no_taurine_source)
    assert any(f.nutrient == "taurine" for f in result.findings)
```

**这套测试本身就是"数据准确性"的证明** —— 引擎输出对得上公开标准的算例。

**Agent/集成测试**:饮食解析边界、追问循环触发(查不到食材 / 缺档案字段)、商品粮 vs 自制路径分流。

---

## 12. 未来扩展(非本期)

- 从零生成营养均衡的自制食谱(约束优化)。
- 营养知识问答 RAG 模块(解释"为什么肾病要限磷")。
- 跨会话营养趋势追踪(体重/饮食变化曲线)。
- 更多疾病(胰腺炎、心脏病、尿结石)。

---

## 13. 风险与边界

| 风险 | 应对 |
|------|------|
| 食材库覆盖不全 | 明确只做常见子集;查不到时追问或建议替代,绝不编造数据 |
| 标签识别出错 | 提取后回显给用户确认关键数值,再进计算 |
| 用户误当医疗诊断 | 每份报告强制附免责声明 + 建议咨询执业兽医 |
| 营养标准的地区差异 | 标注采用 AAFCO/FEDIAF,说明标准出处 |
```
