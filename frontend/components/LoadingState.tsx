const STEPS = [
  "Extract features from the URL text",
  "Classify with the Random Forest",
  "Attach an explanation of that label",
];

export function LoadingState() {
  return (
    <div role="status" aria-live="polite" className="border border-line bg-panel px-4 py-4">
      <p className="text-sm font-semibold text-foreground">Analyzing URL</p>
      <p className="mt-1 text-sm leading-6 text-muted">
        One request is in progress. The page is not opened, and these steps are not separate calls.
      </p>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm leading-6 text-foreground">
        {STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </div>
  );
}
