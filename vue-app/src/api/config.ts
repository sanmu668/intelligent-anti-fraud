// API 基础配置
export const API_BASE_URL = 'http://localhost:5000'

// API 端点配置
export const API_ENDPOINTS = {
  // 仪表盘
  DASHBOARD_STATS: '/api/dashboard/stats',

  // 监控
  MONITOR: {
    REALTIME: '/api/monitor/realtime',
    ALERTS: '/api/monitor/alerts',
    PROCESS_ALERT: (alertId: number) => `/api/monitor/alerts/${alertId}/process`
  },

  // 图谱分析
  GRAPH: {
    TOPOLOGY: '/api/graph/topology',
    PATH_ANALYSIS: '/api/graph/analysis/path',
    CLUSTER_ANALYSIS: '/api/graph/analysis/cluster',
    RISK_PROPAGATION: '/api/graph/analysis/risk-propagation'
  },

  // 聊天功能
  CHAT: {
    SEND: '/api/chat/send',
    HISTORY: '/api/chat/history'
  }
}