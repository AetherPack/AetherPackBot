<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!username.value || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const success = await authStore.login(username.value, password.value)
    
    if (success) {
      router.push('/')
    } else {
      error.value = '用户名或密码错误'
    }
  } catch (e) {
    error.value = '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (authStore.isAuthenticated) {
    router.push('/')
  }
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-950 p-4">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl shadow-lg mb-4">
          <span class="text-white font-bold text-2xl">A</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">AetherPackBot</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-2">登录到管理面板</p>
      </div>

      <!-- Login form -->
      <div class="card">
        <form @submit.prevent="handleLogin" class="space-y-6">
          <!-- Error message -->
          <div v-if="error" class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
          </div>

          <!-- Username -->
          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              用户名
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              class="input"
              placeholder="请输入用户名"
              autocomplete="username"
            />
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              密码
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="input"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </div>

          <!-- Submit button -->
          <button
            type="submit"
            :disabled="loading"
            class="btn-primary w-full"
          >
            <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </form>

        <!-- Footer -->
        <div class="mt-6 text-center">
          <p class="text-xs text-gray-500 dark:text-gray-400">
            默认账号: aetherpackbot / aetherpackbot
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
