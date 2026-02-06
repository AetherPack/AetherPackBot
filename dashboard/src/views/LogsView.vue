<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { getLogs } from '@/services/api'

interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
}

const logs = ref<LogEntry[]>([])
const loading = ref(true)
const error = ref('')
const autoRefresh = ref(true)
const filter = ref('')
const levelFilter = ref('all')

let refreshInterval: number | null = null

async function fetchLogs() {
  try {
    logs.value = await getLogs(500)
    error.value = ''
  } catch (e) {
    error.value = '获取日志失败'
  } finally {
    loading.value = false
  }
}

const filteredLogs = computed(() => {
  let result = logs.value
  
  if (levelFilter.value !== 'all') {
    result = result.filter(log => log.level === levelFilter.value)
  }
  
  if (filter.value) {
    const query = filter.value.toLowerCase()
    result = result.filter(log => 
      log.message.toLowerCase().includes(query) ||
      log.logger.toLowerCase().includes(query)
    )
  }
  
  return result.slice(0, 200)
})

function getLevelClass(level: string): string {
  switch (level.toUpperCase()) {
    case 'DEBUG':
      return 'text-gray-500'
    case 'INFO':
      return 'text-blue-500'
    case 'WARNING':
      return 'text-yellow-500'
    case 'ERROR':
      return 'text-red-500'
    case 'CRITICAL':
      return 'text-red-700 font-bold'
    default:
      return 'text-gray-500'
  }
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return timestamp
  }
}

function startAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  refreshInterval = window.setInterval(fetchLogs, 2000)
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

onMounted(() => {
  fetchLogs()
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<template>
  <div class="p-8 h-full flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">系统日志</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">实时查看系统运行日志</p>
      </div>
      <div class="flex items-center gap-4">
        <button 
          @click="toggleAutoRefresh"
          :class="[
            'btn-ghost text-sm',
            autoRefresh && 'text-green-600'
          ]"
        >
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
        </button>
        <button @click="fetchLogs" class="btn-secondary text-sm">刷新</button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-4 mb-4">
      <input
        v-model="filter"
        type="text"
        class="input max-w-sm"
        placeholder="搜索日志..."
      />
      <select v-model="levelFilter" class="input max-w-xs">
        <option value="all">所有级别</option>
        <option value="DEBUG">DEBUG</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
      <span class="text-sm text-gray-500">共 {{ filteredLogs.length }} 条</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center flex-1">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card">
      <div class="text-center py-8">
        <p class="text-red-500">{{ error }}</p>
        <button @click="fetchLogs" class="btn-primary mt-4">重试</button>
      </div>
    </div>

    <!-- Logs -->
    <div 
      v-else 
      class="flex-1 bg-gray-900 rounded-xl overflow-hidden font-mono text-sm"
    >
      <div class="h-full overflow-y-auto p-4 scrollbar-thin">
        <div v-if="filteredLogs.length === 0" class="text-center py-8 text-gray-500">
          暂无日志
        </div>
        <div 
          v-for="(log, index) in filteredLogs"
          :key="index"
          class="flex items-start gap-3 py-1 hover:bg-gray-800/50"
        >
          <span class="text-gray-500 shrink-0">{{ formatTime(log.timestamp) }}</span>
          <span :class="['shrink-0 w-16 text-right', getLevelClass(log.level)]">
            [{{ log.level }}]
          </span>
          <span class="text-purple-400 shrink-0">{{ log.logger }}</span>
          <span class="text-gray-300">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
