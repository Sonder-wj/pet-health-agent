# 宠物营养 Vue 前端适配 — 纲要(Plan 3 / 3)

> Plan 1 引擎 + Plan 2 Agent 已完成。本计划把前端从医疗问诊 UI 翻新为营养评估管家 UI。

**Goal:** Vue 3 SPA 接好新 SSE 事件(`assessment` / `report`),让用户能输入宠物档案 + 饮食,看到结构化营养评估报告,完成端到端 demo。

**核心思路:** 对话仍是主交互(Agent 自己追问采集),前端只新增**可视化呈现** + **结构化输入快捷入口**,不抢 Agent 的对话主导权。

---

## 范围

**In:**
- 新增 4 个组件:`PetProfileCard`(右侧栏展示档案累积) / `DietInputHelpers`(chat 内快捷按钮) / `AssessmentCard`(评估结果可视化) / `MarkdownReport`(渲染最终报告)。
- SSE 事件处理改:删 `triage`/`question`/`visit_summary` → 加 `assessment`/`report`。
- store(`chat.js`) 字段重命名,加 `assessment`/`reportMd`/`petProfile` 等状态。
- 新增依赖:`marked`(轻量 Markdown → HTML)。
- 删除/改造:`VisitSummary.vue`(删) / `AgentTracePanel.vue` + `utils/agentTrace.js`(精简到只显示工具调用轨迹) / `WelcomeScreen.vue` 文案。
- 构建 → 复制 `frontend/dist/` 到 `static/`。

**Out:** 
- 雷达图/charts.js 等可视化库(用 CSS 进度条 + 卡片代替,先保 demo bundle 小)。
- PDF 导出按钮(MVP 只做"复制 Markdown")。
- 单测(项目无 vitest,Plan 3 走 manual smoke,后续可补)。

---

## 文件清单

### 新增

| 文件 | 单行职责 |
|------|----------|
| `src/components/PetProfileCard.vue` | 显示当前已收集的 pet_profile(species/weight/age/conditions/allergens),空字段灰显 |
| `src/components/DietInputHelpers.vue` | chat 输入框上方的两个快捷按钮:"📷 上传包装" / "🍱 自制饮食模板"(后者插入引导文本到输入框) |
| `src/components/AssessmentCard.vue` | 接 `assessment` 事件 → 渲染能量平衡条 + 营养素卡片 + findings 列表(色码:red=critical / yellow=warning / blue=info) |
| `src/components/MarkdownReport.vue` | 接 `report` 事件 → `marked.parse(content)` 渲染 + "复制 Markdown" 按钮 |

### 修改

| 文件 | 改动 |
|------|------|
| `src/stores/chat.js` | state: 加 `petProfile/assessment/reportMd`;handlers: 改 SSE 事件分派;删 `triage/question/visitSummary` 相关 |
| `src/views/Chat.vue` | 引入新 4 组件;assistant 消息流附近渲染 AssessmentCard + MarkdownReport;右栏挂 PetProfileCard |
| `src/components/AppSidebar.vue` | 主题/copy 改营养向(项目名、副标题) |
| `src/components/ChatInput.vue` | 改提示语 "上传商品粮包装照";接入 DietInputHelpers 快捷按钮 |
| `src/components/WelcomeScreen.vue` | 文案换营养评估,示例 prompt 换"我家 10kg 拉布拉多每天 300g 鸡胸,可以吗?" |
| `src/components/MessageBubble.vue` | 可能微调样式(若需要),否则不改 |
| `src/utils/agentTrace.js` | 精简:只保留"工具调用 → 显示工具名"逻辑,删除分诊/追问相关 case |
| `src/components/AgentTracePanel.vue` | 跟上述 agentTrace.js 一起精简或最小化 |
| `package.json` | 加 `"marked": "^14.x"` |

### 删除

| 文件 | 原因 |
|------|------|
| `src/components/VisitSummary.vue` | 医疗就诊摘要,营养向不需要 |

---

## 集成顺序

```
1. 依赖: npm install marked
2. store/chat.js 重构(SSE 事件 + 新 state 字段)
3. 4 个新组件
4. Chat.vue + ChatInput.vue + WelcomeScreen.vue 整合
5. 旧组件清理(VisitSummary 删 + AgentTracePanel 精简)
6. npm run build → copy dist/* 到 static/
7. Manual smoke: uvicorn 启动 + 浏览器跑一遍完整流(profile → diet → assessment → report)
```

**为什么先 store 再组件:** store 是新组件的数据源,先定字段才好写消费者;反过来会反复改 store。

---

## SSE 事件契约(后端已落定)

```
thinking     → 显示 "小宠营养师正在评估..."
token        → 流式追加到当前 assistant 消息
tool_call    → 显示工具名 + 简短参数预览
tool_result  → 显示工具摘要
assessment   → { type: "assessment", data: { energy, nutrients, findings } }
                → 渲染 AssessmentCard
report       → { type: "report", markdown: "..." }
                → 渲染 MarkdownReport
done         → 隐藏 thinking
error        → 显示错误 toast
```

`assessment.data` 字段细节:
- `energy: { rer, mer, intake_kcal, balance_pct }`
- `nutrients: [{ nutrient, actual, target_min, target_max, unit, status }]`
- `findings: [{ code, nutrient, severity, message, actual, target_min, target_max, unit }]`

---

## AssessmentCard 视觉设计(MVP)

```
┌─────────────────────────────────────────┐
│ 📊 营养评估                              │
├─────────────────────────────────────────┤
│ 能量平衡                                 │
│ 摄入 495 / 目标 630 kcal  ▓▓▓▓▓▓▓░░ 78% │
│ 偏差 -21.4%  → ⚠️ 略低                   │
├─────────────────────────────────────────┤
│ 关键营养素                               │
│ 钙     30 mg/1000kcal  / 目标 1250 🔴   │
│ 磷    460 mg/1000kcal  / 目标 1000 🟡   │
│ 蛋白质 62 g/1000kcal   / 目标 45  🟢    │
├─────────────────────────────────────────┤
│ 发现                                     │
│ 🔴 钙严重不足(actual < 50% 目标)         │
│ 🔴 钙磷比倒置 Ca:P = 0.07                │
│ ⚠️  热量摄入偏低 -21%                     │
└─────────────────────────────────────────┘
```

色码:🔴=critical / 🟡=warning / 🟢=ok。用 CSS 进度条 + flex 卡片实现,不引入 chart 库。

---

## 风险与决策

| 风险 | 决策 |
|------|------|
| Vue/Pinia/Router 已有版本 vs marked 新增 | 只加 marked(轻量、无依赖);其余版本不动 |
| 旧 stores/chat.js SSE 代码盘根错节 | 直接重写整个 handler(写新比改旧更清晰)。原始 `messages` 状态保留兼容旧消息泡 |
| `marked` 默认会渲染原始 HTML(XSS 风险) | report 内容来自我们自己的 Agent,信任源;若担心可加 `DOMPurify`,MVP 跳过 |
| 旧 static/* 文件名带 hash,新构建 hash 变 → 老缓存 | 让 npm run build 自然替换,FastAPI 不缓存 index.html 即可(已是默认) |

---

## 任务划分

按集成顺序,5 个执行任务:

- **F-T1** — 依赖安装(marked) + `stores/chat.js` SSE handler 重构 + 新字段。
- **F-T2** — 4 个新组件(PetProfileCard / DietInputHelpers / AssessmentCard / MarkdownReport)。
- **F-T3** — Chat.vue / ChatInput.vue / WelcomeScreen.vue 整合新组件 + 文案调整。
- **F-T4** — 删 VisitSummary.vue,精简 AgentTracePanel + agentTrace.js,AppSidebar 文案。
- **F-T5** — `npm run build` + 把 `frontend/dist/*` 复制到 `static/`(覆盖旧构建产物),浏览器手动 smoke。
