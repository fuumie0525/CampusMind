const DEFAULT_BASE_URL = import.meta.env.VITE_CAMPUSMIND_API_URL || '/api/campusmind'
const SETTINGS_KEY = 'campusmind.frontend.settings'

export function createInitialSettings() {
  const saved = readSettings()
  return {
    endpoint: saved.endpoint || DEFAULT_BASE_URL,
    userId: saved.userId || 'student_1001',
    conversationId: saved.conversationId || ''
  }
}

export function saveSettings(settings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
}

export async function requestHealth(settings) {
  return requestJson(settings.endpoint, '/health')
}

export async function requestMonitor(settings) {
  return requestJson(settings.endpoint, '/monitor')
}

export async function requestKnowledgeStats(settings) {
  return requestJson(settings.endpoint, '/knowledge/stats')
}

export async function requestSearch(settings, query, topK = 5) {
  const params = new URLSearchParams({ query, top_k: String(topK) })
  return requestJson(settings.endpoint, `/search?${params}`, { method: 'POST' })
}

export async function requestChat(settings, message) {
  const raw = await requestJson(settings.endpoint, '/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      user_id: settings.userId || 'anonymous',
      conv_id: settings.conversationId || undefined
    })
  })
  return normalizeChatResponse(raw)
}

export async function addKnowledge(settings, documents) {
  return requestJson(settings.endpoint, '/knowledge/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ documents })
  })
}

export async function uploadKnowledge(settings, file) {
  const form = new FormData()
  form.append('file', file)
  return requestJson(settings.endpoint, '/knowledge/upload', {
    method: 'POST',
    body: form
  })
}

function normalizeChatResponse(raw) {
  return {
    conversationId: raw.conv_id || raw.conversation_id || raw.conversationId || '',
    response: raw.response || '',
    intent: raw.intent || 'other',
    agentType: raw.agent_type || raw.agentType || '',
    escalated: Boolean(raw.escalated),
    latencyMs: Number(raw.latency_ms ?? raw.latencyMs ?? 0),
    knowledgeUsed: Boolean(raw.knowledge_used ?? raw.knowledgeUsed),
    toolsUsed: Array.isArray(raw.tools_used) ? raw.tools_used : []
  }
}

async function requestJson(baseUrl, path, options = {}) {
  const url = `${normalizeBaseUrl(baseUrl)}${path}`
  const response = await fetch(url, options)
  const text = await response.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!response.ok) {
    const detail = typeof data === 'string' ? data : JSON.stringify(data)
    throw new Error(`${response.status} ${response.statusText}: ${detail}`)
  }
  return data
}

function normalizeBaseUrl(value) {
  return String(value || '').replace(/\/+$/, '')
}

function readSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')
  } catch {
    return {}
  }
}
