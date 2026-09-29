/** Shapes returned by POST /api/v1/predict. The classifier owns the label. */

export type Prediction = "safe" | "phishing";

export type RiskLevel = "low" | "medium" | "high";

export type AnalysisSource = "llm" | "fallback";

export interface Signal {
  feature: string;
  value: number;
  importance: number;
  summary: string;
}

export interface Analysis {
  source: AnalysisSource;
  summary: string;
  reasoning: string[];
  risk_factors: string[];
  recommendations: string[];
}

export interface PredictResponse {
  url: string;
  prediction: Prediction;
  probability: number;
  risk_level: RiskLevel;
  features: Record<string, number>;
  signals: Signal[];
  analysis: Analysis;
}

export interface HistoryItem {
  id: number;
  created_at: string;
  url: string;
  prediction: Prediction;
  probability: number;
  risk_level: RiskLevel;
}

export interface HistoryDetail extends PredictResponse {
  id: number;
  created_at: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}
