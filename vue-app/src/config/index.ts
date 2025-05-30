// API配置
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// 超时配置
export const DEFAULT_TIMEOUT = 60000;
export const LONG_RUNNING_TIMEOUT = 300000;

// 调试模式
export const DEBUG = true; // 开启详细日志

// 分析任务配置
export const ANALYSIS_CONFIG = {
  maxTransactions: 3000,
  maxRetries: 3,
  batchSize: 1024,
  checkInterval: 10000,
  progressTimeout: 600000
}; 