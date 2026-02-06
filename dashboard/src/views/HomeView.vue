<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getStatus } from '@/services/api'

interface StatusData {
  platforms: Record<string, boolean>
  providers: string[]
  plugins: Array<{ name: string; version: string; status: string }>
}

const status = ref<StatusData | null>(null)
const loading = ref(true)
const error = ref('')

async function fetchStatus() {
  loading.value = true
  error.value = ''
  
  try {
    status.value = await getStatus()
  } catch (e) {
    error.value = '获取状态失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchStatus)

function getPlatformCount() {
  if (!status.value) return { active: 0, total: 0 }
  const platforms = status.value.platforms
  const total = Object.keys(platforms).length
  const active = Object.values(platforms).filter(v => v).length
  return { active, total }
}

function getPluginCount() {
  if (!status.value) return { active: 0, total: 0 }
  const plugins = status.value.plugins
  const total = plugins.length
  const active = plugins.filter(p => p.status === 'RUNNING').length
  return { active, total }
}
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">仪表盘</h1>
      <p class="text-gray-500 dark:text-gray-400 mt-1">系统概况和实时状态</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card">
      <div class="text-center py-8">
        <p class="text-red-500">{{ error }}</p>
        <button @click="fetchStatus" class="btn-primary mt-4">重试</button>
      </div>
    </div>

    <!-- Content -->
    <div v-else class="space-y-8">
      <!-- Stats cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Platforms -->
        <div class="card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">平台</p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {{ getPlatformCount().active }} / {{ getPlatformCount().total }}
              </p>
            </div>
            <div class="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
            </div>
          </div>
        </div>

        <!-- Providers -->
        <div class="card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">提供者</p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {{ status?.providers.length || 0 }}
              </p>
            </div>
            <div class="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
          </div>
        </div>

        <!-- Plugins -->
        <div class="card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">插件</p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {{ getPluginCount().active }} / {{ getPluginCount().total }}
              </p>
            </div>
            <div class="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Platforms list -->
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">平台状态</h2>
        <div class="space-y-3">
          <div
            v-for="(running, name) in status?.platforms"
            :key="name"
            class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
          >
            <span class="font-medium text-gray-700 dark:text-gray-300">{{ name }}</span>
            <span :class="running ? 'badge-success' : 'badge-error'">
              {{ running ? '运行中' : '已停止' }}
            </span>
          </div>
          <div v-if="!status?.platforms || Object.keys(status.platforms).length === 0" class="text-center py-4 text-gray-500">
            暂无平台配置
          </div>
        </div>
      </div>

      <!-- Plugins list -->
      <div class="card">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">插件列表</h2>
        <div class="space-y-3">
          <div
            v-for="plugin in status?.plugins"
            :key="plugin.name"
            class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
          >
            <div>
              <span class="font-medium text-gray-700 dark:text-gray-300">{{ plugin.name }}</span>
              <span class="text-sm text-gray-500 ml-2">v{{ plugin.version }}</span>
            </div>
            <span :class="plugin.status === 'RUNNING' ? 'badge-success' : 'badge-warning'">
              {{ plugin.status === 'RUNNING' ? '运行中' : '已加载' }}
            </span>
          </div>
          <div v-if="!status?.plugins || status.plugins.length === 0" class="text-center py-4 text-gray-500">
            暂无插件安装
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
