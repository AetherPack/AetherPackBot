<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getProviders } from '@/services/api'

interface Provider {
  id: string
  model: string
  display_name: string
}

const providers = ref<Provider[]>([])
const loading = ref(true)
const error = ref('')

async function fetchProviders() {
  loading.value = true
  error.value = ''
  
  try {
    providers.value = await getProviders()
  } catch (e) {
    error.value = '获取提供者列表失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchProviders)
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">LLM 提供者</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">管理语言模型提供者配置</p>
      </div>
      <button class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        添加提供者
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
        <button @click="fetchProviders" class="btn-primary mt-4">重试</button>
      </div>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Empty state -->
      <div v-if="providers.length === 0" class="card text-center py-12">
        <svg class="w-16 h-16 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mt-4">暂无提供者</h3>
        <p class="text-gray-500 dark:text-gray-400 mt-2">添加一个 LLM 提供者开始使用</p>
        <button class="btn-primary mt-6">添加提供者</button>
      </div>

      <!-- Providers grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="provider in providers"
          :key="provider.id"
          class="card hover:shadow-md transition-shadow cursor-pointer"
        >
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-gray-900 dark:text-white">
                  {{ provider.display_name || provider.id }}
                </h3>
                <p class="text-sm text-gray-500 dark:text-gray-400">{{ provider.model }}</p>
              </div>
            </div>
            <span class="badge-success">活跃</span>
          </div>
          
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
            <button class="btn-ghost text-sm px-3 py-1">编辑</button>
            <button class="btn-ghost text-sm px-3 py-1 text-red-600 hover:text-red-700">删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
