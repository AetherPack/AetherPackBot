import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/layouts/DashboardLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue')
        },
        {
          path: 'providers',
          name: 'providers',
          component: () => import('@/views/ProvidersView.vue')
        },
        {
          path: 'platforms',
          name: 'platforms',
          component: () => import('@/views/PlatformsView.vue')
        },
        {
          path: 'plugins',
          name: 'plugins',
          component: () => import('@/views/PluginsView.vue')
        },
        {
          path: 'tools',
          name: 'tools',
          component: () => import('@/views/ToolsView.vue')
        },
        {
          path: 'logs',
          name: 'logs',
          component: () => import('@/views/LogsView.vue')
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue')
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
