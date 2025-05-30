import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ApiOptions {
  params?: Record<string, any>;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const statistics = ref<any[]>([])
  const trends = ref({
    xAxis: [] as string[],
    series: [] as any[]
  })
  const riskDistribution = ref({
    labels: [] as string[],
    data: [] as number[]
  })
  const alertList = ref<any[]>([])
  const realtimeTransactions = ref<any[]>([])
  const lastUpdated = ref(0)
  const loading = ref(false)
  const error = ref('')

  // Getters
  const isDataStale = () => {
    // Data is stale if it's more than 30 seconds old
    return Date.now() - lastUpdated.value > 30000
  }

  // Actions
  const fetchWithRetry = async (endpoint: string, options: ApiOptions = {}, retries = 3) => {
    let lastError: Error | null = null
    
    for (let i = 0; i < retries; i++) {
      try {
        const queryParams = options.params ? `?${new URLSearchParams(options.params as Record<string, string>).toString()}` : ''
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}${queryParams}`
        
        const response = await fetch(url)
        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`)
        }
        const data = await response.json()
        if (data.error) {
          throw new Error(data.error)
        }
        return data
      } catch (e) {
        lastError = e instanceof Error ? e : new Error(String(e))
        console.warn(`Attempt ${i + 1} failed:`, lastError.message)
        if (i < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
        }
      }
    }
    throw lastError
  }

  const loadDashboardStats = async () => {
    try {
      const data = await fetchWithRetry('/api/dashboard/stats')
      statistics.value = Object.values(data)
      return data
    } catch (e) {
      console.error('Failed to load dashboard stats:', e)
      error.value = 'Failed to load dashboard stats: ' + (e instanceof Error ? e.message : String(e))
      throw e
    }
  }

  const loadTrendData = async () => {
    try {
      const data = await fetchWithRetry('/api/dashboard/trends')
      trends.value = data
      return data
    } catch (e) {
      console.error('Failed to load trend data:', e)
      error.value = 'Failed to load trend data: ' + (e instanceof Error ? e.message : String(e))
      throw e
    }
  }

  const loadRiskDistribution = async () => {
    try {
      const data = await fetchWithRetry('/api/dashboard/risk-distribution')
      riskDistribution.value = data
      return data
    } catch (e) {
      console.error('Failed to load risk distribution:', e)
      error.value = 'Failed to load risk distribution: ' + (e instanceof Error ? e.message : String(e))
      throw e
    }
  }

  const loadLatestAlerts = async () => {
    try {
      const data = await fetchWithRetry('/api/monitor/latest-alerts')
      alertList.value = data
      return data
    } catch (e) {
      console.error('Failed to load alerts:', e)
      error.value = 'Failed to load alerts: ' + (e instanceof Error ? e.message : String(e))
      throw e
    }
  }

  const loadRealtimeTransactions = async () => {
    try {
      const data = await fetchWithRetry('/api/monitor/realtime-transactions')
      realtimeTransactions.value = data
      return data
    } catch (e) {
      console.error('Failed to load realtime transactions:', e)
      error.value = 'Failed to load realtime transactions: ' + (e instanceof Error ? e.message : String(e))
      throw e
    }
  }

  const refreshAllData = async () => {
    loading.value = true
    error.value = ''
    
    try {
      await Promise.all([
        loadDashboardStats(),
        loadTrendData(),
        loadRiskDistribution(),
        loadLatestAlerts(),
        loadRealtimeTransactions()
      ])
      
      lastUpdated.value = Date.now()
    } catch (e) {
      console.error('Failed to refresh dashboard data:', e)
      error.value = 'Failed to refresh dashboard data: ' + (e instanceof Error ? e.message : String(e))
      ElMessage.error('Failed to refresh dashboard data')
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    statistics,
    trends,
    riskDistribution,
    alertList,
    realtimeTransactions,
    lastUpdated,
    loading,
    error,
    
    // Getters
    isDataStale,
    
    // Actions
    loadDashboardStats,
    loadTrendData,
    loadRiskDistribution,
    loadLatestAlerts,
    loadRealtimeTransactions,
    refreshAllData
  }
}) 