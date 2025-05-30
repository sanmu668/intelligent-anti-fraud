import request from './request'
import { API_ENDPOINTS } from './config'

// 图谱分析路径参数接口
export interface GraphAnalysisPathParams {
  start_time: string;
  end_time: string;
  max_transactions?: number; // 可选参数，限制处理的最大交易数量
  batch_size?: number; // 可选参数，每批处理的交易数量
  use_gnn?: boolean; // 可选参数，是否使用GNN模型
}

// 图谱分析路径结果接口
export interface GraphAnalysisPathResult {
  paths: Array<{
    account_id: string;
    risk_score: number;
    total_amount: number;
    account_type: string;
    last_transaction: string;
  }>;
  nodes: Array<{
    id: string;
    name: string;
    value: number;
    category: number;
    risk_score: number;
    symbolSize: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    value: number;
    risk_score: number;
  }>;
  gnn_info?: {
    clusters?: Record<string, any>;
    potential_edges_count?: number;
    computation_time?: number;
  };
}

// 请求选项接口
export interface RequestOptions {
  timeout?: number;
  headers?: Record<string, string>;
  [key: string]: any;
}

// 仪表盘服务
export const dashboardService = {
  getStats() {
    return request.get(API_ENDPOINTS.DASHBOARD_STATS)
  }
}

// 监控服务
export const monitorService = {
  getRealtimeData() {
    return request.get(API_ENDPOINTS.MONITOR.REALTIME)
  },

  getAlerts(params: any) {
    return request.get(API_ENDPOINTS.MONITOR.ALERTS, { params })
  },

  processAlert(alertId: number, data: any) {
    return request.post(API_ENDPOINTS.MONITOR.PROCESS_ALERT(alertId), data)
  }
}

// 图谱分析服务
export const graphService = {
  // 获取拓扑图数据
  getTopology(params: any) {
    return request.get(API_ENDPOINTS.GRAPH.TOPOLOGY, { params })
  },

  // 路径分析
  analyzePath(params: GraphAnalysisPathParams, options?: RequestOptions) {
    return request<GraphAnalysisPathResult>({
      url: '/api/graph/analysis/path',
      method: 'post',
      data: params,
      ...options
    });
  }
}

export default {
  graphService
} 