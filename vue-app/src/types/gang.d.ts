// Account analysis types
export interface AnalysisResult {
  account_id: string;
  patterns: AnalysisPattern[];
  behaviors: AnalysisBehavior[];
  timeline: TimelinePoint[];
}

export interface AnalysisPattern {
  id: string;
  name: string;
  description: string;
  risk_level: string;
  count: number;
  amount: number;
}

export interface AnalysisBehavior {
  id: string;
  name: string;
  description: string;
  frequency: number;
  risk_score: number;
}

export interface TimelinePoint {
  date: string;
  transaction_count: number;
  amount: number;
  anomaly_score: number;
} 