const TITLES: Record<string, string> = {
  validation_error: "Invalid URL",
  network_error: "Backend unavailable",
  model_unavailable: "Classification unavailable",
  rate_limited: "Too many requests",
  internal_error: "Analysis could not be completed",
  invalid_response: "Unexpected response",
};

type ErrorStateProps = {
  message: string;
  code: string | null;
};

export function ErrorState({ message, code }: ErrorStateProps) {
  const title = (code && TITLES[code]) || "Analysis failed";

  return (
    <div role="alert" className="border border-phish/30 bg-phish-soft px-4 py-4">
      <p className="text-sm font-semibold text-phish">{title}</p>
      <p className="mt-1 text-sm leading-6 text-foreground">{message}</p>
    </div>
  );
}
