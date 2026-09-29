import { formatPercent, predictionLabel } from "@/lib/format";
import type { PredictResponse } from "@/types/predict";

type ModelInformationProps = {
  result: PredictResponse;
};

export function ModelInformation({ result }: ModelInformationProps) {
  const featureCount = Object.keys(result.features).length;
  const rows = [
    { label: "Model", value: "Random Forest", mono: false },
    { label: "Prediction", value: predictionLabel(result.prediction), mono: true },
    { label: "Confidence", value: formatPercent(result.probability), mono: true },
    { label: "Feature count", value: String(featureCount), mono: true },
  ];

  return (
    <section aria-labelledby="model-heading" className="border border-line bg-panel">
      <div className="border-b border-line px-4 py-3">
        <h2 id="model-heading" className="text-sm font-semibold text-foreground">
          Model information
        </h2>
        <p className="mt-1 text-sm text-muted">Values from this response. The model name is the classifier this service uses.</p>
      </div>
      <dl className="grid grid-cols-2 sm:grid-cols-4">
        {rows.map((row) => (
          <div key={row.label} className="border-b border-line px-4 py-3 sm:border-b-0 sm:border-r sm:last:border-r-0">
            <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{row.label}</dt>
            <dd className={`mt-1 text-sm text-foreground ${row.mono ? "font-mono" : "font-medium"}`}>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
