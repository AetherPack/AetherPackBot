<script setup lang="ts">
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

const route = useRoute()
const authStore = useAuthStore()

const navigation = [
  { name: '首页', path: '/', icon: 'home' },
  { name: '提供者', path: '/providers', icon: 'cpu' },
  { name: '平台', path: '/platforms', icon: 'share2' },
  { name: '插件', path: '/plugins', icon: 'package' },
  { name: '工具', path: '/tools', icon: 'tool' },
  { name: '日志', path: '/logs', icon: 'terminal' },
  { name: '设置', path: '/settings', icon: 'settings' }
]

const currentPath = computed(() => route.path)

function handleLogout() {
  authStore.logout()
  window.location.href = '/login'
}
</script>

<template>
  <div class="flex h-screen bg-gray-50 dark:bg-gray-950">
    <!-- Sidebar -->
    <aside class="w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col">
      <!-- Logo -->
      <div class="h-16 flex items-center px-6 border-b border-gray-200 dark:border-gray-800">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center">
            <span class="text-white font-bold text-sm">A</span>
          </div>
          <span class="font-semibold text-gray-900 dark:text-white">AetherPackBot</span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1 overflow-y-auto scrollbar-thin">
        <RouterLink
          v-for="item in navigation"
          :key="item.path"
          :to="item.path"
          :class="[
            'sidebar-item',
            currentPath === item.path && 'active'
          ]"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="item.icon === 'home'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            <path v-else-if="item.icon === 'cpu'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
            <path v-else-if="item.icon === 'share2'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            <path v-else-if="item.icon === 'package'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            <path v-else-if="item.icon === 'tool'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path v-else-if="item.icon === 'terminal'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            <path v-else-if="item.icon === 'settings'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          </svg>
          {{ item.name }}
        </RouterLink>
      </nav>

      <!-- User section -->
      <div class="p-4 border-t border-gray-200 dark:border-gray-800">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
              <span class="text-sm font-medium text-gray-600 dark:text-gray-300">
                {{ authStore.username?.charAt(0).toUpperCase() }}
              </span>
            </div>
            <span class="text-sm font-medium text-gray-700 dark:text-gray-200">
              {{ authStore.username }}
            </span>
          </div>
          <button
            @click="handleLogout"
            class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
            title="登出"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-hidden">
      <div class="h-full overflow-y-auto scrollbar-thin">
        <RouterView />
      </div>
    </main>
  </div>
</template>
