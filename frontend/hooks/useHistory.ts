"use client";

import { useCallback, useRef, useState } from "react";

import { AnalyzeError, fetchHistory, fetchHistoryItem } from "@/lib/api";
import type { HistoryDetail, HistoryItem } from "@/types/predict";

export function useHistory() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [opened, setOpened] = useState<HistoryDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      const next = await fetchHistory();
      setItems(next);
      setErrorMessage(null);
    } catch (error) {
      const message = error instanceof AnalyzeError ? error.message : "Recent analyses could not be loaded.";
      setErrorMessage(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const request = useRef<Promise<void> | null>(null);
  if (request.current == null) {
    request.current = reload();
  }

  async function openItem(id: number) {
    try {
      const detail = await fetchHistoryItem(id);
      setOpened(detail);
      setErrorMessage(null);
    } catch (error) {
      const message = error instanceof AnalyzeError ? error.message : "That analysis could not be opened.";
      setErrorMessage(message);
    }
  }

  function clearOpened() {
    setOpened(null);
  }

  return { items, opened, errorMessage, loading, reload, openItem, clearOpened };
}
