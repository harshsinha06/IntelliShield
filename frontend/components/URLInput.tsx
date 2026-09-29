"use client";

type URLInputProps = {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function URLInput({ value, disabled, onChange, onSubmit }: URLInputProps) {
  return (
    <form
      className="flex flex-col gap-3 sm:flex-row sm:items-end"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="min-w-0 flex-1">
        <label htmlFor="url" className="mb-1.5 block text-sm font-medium text-foreground">
          Enter URL to analyze
        </label>
        <input
          id="url"
          name="url"
          type="text"
          inputMode="url"
          autoComplete="off"
          spellCheck={false}
          value={value}
          disabled={disabled}
          placeholder="https://example.com"
          aria-describedby="url-help"
          onChange={(event) => onChange(event.target.value)}
          className="w-full border border-line bg-panel px-3 py-2 font-mono text-sm text-foreground outline-none placeholder:text-muted/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:bg-header disabled:text-muted"
        />
      </div>
      <button
        type="submit"
        disabled={disabled}
        className="inline-flex h-10 shrink-0 items-center justify-center bg-accent px-4 text-sm font-medium text-white outline-none hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60"
      >
        Analyze
      </button>
    </form>
  );
}
