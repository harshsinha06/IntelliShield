import { RiskBadge } from "@/components/RiskBadge";
import { formatPercent, formatTimestamp, predictionLabel } from "@/lib/format";
import type { HistoryItem } from "@/types/predict";

type HistoryListProps = {
  items: HistoryItem[];
  activeId: number | null;
  loading: boolean;
  errorMessage: string | null;
  onOpen: (id: number) => void;
};

export function HistoryList({ items, activeId, loading, errorMessage, onOpen }: HistoryListProps) {
  return (
    <section aria-labelledby="history-heading" className="border border-line bg-panel">
      <div className="border-b border-line px-4 py-3">
        <h2 id="history-heading" className="text-sm font-semibold text-foreground">
          Recent analyses
        </h2>
        <p className="mt-1 text-sm leading-6 text-muted">
          Saved scores from this server. Userinfo and query values are removed from the stored URL.
        </p>
      </div>
      <div className="px-4 py-3">
        {loading ? <p className="text-sm text-foreground">Loading recent analyses.</p> : null}
        {errorMessage ? (
          <p role="alert" className="text-sm text-phish">
            {errorMessage}
          </p>
        ) : null}
        {!loading && items.length === 0 && !errorMessage ? (
          <p className="text-sm text-foreground">No analyses have been saved yet.</p>
        ) : null}
        {items.length > 0 ? (
          <ul className="divide-y divide-line border-y border-line">
            {items.map((item) => {
              const selected = item.id === activeId;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-current={selected ? "true" : undefined}
                    onClick={() => onOpen(item.id)}
                    className={`flex w-full flex-col gap-1 py-3 text-left outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:grid sm:grid-cols-[minmax(9rem,11rem)_6.5rem_5.5rem_4.5rem_minmax(0,1fr)] sm:items-center sm:gap-2 ${
                      selected ? "text-foreground" : "text-muted hover:text-foreground"
                    }`}
                  >
                    <time dateTime={item.created_at} className="text-sm text-foreground">
                      {formatTimestamp(item.created_at)}
                    </time>
                    <span className="font-mono text-sm tracking-wide text-foreground">
                      {predictionLabel(item.prediction)}
                    </span>
                    <span>
                      <RiskBadge riskLevel={item.risk_level} />
                    </span>
                    <span className="font-mono text-sm text-foreground">{formatPercent(item.probability)}</span>
                    <span className="font-mono text-xs break-all text-muted sm:truncate">{item.url}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
