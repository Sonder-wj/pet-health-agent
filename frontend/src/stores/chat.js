import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { streamChat, streamResume, apiGet } from '../api/client'
import { summarizeArgs, summarizeText, toolLabel, triageLevelLabel } from '../utils/agentTrace'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const activeThreadId = ref(null)
  const messages = reactive([])
  const isStreaming = ref(false)
  const streamingText = ref('')
  const toolCalls = reactive([])
  const agentTrace = reactive([])
  const triageLevel = ref(null)
  const pendingQuestion = ref(null)
  const visitSummary = ref(null)
  const error = ref(null)
  const thinking = ref(false)

  let finalAnswerFallback = ''
  let tokenStarted = false
  let traceId = 0

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
    triageLevel.value = null
    pendingQuestion.value = null
    visitSummary.value = null
    error.value = null
    thinking.value = false
    finalAnswerFallback = ''
    tokenStarted = false
    traceId = 0
  }

  async function sendMessage(query, imageFile) {
    if (isStreaming.value) return

    const shouldResume = pendingQuestion.value !== null && activeThreadId.value

    error.value = null
    thinking.value = true
    isStreaming.value = true
    streamingText.value = ''
    toolCalls.length = 0
    agentTrace.length = 0
    triageLevel.value = null
    pendingQuestion.value = null
    visitSummary.value = null
    finalAnswerFallback = ''
    tokenStarted = false

    messages.push({ sender: 'user', content: query, type: 'text' })
    messages.push({ sender: 'assistant', content: '', type: 'streaming', _placeholder: true })

    const abortController = new AbortController()

    try {
      const res = shouldResume
        ? await streamResume({ sessionId: activeThreadId.value, query, signal: abortController.signal })
        : await streamChat({ query, sessionId: activeThreadId.value, imageFile, signal: abortController.signal })

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
        error.value = '连接中断，请重试'
        appendTraceStep({
          kind: 'thinking',
          status: 'done',
          title: '本次处理被中断',
          summary: '和后端的流式连接中断了，没能完整拿到这次执行结果。',
        })
      }
    }

    isStreaming.value = false
    thinking.value = false
    finalizeRunningTraceSteps()

    const finalContent = streamingText.value || finalAnswerFallback
    const assistantContent = buildAssistantMessageContent(finalContent, pendingQuestion.value, error.value)
    const placeholderIdx = messages.findIndex(message => message._placeholder)

    if (placeholderIdx >= 0) {
      if (assistantContent) {
        messages.splice(placeholderIdx, 1, {
          sender: 'assistant',
          content: assistantContent,
          type: 'text',
        })
      } else {
        messages.splice(placeholderIdx, 1)
      }
    } else if (assistantContent) {
      messages.push({ sender: 'assistant', content: assistantContent, type: 'text' })
    }
  }

  function handleSSEEvent(event) {
    switch (event.type) {
      case 'thinking':
        thinking.value = true
        appendTraceStep({
          kind: 'thinking',
          status: 'running',
          title: '正在分析用户问题',
          summary: summarizeText(event.msg || 'Agent 正在理解症状并规划下一步行动。'),
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

      case 'triage':
        triageLevel.value = event.level
        appendTraceStep({
          kind: 'triage',
          status: 'done',
          title: `完成分诊判断：${triageLevelLabel(event.level)}`,
          summary: '系统已根据当前描述给出这轮的紧急程度判断。',
        })
        break

      case 'question':
        pendingQuestion.value = event.message
        appendTraceStep({
          kind: 'thinking',
          status: 'done',
          title: '需要补充信息后继续',
          summary: summarizeText(event.message, 180),
        })

        if (event.message) {
          const placeholder = messages.find(message => message._placeholder)
          if (placeholder && !streamingText.value) {
            placeholder.content = event.message
          }
        }
        break

      case 'visit_summary':
        visitSummary.value = event.message
        appendTraceStep({
          kind: 'tool',
          status: 'done',
          title: '已生成就诊摘要',
          summary: '这份摘要可以直接给用户查看，也方便线下就诊时出示。',
          resultPreview: summarizeText(event.message, 180),
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
        runningThinking.summary = '分析完成，开始执行下一步。'
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

  function buildAssistantMessageContent(finalContent, pendingQuestionText, currentError) {
    if (currentError) return ''

    const reply = (finalContent || '').trim()
    const followUp = (pendingQuestionText || '').trim()

    if (reply && followUp) {
      return `${reply}\n\n补充确认：\n${followUp}`
    }

    return reply || followUp
  }

  return {
    conversations,
    activeThreadId,
    messages,
    isStreaming,
    streamingText,
    toolCalls,
    agentTrace,
    triageLevel,
    pendingQuestion,
    visitSummary,
    error,
    thinking,
    currentTitle,
    loadHistory,
    loadThread,
    resetSession,
    sendMessage,
  }
})
