// 基础图分析结果接口
export interface GraphAnalysisPathResult {
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
  paths: Array<{
    nodes: string[];
    risk: number;
  }>;
}

// 风险传播分析结果接口
export interface RiskPropagationResult {
  affected_accounts: number;
  max_depth: number;
  propagation_tree: {
    name: string;
    risk_score: number;
    affected_accounts: number;
    children: Array<RiskPropagationNode>;
  };
}

// 风险传播节点接口
export interface RiskPropagationNode {
  name: string;
  risk_score: number;
  affected_accounts: number;
  children: Array<RiskPropagationNode>;
}

// 图分析服务接口
export interface GraphAnalysisService {
  analyzePath(params: any): Promise<any>;
  analyzeCluster(data: any): Promise<any>;
  analyzeRiskPropagation(data: any): Promise<any>;
}

// 导出所有类型
export * from '@/api/services/graphAnalysisService'; 