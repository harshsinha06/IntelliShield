"use client";

import { useEffect } from "react";

import { AnalysisResult } from "@/components/AnalysisResult";
import { ErrorState } from "@/components/ErrorState";
import { HistoryList } from "@/components/HistoryList";
import { LoadingState } from "@/components/LoadingState";
import { StatusIndicator } from "@/components/StatusIndicator";
import { URLInput } from "@/components/URLInput";
import { useAnalyzeUrl } from "@/hooks/useAnalyzeUrl";
import { useHistory } from "@/hooks/useHistory";
import { formatTimestamp } from "@/lib/format";

export default function HomePage() {
  const { url, setUrl, status, result, errorMessage, errorCode, submit } = useAnalyzeUrl();
  const { items, opened, errorMessage: historyError, loading, reload, openItem, clearOpened } = useHistory();

  useEffect(() => {
    if (status === "success" && result) {
      void reload();
    }
  }, [reload, result, status]);

  const showingSaved = opened !== null;
  const showingLive = !showingSaved && status === "success" && result !== null;

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="border-b border-line bg-panel">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <p className="text-base font-semibold tracking-tight text-foreground">IntelliShield</p>
            <p className="text-xs text-muted">URL Threat Intelligence</p>
          </div>
          <StatusIndicator />
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        <section aria-labelledby="analyze-heading">
          <h1 id="analyze-heading" className="text-xl font-semibold tracking-tight text-foreground">
            Analyze a suspicious URL
          </h1>
          <p id="url-help" className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            IntelliShield uses a Random Forest to measure suspicious characteristics of the URL text. The label comes
            from that classifier. An explanation is attached afterward and does not change the result. The page is not
            opened.
          </p>
          <div className="mt-4 border border-line bg-panel px-4 py-4">
            <URLInput
              value={url}
              disabled={status === "loading"}
              onChange={setUrl}
              onSubmit={() => {
                clearOpened();
                void submit();
              }}
            />
          </div>
        </section>

        <div className="mt-6 space-y-4" aria-busy={status === "loading"}>
          {status === "loading" ? <LoadingState /> : null}
          {status === "error" && errorMessage && !showingSaved ? (
            <ErrorState message={errorMessage} code={errorCode} />
          ) : null}
          {showingSaved && opened ? (
            <div className="space-y-3">
              <p className="text-sm text-muted">
                Saved analysis from {formatTimestamp(opened.created_at)}. This is the stored report, not a new score.
              </p>
              <AnalysisResult result={opened} />
            </div>
          ) : null}
          {showingLive && result ? <AnalysisResult result={result} /> : null}
          {status === "idle" && !showingSaved ? (
            <p className="border border-line bg-panel px-4 py-4 text-sm leading-6 text-muted">
              No URL has been analyzed in this session. Enter an http or https address and choose Analyze.
            </p>
          ) : null}
        </div>

        <div className="mt-6">
          <HistoryList
            items={items}
            activeId={opened?.id ?? null}
            loading={loading}
            errorMessage={historyError}
            onOpen={(id) => {
              void openItem(id);
            }}
          />
        </div>
      </main>
    </div>
  );
}
