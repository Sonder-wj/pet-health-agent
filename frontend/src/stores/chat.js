import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { streamChat, streamResume, apiGet } from '../api/client'
import { summarizeArgs, summarizeText, toolLabel } from '../utils/agentTrace'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const activeThreadId = ref(null)
  const messages = reactive([])
  const isStreaming = ref(false)
  const streamingText = ref('')
  const toolCalls = reactive([])
  const agentTrace = reactive([])

  // 营养 Agent 状态
  const petProfile = ref({})       // 后端 state.pet_profile;MVP 仅从对话中累积,前端不直接编辑

  const error = ref(null)
  const thinking = ref(false)

  let finalAnswerFallback = ''
  let tokenStarted = false
  let traceId = 0
  // 当前轮次累积的 assessment / report;turn 结束时附加到 assistant 消息上,
  // 这样它们成为消息历史的一部分,不会"漂浮"在所有消息底下。
  let currentAssessment = null
  let currentReportMd = ''

  const currentTitle = computed(() => {
    const conversation = conversations.value.find(item => item.thread_id === activeThreadId.value)
    return conversation ? conversation.title : '新对话'
  })

  async function loadHistory() {
    try {
      const res = await apiGet('/api/history')
      const data = await res.json()
      conversations.value = data.conversations || []
    } catch {
      conversations.value = []
    }
  }

  async function loadThread(threadId) {
    try {
      const res = await apiGet(`/api/history/${threadId}`)
      const data = await res.json()
      if (data.messages) {
        messages.splice(0, messages.length, ...data.messages.map(message => ({
          sender: message.sender,
          content: message.content,
          type: message.type,
          time: message.time,
        })))
      }
    } catch {
      messages.length = 0
    }
  }

  function resetSession() {
    activeThreadId.value = null
    messages.length = 0
    streamingText.value = ''
    toolCalls.length = 0
    agentTrace.length = 0
    petProfile.value = {}
    error.value = null
    thinking.value = false
    finalAnswerFallback = ''
    tokenStarted = false
    traceId = 0
    currentAssessment = null
    currentReportMd = ''
  }

  /**
   * 切账号 / 登出时调用 — 清掉所有"个人数据",
   * 包括侧栏会话列表,防止 A 的记录漂到 B 的页面。
   */
  function clearAccountData() {
    conversations.value = []
    resetSession()
  }

  async function sendMessage(query, imageFile) {
    if (isStreaming.value) return

    error.value = null
    thinking.value = true
    isStreaming.value = true
    streamingText.value = ''
    toolCalls.length = 0
    agentTrace.length = 0
    // 不清 petProfile — 跨轮累积
    finalAnswerFallback = ''
    tokenStarted = false
    // 新一轮的 assessment/report 从空开始;旧的已经附在上轮的 assistant 消息里了
    currentAssessment = null
    currentReportMd = ''

    messages.push({ sender: 'user', content: query, type: 'text' })
    messages.push({ sender: 'assistant', content: '', type: 'streaming', _placeholder: true })

    const abortController = new AbortController()
    const hasSession = !!activeThreadId.value

    try {
      const res = hasSession
        ? await streamResume({ sessionId: activeThreadId.value, query, imageFile, signal: abortController.signal })
        : await streamChat({ query, sessionId: null, imageFile, signal: abortController.signal })

      if (!activeThreadId.value) {
        activeThreadId.value = res.headers.get('X-Session-ID') || ''
      }

      if (!res.ok) {
        error.value = `服务端错误 (${res.status})`
      } else {
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const event = JSON.parse(line.slice(6))
              handleSSEEvent(event)
            } catch {
              // Ignore malformed SSE lines.
            }
          }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        error.value = '连接中断,请重试'
        appendTraceStep({
          kind: 'thinking',
          status: 'done',
          title: '本次处理被中断',
          summary: '和后端的流式连接中断了,没能完整拿到这次执行结果。',
        })
      }
    }

    isStreaming.value = false
    thinking.value = false
    finalizeRunningTraceSteps()

    const finalContent = streamingText.value || finalAnswerFallback
    const assistantContent = (finalContent || '').trim()
    const placeholderIdx = messages.findIndex(message => message._placeholder)

    if (placeholderIdx >= 0) {
      if (assistantContent) {
        messages.splice(placeholderIdx, 1, {
          sender: 'assistant',
          content: assistantContent,
          type: 'text',
          assessment: currentAssessment,  // 嵌入到这条消息,而不是全局漂浮
          report: currentReportMd || null,
        })
      } else {
        messages.splice(placeholderIdx, 1)
      }
    } else if (assistantContent) {
      messages.push({
        sender: 'assistant',
        content: assistantContent,
        type: 'text',
        assessment: currentAssessment,
        report: currentReportMd || null,
      })
    }
  }

  function handleSSEEvent(event) {
    switch (event.type) {
      case 'thinking':
        thinking.value = true
        appendTraceStep({
          kind: 'thinking',
          status: 'running',
          title: '正在思考',
          summary: summarizeText(event.msg || 'Agent 正在理解需求并规划下一步行动。'),
        })
        break

      case 'token': {
        thinking.value = false
        markThinkingComplete()

        if (!tokenStarted) {
          tokenStarted = true
          if (finalAnswerFallback) {
            streamingText.value = ''
          }
        }

        streamingText.value += event.content

        const placeholder = messages.find(message => message._placeholder)
        if (placeholder) {
          placeholder.content = streamingText.value
        }
        break
      }

      case 'tool_call': {
        thinking.value = false
        markThinkingComplete()

        const traceEntry = {
          id: nextTraceId('tool'),
          kind: 'tool',
          tool: event.tool,
          status: 'running',
          title: `调用 ${toolLabel(event.tool)}`,
          summary: 'Agent 正在执行这个工具步骤。',
          argsPreview: summarizeArgs(event.args),
          resultPreview: '',
        }

        toolCalls.push({
          tool: event.tool,
          args: event.args,
          status: 'running',
          summary: null,
          traceId: traceEntry.id,
        })
        agentTrace.push(traceEntry)
        break
      }

      case 'tool_result': {
        const activeTool = [...toolCalls].reverse().find(item => item.status === 'running')
        const activeTrace = activeTool
          ? agentTrace.find(step => step.id === activeTool.traceId)
          : [...agentTrace].reverse().find(step => step.kind === 'tool' && step.status === 'running')

        if (activeTool) {
          activeTool.status = 'done'
          activeTool.summary = event.summary
        }

        if (activeTrace) {
          activeTrace.status = 'done'
          activeTrace.summary = `已完成 ${toolLabel(event.tool)}`
          activeTrace.resultPreview = summarizeText(event.summary || '工具已返回结果。', 180)
        }

        if (event.tool === 'final_answer') {
          finalAnswerFallback = event.summary || ''
        }
        break
      }

      case 'assessment':
        currentAssessment = event.data || null
        appendTraceStep({
          kind: 'tool',
          status: 'done',
          title: '已生成营养评估',
          summary: '能量平衡、营养素密度、关键发现已经准备好。',
          resultPreview: currentAssessment
            ? `${currentAssessment.findings?.length || 0} 项 findings`
            : '',
        })
        break

      case 'report':
        currentReportMd = event.markdown || ''
        appendTraceStep({
          kind: 'tool',
          status: 'done',
          title: '已渲染最终报告',
          summary: 'Markdown 报告将随这条消息保留在对话历史中。',
          resultPreview: summarizeText(currentReportMd, 180),
        })
        break

      case 'error':
        error.value = event.message
        appendTraceStep({
          kind: 'thinking',
          status: 'done',
          title: '处理过程中出现错误',
          summary: summarizeText(event.message, 180),
        })
        break

      case 'done':
        markThinkingComplete()
        finalizeRunningTraceSteps()
        break
    }
  }

  function appendTraceStep(step) {
    agentTrace.push({
      id: step.id || nextTraceId(step.kind || 'step'),
      kind: step.kind || 'thinking',
      status: step.status || 'done',
      title: step.title || '处理中',
      summary: step.summary || '',
      argsPreview: step.argsPreview || '',
      resultPreview: step.resultPreview || '',
      tool: step.tool || '',
    })
  }

  function markThinkingComplete() {
    const runningThinking = [...agentTrace].reverse().find(step => step.kind === 'thinking' && step.status === 'running')
    if (runningThinking) {
      runningThinking.status = 'done'
      if (!runningThinking.summary) {
        runningThinking.summary = '思考结束,开始执行下一步。'
      }
    }
  }

  function finalizeRunningTraceSteps() {
    agentTrace.forEach(step => {
      if (step.status === 'running') {
        step.status = 'done'
        if (!step.resultPreview && step.kind === 'tool') {
          step.resultPreview = '工具步骤已结束。'
        }
      }
    })

    toolCalls.forEach(tool => {
      if (tool.status === 'running') {
        tool.status = 'done'
      }
    })
  }

  function nextTraceId(prefix) {
    traceId += 1
    return `${prefix}-${Date.now()}-${traceId}`
  }

  return {
    conversations,
    activeThreadId,
    messages,
    isStreaming,
    streamingText,
    toolCalls,
    agentTrace,
    petProfile,
    error,
    thinking,
    currentTitle,
    loadHistory,
    loadThread,
    resetSession,
    clearAccountData,
    sendMessage,
  }
})
