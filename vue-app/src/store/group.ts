import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface ApiOptions {
  params?: Record<string, any>;
  method?: string;
  body?: string;
  headers?: Record<string, string>;
}

interface GroupData {
  id: string;
  memberCount: number;
  totalAmount: number;
  avgRiskScore: number;
  riskTypes: string[];
  [key: string]: any;
}

interface AnalysisData {
  patterns: any[];
  behaviors: any[];
  timeline: any[];
  [key: string]: any;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

export const useGroupStore = defineStore('group', () => {
  // State - Detection
  const detectionData = ref<any>({
    nodes: [],
    edges: []
  })
  const selectedGroup = ref<GroupData | null>(null)
  const detectionParams = ref<Record<string, any>>({})
  const lastDetectionParamsHash = ref('')
  
  // State - Analysis
  const analysisData = ref<AnalysisData>({
    patterns: [],
    behaviors: [],
    timeline: []
  })
  const analysisParams = ref<Record<string, any>>({})
  const lastAnalysisParamsHash = ref('')
  
  // Common state
  const lastUpdated = ref(0)
  const loading = ref(false)
  const error = ref('')

  // Helpers
  const getParamsHash = (params: Record<string, any>) => {
    return JSON.stringify(params)
  }
  
  const isDataStale = (
    currentHash: string, 
    lastHash: string, 
    dataExists: boolean
  ) => {
    // Data is stale if:
    // 1. Parameters have changed
    // 2. Data is more than 10 minutes old
    // 3. Data doesn't exist yet
    const paramsChanged = currentHash !== lastHash
    const timeStale = Date.now() - lastUpdated.value > 10 * 60 * 1000
    
    return paramsChanged || timeStale || !dataExists
  }

  // Network request helper
  const fetchWithRetry = async (endpoint: string, options: ApiOptions = {}, retries = 3) => {
    let lastError: Error | null = null
    
    for (let i = 0; i < retries; i++) {
      try {
        let url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
        const method = options.method || 'GET';
        const headers = {
          'Content-Type': 'application/json',
          ...options.headers
        };
        
        // Set up fetch options based on method
        const fetchOptions: RequestInit = {
          method,
          headers
        };
        
        // For GET requests, append params to URL
        // For POST/PUT, add params to the body
        if (method === 'GET' && options.params) {
          const queryParams = `?${new URLSearchParams(options.params as Record<string, string>).toString()}`;
          url += queryParams;
        } else if (['POST', 'PUT', 'PATCH'].includes(method) && options.params) {
          fetchOptions.body = JSON.stringify(options.params);
        } else if (options.body) {
          fetchOptions.body = options.body;
        }
        
        const response = await fetch(url, fetchOptions);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        const data = await response.json();
        if (data.error) {
          throw new Error(data.error);
        }
        return data;
      } catch (e) {
        lastError = e instanceof Error ? e : new Error(String(e));
        console.warn(`Attempt ${i + 1} failed:`, lastError.message);
        if (i < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        }
      }
    }
    throw lastError;
  }

  // Group Detection Methods
  const loadDetectionData = async (params: Record<string, any> = {}) => {
    const combinedParams = {
      ...detectionParams.value,
      ...params
    }
    
    const paramsHash = getParamsHash(combinedParams)
    const dataExists = detectionData.value.nodes.length > 0
    
    // Return cached data if not stale
    if (!isDataStale(paramsHash, lastDetectionParamsHash.value, dataExists)) {
      console.log('Using cached group detection data')
      return detectionData.value
    }
    
    loading.value = true
    error.value = ''
    
    try {
      // Convert the parameters to match the API expectations
      const apiParams = {
        start_time: combinedParams.startDate,
        end_time: combinedParams.endDate,
        min_risk_score: combinedParams.minRisk || 0.5,
        use_gnn: true,
        max_transactions: 10000,
        use_streaming: true,
        analysis_type: 'path'
      }

      const data = await fetchWithRetry('/api/graph/analysis/path', { 
        method: 'POST',
        params: apiParams,
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (!data.result?.nodes || !data.result?.edges) {
        throw new Error('Invalid graph data format')
      }
      
      detectionData.value = data.result
      detectionParams.value = { ...combinedParams }
      lastDetectionParamsHash.value = paramsHash
      lastUpdated.value = Date.now()
      
      return data.result
    } catch (e) {
      console.error('Failed to load group detection data:', e)
      error.value = 'Failed to load group detection data: ' + (e instanceof Error ? e.message : String(e))
      ElMessage.error('加载团伙网络数据失败')
      throw e
    } finally {
      loading.value = false
    }
  }

  // Selected group
  const setSelectedGroup = (group: GroupData | null) => {
    selectedGroup.value = group
  }
  
  // Analysis Methods
  const loadAnalysisData = async (accountId: string, params: Record<string, any> = {}) => {
    const combinedParams = {
      ...analysisParams.value,
      ...params,
      account_id: accountId
    }
    
    const paramsHash = getParamsHash(combinedParams)
    const dataExists = analysisData.value.patterns.length > 0 || analysisData.value.behaviors.length > 0
    
    // Return cached data if not stale
    if (!isDataStale(paramsHash, lastAnalysisParamsHash.value, dataExists)) {
      console.log('Using cached analysis data')
      return analysisData.value
    }
    
    loading.value = true
    error.value = ''
    
    try {
      const data = await fetchWithRetry('/api/account/analysis', { 
        method: 'POST',
        params: combinedParams,
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      analysisData.value = data
      analysisParams.value = { ...combinedParams }
      lastAnalysisParamsHash.value = paramsHash
      lastUpdated.value = Date.now()
      
      return data
    } catch (e) {
      console.error('Failed to load account analysis data:', e)
      error.value = 'Failed to load account analysis data: ' + (e instanceof Error ? e.message : String(e))
      ElMessage.error('加载账户分析数据失败')
      throw e
    } finally {
      loading.value = false
    }
  }
  
  // Cache Management
  const clearDetectionCache = () => {
    detectionData.value = { nodes: [], edges: [] }
    lastDetectionParamsHash.value = ''
    console.log('Detection cache cleared')
  }
  
  const clearAnalysisCache = () => {
    analysisData.value = { patterns: [], behaviors: [], timeline: [] }
    lastAnalysisParamsHash.value = ''
    console.log('Analysis cache cleared')
  }
  
  const clearAllCache = () => {
    clearDetectionCache()
    clearAnalysisCache()
    console.log('All caches cleared')
  }

  return {
    // State
    detectionData,
    selectedGroup,
    detectionParams,
    analysisData,
    analysisParams,
    loading,
    error,
    
    // Methods
    loadDetectionData,
    setSelectedGroup,
    loadAnalysisData,
    clearDetectionCache,
    clearAnalysisCache,
    clearAllCache
  }
}) 