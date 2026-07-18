<template>
  <main class="app-shell">
    <aside class="sidebar">
      <section class="brand">
        <div class="brand-mark">CM</div>
        <div>
          <h1>CampusMind</h1>
          <p>校园多 Agent 咨询服务系统</p>
        </div>
      </section>

      <section class="panel">
        <div class="panel-heading">
          <h2>服务配置</h2>
          <span class="pill">Python · FastAPI</span>
        </div>

        <label>
          <span>CampusMind API</span>
          <input v-model="settings.endpoint" @change="persist" placeholder="/api/campusmind" />
        </label>
        <label>
          <span>用户 ID</span>
          <input v-model="settings.userId" @change="persist" placeholder="student_1001" />
        </label>
        <label>
          <span>会话 ID</span>
          <input v-model="settings.conversationId" @change="persist" placeholder="首次对话自动生成" />
        </label>

        <div class="actions">
          <button @click="checkHealth">健康检查</button>
          <button @click="loadStats">刷新状态</button>
        </div>
      </section>

      <section class="panel status-panel">
        <div class="panel-heading">
          <h2>运行状态</h2>
          <span :class="['status-dot', healthOk ? 'online' : 'offline']"></span>
        </div>
        <dl>
          <div>
            <dt>后端服务</dt>
            <dd>CampusMind</dd>
          </div>
          <div>
            <dt>健康状态</dt>
            <dd :class="healthOk ? 'ok' : 'muted'">{{ healthLabel }}</dd>
          </div>
          <div>
            <dt>知识片段</dt>
            <dd>{{ knowledgeCount }}</dd>
          </div>
        </dl>
        <pre v-if="statusText">{{ statusText }}</pre>
      </section>
    </aside>

    <section class="workspace">
      <header class="workspace-header">
        <div>
          <span class="eyebrow">CampusMind Workspace</span>
          <h2>校园智能咨询</h2>
          <p>{{ settings.endpoint }}</p>
        </div>
        <div class="header-actions">
          <a :href="docsUrl" target="_blank" rel="noreferrer">API 文档</a>
        </div>
      </header>

      <section class="chat-panel">
        <div class="messages" ref="messageList">
          <article v-for="item in messages" :key="item.id" :class="['message', item.role]">
            <div class="message-meta">
              <span>{{ item.role === 'user' ? '学生用户' : 'CampusMind' }}</span>
              <small v-if="item.meta">{{ item.meta }}</small>
            </div>
            <p>{{ item.content }}</p>
          </article>

          <div v-if="messages.length === 0" class="empty-state">
            <h3>开始校园咨询</h3>
            <p>支持校园政策、学生事务、校园网络、校园卡和宿舍后勤等问题。</p>
            <div class="quick-prompts">
              <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="usePrompt(prompt)">
                {{ prompt }}
              </button>
            </div>
          </div>
        </div>

        <form class="composer" @submit.prevent="sendMessage">
          <textarea
            v-model="draft"
            rows="3"
            placeholder="输入问题，例如：校园网认证失败怎么办？"
          ></textarea>
          <button :disabled="busy || !draft.trim()">{{ busy ? '发送中' : '发送' }}</button>
        </form>
      </section>

      <section class="tools-grid">
        <article class="tool-panel">
          <div class="panel-heading">
            <h2>校园知识库检索</h2>
            <span class="pill soft">RAG</span>
          </div>
          <div class="inline-form">
            <input v-model="searchQuery" placeholder="在读证明怎么办理" />
            <button @click="searchKnowledge" :disabled="busy || !searchQuery.trim()">检索</button>
          </div>
          <div class="result-list">
            <article v-for="item in searchResults" :key="item.id || item.title" class="result-item">
              <strong>{{ item.title || '未命名结果' }}</strong>
              <span>score {{ item.score ?? '-' }}</span>
              <p>{{ item.content }}</p>
            </article>
          </div>
        </article>

        <article class="tool-panel">
          <div class="panel-heading">
            <h2>导入校园知识</h2>
            <span class="pill soft">Docs</span>
          </div>
          <label>
            <span>标题</span>
            <input v-model="docTitle" placeholder="校园网使用指南" />
          </label>
          <label>
            <span>内容</span>
            <textarea v-model="docContent" rows="5" placeholder="输入学校政策或办事流程内容"></textarea>
          </label>
          <div class="actions">
            <button @click="submitKnowledge" :disabled="busy || !docTitle.trim() || !docContent.trim()">添加文档</button>
            <label class="file-button">
              上传文件
              <input type="file" accept=".txt,.md,.json" @change="handleUpload" />
            </label>
          </div>
        </article>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import {
  addKnowledge,
  createInitialSettings,
  requestChat,
  requestHealth,
  requestKnowledgeStats,
  requestMonitor,
  requestSearch,
  saveSettings,
  uploadKnowledge
} from './lib/backends'

const settings = reactive(createInitialSettings())
const messages = ref([])
const draft = ref('')
const busy = ref(false)
const healthOk = ref(false)
const healthLabel = ref('未检查')
const statusText = ref('')
const knowledgeCount = ref('-')
const searchQuery = ref('在读证明怎么办理')
const searchResults = ref([])
const docTitle = ref('校园网使用指南')
const docContent = ref('校园网认证失败时，可先检查账号状态、认证页面、代理设置及网络配置；仍无法解决时联系网络中心。')
const messageList = ref(null)

const quickPrompts = [
  '学校奖学金评定条件是什么？',
  '在读证明怎么办理？',
  '校园网认证失败怎么办？',
  '校园卡丢了怎么挂失？',
  '宿舍空调坏了怎么报修？'
]

const intentLabels = {
  campus_policy: '校园政策',
  student_affairs: '学生事务',
  network_support: '校园网络',
  campus_card: '校园卡',
  dorm_service: '宿舍后勤',
  complaint: '投诉建议',
  escalation: '人工服务',
  greeting: '问候',
  feedback: '反馈',
  other: '其他'
}

const agentLabels = {
  general: '综合咨询 Agent',
  affairs: '学生事务 Agent',
  network: '校园网络 Agent',
  campus_card: '校园卡 Agent'
}

const docsUrl = computed(() => `${String(settings.endpoint || '').replace(/\/+$/, '')}/docs`)

watch(
  () => settings.conversationId,
  () => persist()
)

onMounted(() => {
  checkHealth()
  loadStats()
})

function createId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function persist() {
  saveSettings(settings)
}

function usePrompt(prompt) {
  draft.value = prompt
}

function friendlyIntent(value) {
  return intentLabels[value] || value || ''
}

function friendlyAgent(value) {
  return agentLabels[value] || value || ''
}

async function sendMessage() {
  const content = draft.value.trim()
  if (!content) return
  messages.value.push({ id: createId(), role: 'user', content })
  draft.value = ''
  busy.value = true
  try {
    const response = await requestChat(settings, content)
    if (response.conversationId && !settings.conversationId) {
      settings.conversationId = response.conversationId
      persist()
    }
    const meta = [
      friendlyIntent(response.intent),
      friendlyAgent(response.agentType),
      response.knowledgeUsed ? 'RAG' : '',
      response.toolsUsed.length ? `工具: ${response.toolsUsed.join(', ')}` : '',
      response.escalated ? '转人工' : '',
      response.latencyMs ? `${Math.round(response.latencyMs)} ms` : ''
    ].filter(Boolean).join(' · ')
    messages.value.push({
      id: createId(),
      role: 'assistant',
      content: response.response,
      meta
    })
  } catch (error) {
    messages.value.push({
      id: createId(),
      role: 'assistant',
      content: error.message,
      meta: '请求失败'
    })
  } finally {
    busy.value = false
    await nextTick()
    messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: 'smooth' })
  }
}

async function checkHealth() {
  try {
    const data = await requestHealth(settings)
    healthOk.value = data.status === 'ok'
    healthLabel.value = data.status || 'ok'
    statusText.value = JSON.stringify(data, null, 2)
  } catch (error) {
    healthOk.value = false
    healthLabel.value = '不可用'
    statusText.value = error.message
  }
}

async function loadStats() {
  try {
    const [stats, monitor] = await Promise.allSettled([
      requestKnowledgeStats(settings),
      requestMonitor(settings)
    ])
    if (stats.status === 'fulfilled') {
      knowledgeCount.value = stats.value.total_chunks ?? '-'
    }
    if (monitor.status === 'fulfilled') {
      statusText.value = JSON.stringify(monitor.value, null, 2)
    }
  } catch (error) {
    statusText.value = error.message
  }
}

async function searchKnowledge() {
  busy.value = true
  try {
    const data = await requestSearch(settings, searchQuery.value, 5)
    searchResults.value = data.results || []
  } catch (error) {
    statusText.value = error.message
  } finally {
    busy.value = false
  }
}

async function submitKnowledge() {
  busy.value = true
  try {
    const data = await addKnowledge(settings, [
      { title: docTitle.value.trim(), content: docContent.value.trim() }
    ])
    statusText.value = JSON.stringify(data, null, 2)
    await loadStats()
  } catch (error) {
    statusText.value = error.message
  } finally {
    busy.value = false
  }
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  busy.value = true
  try {
    const data = await uploadKnowledge(settings, file)
    statusText.value = JSON.stringify(data, null, 2)
    await loadStats()
  } catch (error) {
    statusText.value = error.message
  } finally {
    busy.value = false
  }
}
</script>
