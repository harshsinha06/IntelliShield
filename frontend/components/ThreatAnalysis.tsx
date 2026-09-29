import type { Analysis } from "@/types/predict";

type ThreatAnalysisProps = {
  analysis: Analysis;
};

function ItemList({ items, emptyLabel }: { items: string[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="mt-2 text-sm text-foreground">{emptyLabel}</p>;
  }
  return (
    <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-6 text-foreground">
      {items.map((item, index) => (
        <li key={`${index}-${item}`}>{item}</li>
      ))}
    </ul>
  );
}

export function ThreatAnalysis({ analysis }: ThreatAnalysisProps) {
  const fallback = analysis.source === "fallback";

  return (
    <section aria-labelledby="analysis-heading" className="border border-line bg-panel px-4 py-4">
      <p className="text-xs font-semibold tracking-wide text-muted uppercase">AI threat analysis</p>
      <h2 id="analysis-heading" className="mt-1 text-sm font-semibold text-foreground">
        Explanation of the ML prediction
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        This text describes the classifier result. It does not classify the URL.
      </p>
      {fallback ? (
        <p className="mt-3 border border-warn/30 bg-warn-soft px-3 py-2 text-sm leading-6 text-foreground">
          A language-model explanation was unavailable. The text below was written from the classifier output.
        </p>
      ) : (
        <p className="mt-3 text-sm leading-6 text-muted">Written by the language model from the classifier output.</p>
      )}

      <h3 className="mt-5 text-sm font-semibold text-foreground">Threat summary</h3>
      <p className="mt-2 text-sm leading-6 text-foreground">{analysis.summary}</p>

      <h3 className="mt-5 text-sm font-semibold text-foreground">Why this URL was classified this way</h3>
      <ItemList items={analysis.reasoning} emptyLabel="No reasoning was returned." />

      <h3 className="mt-5 text-sm font-semibold text-foreground">Risk factors</h3>
      <ItemList items={analysis.risk_factors} emptyLabel="No risk factors were returned." />
    </section>
  );
}
