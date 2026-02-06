<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPlatforms } from '@/services/api'

const platforms = ref<Record<string, boolean>>({})
const loading = ref(true)
const error = ref('')

async function fetchPlatforms() {
  loading.value = true
  error.value = ''
  
  try {
    platforms.value = await getPlatforms()
  } catch (e) {
    error.value = '获取平台列表失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchPlatforms)

function getPlatformIcon(name: string): string {
  const lower = name.toLowerCase()
  if (lower.includes('telegram')) return 'telegram'
  if (lower.includes('discord')) return 'discord'
  if (lower.includes('qq')) return 'qq'
  if (lower.includes('wechat') || lower.includes('weixin')) return 'wechat'
  return 'default'
}
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">消息平台</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">管理连接的消息平台</p>
      </div>
      <button class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        添加平台
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
        <button @click="fetchPlatforms" class="btn-primary mt-4">重试</button>
      </div>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Empty state -->
      <div v-if="Object.keys(platforms).length === 0" class="card text-center py-12">
        <svg class="w-16 h-16 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mt-4">暂无平台</h3>
        <p class="text-gray-500 dark:text-gray-400 mt-2">添加一个消息平台开始接收消息</p>
        <button class="btn-primary mt-6">添加平台</button>
      </div>

      <!-- Platforms grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(running, name) in platforms"
          :key="name"
          class="card hover:shadow-md transition-shadow"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-4">
              <div 
                :class="[
                  'w-12 h-12 rounded-xl flex items-center justify-center',
                  running 
                    ? 'bg-gradient-to-br from-green-500 to-green-600' 
                    : 'bg-gradient-to-br from-gray-400 to-gray-500'
                ]"
              >
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-gray-900 dark:text-white">{{ name }}</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  {{ getPlatformIcon(name) }}
                </p>
              </div>
            </div>
            <span :class="running ? 'badge-success' : 'badge-error'">
              {{ running ? '运行中' : '已停止' }}
            </span>
          </div>
          
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-between">
            <button 
              :class="running ? 'btn-ghost text-red-600' : 'btn-ghost text-green-600'"
              class="text-sm px-3 py-1"
            >
              {{ running ? '停止' : '启动' }}
            </button>
            <div class="flex gap-2">
              <button class="btn-ghost text-sm px-3 py-1">编辑</button>
              <button class="btn-ghost text-sm px-3 py-1 text-red-600">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
