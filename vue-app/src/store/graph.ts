import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ApiOptions {
  params?: Record<string, any>;
}

interface GraphNode {
  id: string;
  label: string;
  risk_score: number;
  transaction_count: number;
  total_amount: number;
  is_merchant: boolean;
  [key: string]: any;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  count: number;
  risk_score: number;
  [key: string]: any;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layout?: Record<string, { x: number; y: number }>;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

export const useGraphStore = defineStore('graph', () => {
  // State
  const graphData = ref<GraphData>({
    nodes: [],
    edges: []
  })
  const lastParams = ref<Record<string, any>>({})
  const lastUpdated = ref(0)
  const loading = ref(false)
  const error = ref('')

  // Getters
  const isDataStale = (params: Record<string, any>) => {
    // Data is stale if parameters changed or it's more than 5 minutes old
    const paramsChanged = JSON.stringify(params) !== JSON.stringify(lastParams.value)
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

  const loadGraphData = async (params: Record<string, any> = {}) => {
    if (!isDataStale(params) && graphData.value.nodes.length > 0) {
      console.log('Using cached graph data')
      return graphData.value
    }

    loading.value = true
    error.value = ''
    
    try {
      const data = await fetchWithRetry('/api/topology', { params })
      
      if (!data.nodes || !data.edges) {
        throw new Error('Invalid graph data format')
      }
      
      graphData.value = data
      lastParams.value = { ...params }
      lastUpdated.value = Date.now()
      
      return data
    } catch (e) {
      console.error('Failed to load graph data:', e)
      error.value = 'Failed to load graph data: ' + (e instanceof Error ? e.message : String(e))
      ElMessage.error('Failed to load graph data')
      throw e
    } finally {
      loading.value = false
    }
  }

  const forceRefresh = async (params: Record<string, any> = {}) => {
    // Force a refresh by setting a parameter that ensures cache is bypassed
    const refreshParams = {
      ...params,
      force_refresh: true,
      _t: Date.now()
    }
    
    loading.value = true
    
    try {
      const data = await fetchWithRetry('/api/topology', { params: refreshParams })
      
      if (!data.nodes || !data.edges) {
        throw new Error('Invalid graph data format')
      }
      
      graphData.value = data
      lastParams.value = { ...params } // Store the original params without the force_refresh
      lastUpdated.value = Date.now()
      
      return data
    } catch (e) {
      console.error('Failed to refresh graph data:', e)
      error.value = 'Failed to refresh graph data: ' + (e instanceof Error ? e.message : String(e))
      ElMessage.error('Failed to refresh graph data')
      throw e
    } finally {
      loading.value = false
    }
  }

  const clearCache = () => {
    graphData.value = {
      nodes: [],
      edges: []
    }
    lastParams.value = {}
    lastUpdated.value = 0
  }

  return {
    // State
    graphData,
    lastParams,
    lastUpdated,
    loading,
    error,
    
    // Getters
    isDataStale,
    
    // Actions
    loadGraphData,
    forceRefresh,
    clearCache
  }
}) 