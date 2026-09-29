import { featureLabel, formatMeasurement, orderedFeatures } from "@/lib/format";
import type { PredictResponse } from "@/types/predict";

type ThreatSignalsProps = {
  result: PredictResponse;
};

export function ThreatSignals({ result }: ThreatSignalsProps) {
  const features = orderedFeatures(result.features);

  return (
    <section aria-labelledby="signals-heading" className="border border-line bg-panel">
      <div className="border-b border-line px-4 py-3">
        <h2 id="signals-heading" className="text-sm font-semibold text-foreground">
          Threat signals
        </h2>
        <p className="mt-1 text-sm leading-6 text-muted">
          Signals the API selected for this URL. The assessment is the sentence returned with each signal, not a second score.
        </p>
      </div>

      {result.signals.length === 0 ? (
        <p className="px-4 py-4 text-sm text-foreground">No signals were returned for this URL.</p>
      ) : (
        <div className="overflow-x-auto px-4">
          <table className="data-table w-full border-collapse text-left text-sm">
            <caption className="sr-only">Threat signals for the analyzed URL</caption>
            <thead>
              <tr className="border-b border-line text-xs font-semibold tracking-wide text-muted uppercase">
                <th scope="col" className="py-2 pr-4 font-semibold">
                  Signal
                </th>
                <th scope="col" className="py-2 pr-4 font-semibold">
                  Value
                </th>
                <th scope="col" className="py-2 font-semibold">
                  Assessment
                </th>
              </tr>
            </thead>
            <tbody>
              {result.signals.map((signal) => (
                <tr key={signal.feature} className="border-b border-line last:border-b-0">
                  <th scope="row" data-label="Signal" className="py-2.5 pr-4 text-left font-medium text-foreground">
                    {featureLabel(signal.feature)}
                  </th>
                  <td data-label="Value" className="py-2.5 pr-4 font-mono text-foreground">
                    {formatMeasurement(signal.feature, signal.value)}
                  </td>
                  <td data-label="Assessment" className="py-2.5 text-foreground">
                    {signal.summary}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="border-t border-line px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">All measurements</h3>
        <p className="mt-1 text-sm text-muted">Every feature value returned with this score.</p>
      </div>
      {features.length === 0 ? (
        <p className="px-4 pb-4 text-sm text-foreground">No feature values were returned.</p>
      ) : (
        <div className="overflow-x-auto px-4 pb-2">
          <table className="data-table w-full border-collapse text-left text-sm">
            <caption className="sr-only">All feature measurements returned with this score</caption>
            <thead>
              <tr className="border-b border-line text-xs font-semibold tracking-wide text-muted uppercase">
                <th scope="col" className="py-2 pr-4 font-semibold">
                  Feature
                </th>
                <th scope="col" className="py-2 font-semibold">
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              {features.map((feature) => (
                <tr key={feature.name} className="border-b border-line last:border-b-0">
                  <th scope="row" data-label="Feature" className="py-2 pr-4 text-left font-medium text-foreground">
                    {featureLabel(feature.name)}
                  </th>
                  <td data-label="Value" className="py-2 font-mono text-foreground">
                    {formatMeasurement(feature.name, feature.value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
