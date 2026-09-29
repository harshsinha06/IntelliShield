import type { Analysis, HistoryDetail, HistoryItem, PredictResponse, Signal } from "@/types/predict";

export class AnalyzeError extends Error {
  readonly code: string;

  constructor(message: string, code: string) {
    super(message);
    this.name = "AnalyzeError";
    this.code = code;
  }
}

export function apiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return (configured && configured.length > 0 ? configured : "http://localhost:8000").replace(/\/$/, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isSignal(value: unknown): value is Signal {
  return (
    isRecord(value) &&
    typeof value.feature === "string" &&
    typeof value.value === "number" &&
    Number.isFinite(value.value) &&
    typeof value.importance === "number" &&
    Number.isFinite(value.importance) &&
    typeof value.summary === "string"
  );
}

function isAnalysis(value: unknown): value is Analysis {
  return (
    isRecord(value) &&
    (value.source === "llm" || value.source === "fallback") &&
    typeof value.summary === "string" &&
    isStringList(value.reasoning) &&
    isStringList(value.risk_factors) &&
    isStringList(value.recommendations)
  );
}

export function isPredictResponse(value: unknown): value is PredictResponse {
  if (!isRecord(value)) return false;
  if (typeof value.url !== "string") return false;
  if (value.prediction !== "safe" && value.prediction !== "phishing") return false;
  if (typeof value.probability !== "number" || !Number.isFinite(value.probability)) return false;
  if (value.probability < 0 || value.probability > 1) return false;
  if (value.risk_level !== "low" && value.risk_level !== "medium" && value.risk_level !== "high") return false;
  if (!isRecord(value.features)) return false;
  if (!Object.values(value.features).every((item) => typeof item === "number" && Number.isFinite(item))) {
    return false;
  }
  if (!Array.isArray(value.signals) || !value.signals.every(isSignal)) return false;
  return isAnalysis(value.analysis);
}

function readApiError(payload: unknown): { code: string; message: string } | null {
  if (!isRecord(payload) || !isRecord(payload.error)) return null;
  const { code, message } = payload.error;
  if (typeof code !== "string" || typeof message !== "string" || message.trim() === "") return null;
  return { code, message };
}

export async function fetchHealth(): Promise<{ status: "ok"; model_loaded: boolean }> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/health`);
  } catch {
    throw new AnalyzeError("The analysis service could not be reached.", "network_error");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (
    !response.ok ||
    !isRecord(payload) ||
    payload.status !== "ok" ||
    typeof payload.model_loaded !== "boolean"
  ) {
    throw new AnalyzeError("The analysis service could not be reached.", "network_error");
  }
  return { status: "ok", model_loaded: payload.model_loaded };
}

export async function analyzeUrl(url: string): Promise<PredictResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/api/v1/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch {
    throw new AnalyzeError("The analysis service could not be reached.", "network_error");
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const parsed = readApiError(payload);
    throw new AnalyzeError(
      parsed?.message ?? "The analysis could not be completed.",
      parsed?.code ?? "request_failed",
    );
  }
  if (!isPredictResponse(payload)) {
    throw new AnalyzeError("The analysis service returned an unexpected response.", "invalid_response");
  }
  return payload;
}

function isHistoryItem(value: unknown): value is HistoryItem {
  return (
    isRecord(value) &&
    typeof value.id === "number" &&
    Number.isInteger(value.id) &&
    typeof value.created_at === "string" &&
    typeof value.url === "string" &&
    (value.prediction === "safe" || value.prediction === "phishing") &&
    typeof value.probability === "number" &&
    Number.isFinite(value.probability) &&
    (value.risk_level === "low" || value.risk_level === "medium" || value.risk_level === "high")
  );
}

function isHistoryDetail(value: unknown): value is HistoryDetail {
  return (
    isPredictResponse(value) &&
    isRecord(value) &&
    typeof value.id === "number" &&
    typeof value.created_at === "string"
  );
}

async function readJson(path: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`);
  } catch {
    throw new AnalyzeError("The analysis service could not be reached.", "network_error");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const parsed = readApiError(payload);
    throw new AnalyzeError(
      parsed?.message ?? "The history could not be loaded.",
      parsed?.code ?? "request_failed",
    );
  }
  return payload;
}

export async function fetchHistory(): Promise<HistoryItem[]> {
  const payload = await readJson("/api/v1/history");
  if (!isRecord(payload) || !Array.isArray(payload.items) || !payload.items.every(isHistoryItem)) {
    throw new AnalyzeError("The analysis service returned an unexpected response.", "invalid_response");
  }
  return payload.items;
}

export async function fetchHistoryItem(id: number): Promise<HistoryDetail> {
  const payload = await readJson(`/api/v1/history/${id}`);
  if (!isHistoryDetail(payload)) {
    throw new AnalyzeError("The analysis service returned an unexpected response.", "invalid_response");
  }
  return payload;
}
