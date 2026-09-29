type RecommendationsProps = {
  items: string[];
};

export function Recommendations({ items }: RecommendationsProps) {
  return (
    <section aria-labelledby="recommendations-heading" className="border border-line bg-panel px-4 py-4">
      <h2 id="recommendations-heading" className="text-sm font-semibold text-foreground">
        Recommendations
      </h2>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-foreground">No recommendations were returned.</p>
      ) : (
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-foreground">
          {items.map((item, index) => (
            <li key={`${index}-${item}`}>{item}</li>
          ))}
        </ol>
      )}
    </section>
  );
}
