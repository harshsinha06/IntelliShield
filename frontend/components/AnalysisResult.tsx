import { ConfidenceIndicator } from "@/components/ConfidenceIndicator";
import { ModelInformation } from "@/components/ModelInformation";
import { Recommendations } from "@/components/Recommendations";
import { RiskBadge } from "@/components/RiskBadge";
import { ThreatAnalysis } from "@/components/ThreatAnalysis";
import { ThreatSignals } from "@/components/ThreatSignals";
import { predictionLabel } from "@/lib/format";
import type { PredictResponse } from "@/types/predict";

type AnalysisResultProps = {
  result: PredictResponse;
};

export function AnalysisResult({ result }: AnalysisResultProps) {
  const phishing = result.prediction === "phishing";
  const tone = phishing ? "border-phish bg-phish-soft" : "border-safe bg-safe-soft";
  const verdictColor = phishing ? "text-phish" : "text-safe";

  return (
    <div className="space-y-4">
      <section aria-labelledby="report-heading" className="border border-line bg-panel">
        <div className="border-b border-line px-4 py-3">
          <h2 id="report-heading" className="text-sm font-semibold text-foreground">
            URL analysis
          </h2>
          <p className="mt-2 font-mono text-sm break-all text-foreground">{result.url}</p>
        </div>
        <div className={`border-l-4 px-4 py-4 ${tone}`}>
          <p className="text-xs font-semibold tracking-wide text-muted uppercase">ML prediction</p>
          <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className={`text-3xl font-semibold tracking-tight ${verdictColor}`}>
                {predictionLabel(result.prediction)}
              </p>
              <p className="mt-2 flex items-center gap-2 text-sm text-foreground">
                <span>Risk</span>
                <RiskBadge riskLevel={result.risk_level} />
              </p>
            </div>
            <div className="sm:w-64">
              <ConfidenceIndicator probability={result.probability} prediction={result.prediction} />
            </div>
          </div>
        </div>
      </section>
      <ModelInformation result={result} />
      <ThreatSignals result={result} />
      <ThreatAnalysis analysis={result.analysis} />
      <Recommendations items={result.analysis.recommendations} />
    </div>
  );
}
