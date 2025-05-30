import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ApiOptions {
  params?: Record<string, any>;
}

interface Alert {
  id: number;
  time: string;
  title: string;
  description: string;
  riskLevel: string;
  status: string;
  handler: string;
  [key: string]: any;
}

interface Transaction {
  time: string;
  type: string;
  amount: number;
  source: string;
  target: string;
  riskScore: number;
  details: any;
}

interface FilterParams {
  dateRange?: string[];
  alertType?: string;
  riskLevel?: string;
  status?: string;
  page?: number;
  pageSize?: number;
  startDate?: string;
  endDate?: string;
  [key: string]: any;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

export const useAlertsStore = defineStore('alerts', () => {
  // State
  const alerts = ref<Alert[]>([])
  const transactions = ref<Transaction[]>([])
  const totalAlerts = ref(0)
  const totalTransactions = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const filterParams = ref<FilterParams>({})
  const lastFilterHash = ref('')
  const lastUpdated = ref(0)
  const loading = ref(false)
  const error = ref('')

  // Getters
  const isDataStale = (params: FilterParams) => {
    // Generate a hash of the filter params to compare
    const paramsHash = JSON.stringify(params)
    
    // Data is stale if:
    // 1. Filter params have changed
    // 2. Data is more than 5 minutes old
    const paramsChanged = paramsHash !== lastFilterHash.value
    const timeStale = Date.now() - lastUpdated.value > 5 * 60 * 1000
    
    return paramsChanged || timeStale
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

  const fetchAlerts = async (params: FilterParams = {}) => {
    // Use current store values as defaults
    const queryParams = {
      page: currentPage.value,
      pageSize: pageSize.value,
      ...filterParams.value,
      ...params
    }
    
    const paramsHash = JSON.stringify(queryParams)
    
    // Return cached data if not stale
    if (!isDataStale(queryParams) && alerts.value.length > 0) {
      console.log('Using cached alerts data')
      return { alerts: alerts.value, total: totalAlerts.value }
    }
    
    loading.value = true
    error.value = ''
    
    try {
      const data = await fetchWithRetry('/api/alerts', { params: queryParams })
      
      alerts.value = data.items.map((item: any) => ({
        ...item,
        time: new Date(item.time).toLocaleString('zh-CN')
      }))
      totalAlerts.value = data.total
      
      // Update cache metadata
      lastFilterHash.value = paramsHash
      lastUpdated.value = Date.now()
      
      return { alerts: alerts.value, total: totalAlerts.value }
    } catch (e) {
      console.error('Failed to fetch alerts:', e)
      error.value = 'Failed to fetch alerts: ' + (e instanceof Error ? e.message : String(e))
      ElMessage.error('获取预警数据失败')
      throw e
    } finally {
      loading.value = false
    }
  }

  const fetchTransactions = async () => {
    loading.value = true
    error.value = ''
    
    try {
      const data = await fetchWithRetry('/api/monitor/transactions')
      
      transactions.value = data.map((tx: any) => {
        const timestamp = new Date(tx.timestamp)
        const amount = Number(tx.amount)
        const riskScore = Number(tx.risk_score)
        
        return {
          time: timestamp.toLocaleString(),
          type: tx.transaction_type || 'UNKNOWN',
          amount: amount,
          source: tx.source_account || '未知来源',
          target: tx.target_account || '未知目标',
          riskScore: riskScore * 100,
          details: tx
        }
      })
      
      totalTransactions.value = transactions.value.length
      lastUpdated.value = Date.now()
      
      return transactions.value
    } catch (e) {
      console.error('Failed to fetch transactions:', e)
      error.value = 'Failed to fetch transactions: ' + (e instanceof Error ? e.message : String(e))
      ElMessage.error('获取交易数据失败')
      throw e
    } finally {
      loading.value = false
    }
  }

  const updateAlertStatus = async (alertId: number, status: string, description: string = '') => {
    loading.value = true
    
    try {
      const response = await fetchWithRetry(`/api/alerts/${alertId}/process`, {
        params: {
          method: status,
          description,
          handler: 'Admin' // Ideally this would come from user auth
        }
      })
      
      if (response.success) {
        ElMessage.success('预警处理成功')
        // Update the local alert item
        const alertIndex = alerts.value.findIndex(a => a.id === alertId)
        if (alertIndex !== -1) {
          alerts.value[alertIndex].status = status
        }
        return true
      } else {
        throw new Error(response.error || '预警处理失败')
      }
    } catch (e) {
      console.error('Failed to update alert status:', e)
      ElMessage.error('预警处理失败')
      return false
    } finally {
      loading.value = false
    }
  }

  const setPageSize = (size: number) => {
    pageSize.value = size
  }

  const setCurrentPage = (page: number) => {
    currentPage.value = page
  }

  const setFilterParams = (params: FilterParams) => {
    filterParams.value = params
  }

  const resetFilters = () => {
    filterParams.value = {}
    currentPage.value = 1
  }

  const clearCache = () => {
    alerts.value = []
    transactions.value = []
    lastFilterHash.value = ''
    lastUpdated.value = 0
  }

  const addTransaction = (transaction: Transaction) => {
    transactions.value.unshift(transaction)
    if (transactions.value.length > 100) {
      transactions.value.pop()
    }
  }
  
  const addAlert = (alert: any) => {
    alerts.value.unshift(alert)
    if (alerts.value.length > 20) {
      alerts.value.pop()
    }
  }
  
  const clearTransactions = () => {
    transactions.value = []
  }
  
  const clearAlerts = () => {
    alerts.value = []
  }

  return {
    // State
    alerts,
    transactions,
    totalAlerts,
    totalTransactions,
    currentPage,
    pageSize,
    filterParams,
    loading,
    error,
    
    // Actions
    fetchAlerts,
    fetchTransactions,
    updateAlertStatus,
    setPageSize,
    setCurrentPage,
    setFilterParams,
    resetFilters,
    clearCache,
    addTransaction,
    addAlert,
    clearTransactions,
    clearAlerts
  }
}) 