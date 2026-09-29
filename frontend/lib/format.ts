import type { Prediction, RiskLevel } from "@/types/predict";

/** Display order for the 15 lexical measurements. Extra keys from the API are appended. */
export const FEATURE_ORDER = [
  "uses_https",
  "url_length",
  "has_ip_address",
  "has_suspicious_keyword",
  "subdomain_count",
  "hostname_length",
  "domain_length",
  "dot_count",
  "hyphen_count",
  "special_char_count",
  "digit_count",
  "has_at_symbol",
  "is_url_shortener",
  "path_segment_count",
  "query_param_count",
] as const;

const FEATURE_LABELS: Record<string, string> = {
  uses_https: "HTTPS",
  url_length: "URL length",
  has_ip_address: "IP address",
  has_suspicious_keyword: "Suspicious keyword",
  subdomain_count: "Subdomains",
  hostname_length: "Hostname length",
  domain_length: "Domain length",
  dot_count: "Dots",
  hyphen_count: "Hyphens",
  special_char_count: "Special characters",
  digit_count: "Digits",
  has_at_symbol: "@ symbol",
  is_url_shortener: "URL shortener",
  path_segment_count: "Path segments",
  query_param_count: "Query parameters",
};

const BINARY_FEATURES = new Set([
  "uses_https",
  "has_ip_address",
  "has_suspicious_keyword",
  "has_at_symbol",
  "is_url_shortener",
]);

export function predictionLabel(prediction: Prediction): "SAFE" | "PHISHING" {
  return prediction === "safe" ? "SAFE" : "PHISHING";
}

export function riskLabel(riskLevel: RiskLevel): "LOW" | "MEDIUM" | "HIGH" {
  if (riskLevel === "low") return "LOW";
  if (riskLevel === "medium") return "MEDIUM";
  return "HIGH";
}

export function formatPercent(probability: number): string {
  return `${(probability * 100).toFixed(1)}%`;
}

export function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function featureLabel(name: string): string {
  return FEATURE_LABELS[name] ?? name.replaceAll("_", " ");
}

export function formatMeasurement(name: string, value: number): string {
  if (name === "uses_https") {
    if (value === 1) return "Enabled";
    if (value === 0) return "Not used";
  }
  if (BINARY_FEATURES.has(name)) {
    if (value === 1) return "Yes";
    if (value === 0) return "No";
  }
  if (!Number.isFinite(value)) return "—";
  if (Number.isInteger(value)) return String(value);
  return String(Math.round(value * 1_000_000) / 1_000_000);
}

export function formatImportance(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value !== 0 && Math.abs(value) < 0.001) return value.toExponential(2);
  return value.toFixed(3);
}

export function orderedFeatures(features: Record<string, number>): { name: string; value: number }[] {
  const seen = new Set<string>();
  const rows: { name: string; value: number }[] = [];
  for (const name of FEATURE_ORDER) {
    if (Object.prototype.hasOwnProperty.call(features, name)) {
      rows.push({ name, value: features[name] });
      seen.add(name);
    }
  }
  for (const name of Object.keys(features).sort()) {
    if (!seen.has(name)) {
      rows.push({ name, value: features[name] });
    }
  }
  return rows;
}
