import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const BASE_URL = import.meta.env.BASE_URL || '/'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/index.vue')
  },
  {
    path: '/graph-analysis',
    name: 'GraphAnalysis',
    component: () => import('@/views/graph/analysis.vue')
  },
  {
    path: '/monitor',
    name: 'Monitor',
    children: [
      {
        path: 'realtime',
        name: 'MonitorRealtime',
        component: () => import('@/views/monitor/realtime.vue')
      },
      {
        path: 'alerts',
        name: 'MonitorAlerts',
        component: () => import('@/views/monitor/alerts.vue')
      }
    ]
  },
  {
    path: '/group/analysis',
    name: 'GroupAnalysis',
    component: () => import('@/views/group/analysis.vue')
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/reports/index.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/index.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/chat/index.vue'),
    meta: { title: 'AI对话' }
  }
]

const router = createRouter({
  history: createWebHistory(BASE_URL),
  routes
})

export default router