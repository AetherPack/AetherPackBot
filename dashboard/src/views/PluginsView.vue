<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPlugins, reloadPlugin } from '@/services/api'

interface Plugin {
  name: string
  version: string
  author: string
  description: string
  status: string
  is_builtin: boolean
}

const plugins = ref<Plugin[]>([])
const loading = ref(true)
const error = ref('')
const reloading = ref<string | null>(null)

async function fetchPlugins() {
  loading.value = true
  error.value = ''
  
  try {
    plugins.value = await getPlugins()
  } catch (e) {
    error.value = '获取插件列表失败'
  } finally {
    loading.value = false
  }
}

async function handleReload(name: string) {
  reloading.value = name
  
  try {
    await reloadPlugin(name)
    await fetchPlugins()
  } catch (e) {
    console.error('Reload failed:', e)
  } finally {
    reloading.value = null
  }
}

onMounted(fetchPlugins)
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">插件管理</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">安装和管理扩展插件</p>
      </div>
      <button class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        安装插件
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card">
      <div class="text-center py-8">
        <p class="text-red-500">{{ error }}</p>
        <button @click="fetchPlugins" class="btn-primary mt-4">重试</button>
      </div>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Empty state -->
      <div v-if="plugins.length === 0" class="card text-center py-12">
        <svg class="w-16 h-16 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mt-4">暂无插件</h3>
        <p class="text-gray-500 dark:text-gray-400 mt-2">安装插件扩展机器人功能</p>
        <button class="btn-primary mt-6">安装插件</button>
      </div>

      <!-- Plugins list -->
      <div v-else class="space-y-4">
        <div
          v-for="plugin in plugins"
          :key="plugin.name"
          class="card hover:shadow-md transition-shadow"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-4">
              <div 
                :class="[
                  'w-12 h-12 rounded-xl flex items-center justify-center',
                  plugin.is_builtin 
                    ? 'bg-gradient-to-br from-purple-500 to-purple-600' 
                    : 'bg-gradient-to-br from-blue-500 to-blue-600'
                ]"
              >
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <h3 class="font-semibold text-gray-900 dark:text-white">{{ plugin.name }}</h3>
                  <span class="text-sm text-gray-500">v{{ plugin.version }}</span>
                  <span v-if="plugin.is_builtin" class="badge-info">内置</span>
                </div>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {{ plugin.description || '暂无描述' }}
                </p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  作者: {{ plugin.author || '未知' }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span :class="plugin.status === 'RUNNING' ? 'badge-success' : 'badge-warning'">
                {{ plugin.status === 'RUNNING' ? '运行中' : '已加载' }}
              </span>
            </div>
          </div>
          
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
            <button 
              @click="handleReload(plugin.name)"
              :disabled="reloading === plugin.name"
              class="btn-ghost text-sm px-3 py-1"
            >
              <svg 
                v-if="reloading === plugin.name" 
                class="animate-spin w-4 h-4 mr-1" 
                fill="none" 
                viewBox="0 0 24 24"
              >
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              重载
            </button>
            <button v-if="!plugin.is_builtin" class="btn-ghost text-sm px-3 py-1 text-red-600">
              卸载
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
