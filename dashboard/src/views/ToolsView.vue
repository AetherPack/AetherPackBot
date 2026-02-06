<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getTools } from '@/services/api'

interface ToolParameter {
  name: string
  type: string
  description: string
  required: boolean
}

interface Tool {
  name: string
  description: string
  enabled: boolean
  parameters: ToolParameter[]
}

const tools = ref<Tool[]>([])
const loading = ref(true)
const error = ref('')
const expandedTool = ref<string | null>(null)

async function fetchTools() {
  loading.value = true
  error.value = ''
  
  try {
    tools.value = await getTools()
  } catch (e) {
    error.value = '获取工具列表失败'
  } finally {
    loading.value = false
  }
}

function toggleExpand(name: string) {
  expandedTool.value = expandedTool.value === name ? null : name
}

onMounted(fetchTools)
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">工具管理</h1>
      <p class="text-gray-500 dark:text-gray-400 mt-1">查看和管理可用的 Agent 工具</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card">
      <div class="text-center py-8">
        <p class="text-red-500">{{ error }}</p>
        <button @click="fetchTools" class="btn-primary mt-4">重试</button>
      </div>
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Empty state -->
      <div v-if="tools.length === 0" class="card text-center py-12">
        <svg class="w-16 h-16 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mt-4">暂无工具</h3>
        <p class="text-gray-500 dark:text-gray-400 mt-2">安装插件以添加新工具</p>
      </div>

      <!-- Tools list -->
      <div v-else class="space-y-4">
        <div
          v-for="tool in tools"
          :key="tool.name"
          class="card"
        >
          <div 
            class="flex items-start justify-between cursor-pointer"
            @click="toggleExpand(tool.name)"
          >
            <div class="flex items-center gap-4">
              <div 
                :class="[
                  'w-10 h-10 rounded-lg flex items-center justify-center',
                  tool.enabled 
                    ? 'bg-green-100 dark:bg-green-900/30' 
                    : 'bg-gray-100 dark:bg-gray-800'
                ]"
              >
                <svg 
                  :class="[
                    'w-5 h-5',
                    tool.enabled 
                      ? 'text-green-600 dark:text-green-400' 
                      : 'text-gray-400'
                  ]" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-gray-900 dark:text-white font-mono">
                  {{ tool.name }}
                </h3>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                  {{ tool.description }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span :class="tool.enabled ? 'badge-success' : 'badge-error'">
                {{ tool.enabled ? '已启用' : '已禁用' }}
              </span>
              <svg 
                :class="[
                  'w-5 h-5 text-gray-400 transition-transform',
                  expandedTool === tool.name && 'rotate-180'
                ]" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
          
          <!-- Expanded details -->
          <div 
            v-if="expandedTool === tool.name && tool.parameters.length > 0"
            class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700"
          >
            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">参数</h4>
            <div class="space-y-2">
              <div 
                v-for="param in tool.parameters"
                :key="param.name"
                class="flex items-start gap-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-sm text-gray-900 dark:text-white">{{ param.name }}</span>
                    <span class="text-xs text-gray-500">({{ param.type }})</span>
                    <span v-if="param.required" class="text-xs text-red-500">*必填</span>
                  </div>
                  <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {{ param.description }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
