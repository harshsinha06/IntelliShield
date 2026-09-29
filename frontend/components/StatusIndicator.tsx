"use client";

import { useEffect, useState } from "react";

import { fetchHealth } from "@/lib/api";

type EngineStatus = "checking" | "online" | "degraded" | "offline";

const LABEL: Record<EngineStatus, string> = {
  checking: "Checking analysis engine",
  online: "Analysis engine online",
  degraded: "Analysis engine reachable, model not loaded",
  offline: "Analysis engine unreachable",
};

const DOT: Record<EngineStatus, string> = {
  checking: "bg-muted",
  online: "bg-safe",
  degraded: "bg-warn",
  offline: "bg-phish",
};

export function StatusIndicator() {
  const [status, setStatus] = useState<EngineStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const health = await fetchHealth();
        if (!cancelled) setStatus(health.model_loaded ? "online" : "degraded");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    }

    void check();
    const timer = window.setInterval(() => {
      void check();
    }, 30_000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <p className="inline-flex items-center gap-2 text-sm text-foreground" role="status" aria-live="polite">
      <span className={`size-2 shrink-0 rounded-full ${DOT[status]}`} aria-hidden="true" />
      {LABEL[status]}
    </p>
  );
}
