import { formatPercent, predictionLabel } from "@/lib/format";
import type { Prediction } from "@/types/predict";

type ConfidenceIndicatorProps = {
  probability: number;
  prediction: Prediction;
};

export function ConfidenceIndicator({ probability, prediction }: ConfidenceIndicatorProps) {
  const percent = Math.min(100, Math.max(0, probability * 100));
  const label = predictionLabel(prediction);
  const fill = prediction === "phishing" ? "bg-phish" : "bg-safe";

  return (
    <div>
      <p className="text-xs font-semibold tracking-wide text-muted uppercase">Confidence</p>
      <p className="mt-1 font-mono text-2xl text-foreground">{formatPercent(probability)}</p>
      <div
        className="mt-2 h-1.5 bg-header"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Number(percent.toFixed(1))}
        aria-label={`Confidence of the ${label} label`}
      >
        <div className={`h-full ${fill}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-2 text-sm text-muted">Probability of the {label} label returned by the classifier.</p>
    </div>
  );
}
