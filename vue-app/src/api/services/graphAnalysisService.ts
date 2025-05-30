import axios from 'axios';
import type { AxiosResponse } from 'axios';
import { API_BASE_URL } from '@/config';
import { ElMessage } from 'element-plus';

// Create a custom axios instance for graph analysis
const graphAxios = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add response interceptor for better error handling
graphAxios.interceptors.response.use(
  response => response,
  error => {
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      ElMessage.error('分析请求超时，请减少数据量或稍后重试');
    } else if (!error.response) {
      ElMessage.error('无法连接到服务器，请检查网络连接');
    } else {
      ElMessage.error(error.response.data?.message || '分析请求失败');
    }
    return Promise.reject(error);
  }
);

export interface GraphAnalysisParams {
  start_time: string;
  end_time: string;
  max_transactions: number;
  use_gnn: boolean;
  use_basic_analysis: boolean;
  min_risk_score: number;
  batch_size: number;
  similarity_threshold: number;
  use_streaming: boolean;
  similarity_batch_size: number;
  clustering_batch_size: number;
  max_nodes: number;
  use_progressive_loading: boolean;
  use_alternative_pagerank: boolean;
  disable_cache: boolean;
  analysis_type?: 'path' | 'risk_propagation';
  disable_optimization?: boolean;
}

export interface AnalysisTaskResponse {
  task_id: string;
  status: string;
  message?: string;
  result?: any;
}

export interface AnalysisProgressResponse {
  status: 'completed' | 'failed' | 'processing';
  percent?: number;
  message?: string;
  stage?: string;
  result?: any;
  error?: string;
}

const graphAnalysisService = {
  // 启动路径分析任务
  startPathAnalysis(params: GraphAnalysisParams): Promise<AxiosResponse<AnalysisTaskResponse>> {
    return graphAxios.post('/api/graph/analysis/path', params);
  },

  // 启动风险传播分析
  startRiskPropagation(params: GraphAnalysisParams): Promise<AxiosResponse<AnalysisTaskResponse>> {
    return graphAxios.post('/api/graph/analysis/risk-propagation', params);
  },

  // 启动团伙聚类分析
  startClusterAnalysis(params: GraphAnalysisParams): Promise<AxiosResponse<AnalysisTaskResponse>> {
    return graphAxios.post('/api/graph/analysis/cluster', params);
  },

  // 获取图谱拓扑
  getGraphTopology(): Promise<AxiosResponse<any>> {
    return graphAxios.get('/api/graph/topology');
  },

  // 检查分析任务进度
  checkAnalysisProgress(taskId: string): Promise<AxiosResponse<AnalysisProgressResponse>> {
    return graphAxios.get(`/api/graph/analysis/progress/${taskId}`);
  },

  // 取消分析任务
  cancelAnalysis(taskId: string): Promise<AxiosResponse<void>> {
    return graphAxios.post(`/api/graph/analysis/cancel/${taskId}`);
  }
};

export default graphAnalysisService; 