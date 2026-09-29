"use client";

import { useRef, useState } from "react";

import { AnalyzeError, analyzeUrl } from "@/lib/api";
import type { PredictResponse } from "@/types/predict";

export type AnalyzeStatus = "idle" | "loading" | "success" | "error";

export function useAnalyzeUrl() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<AnalyzeStatus>("idle");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const requestId = useRef(0);

  async function submit() {
    const id = requestId.current + 1;
    requestId.current = id;
    setStatus("loading");
    setResult(null);
    setErrorMessage(null);
    setErrorCode(null);
    try {
      const next = await analyzeUrl(url);
      if (requestId.current !== id) return;
      setResult(next);
      setStatus("success");
    } catch (error) {
      if (requestId.current !== id) return;
      const message =
        error instanceof AnalyzeError ? error.message : "The analysis could not be completed.";
      const code = error instanceof AnalyzeError ? error.code : "request_failed";
      setErrorMessage(message);
      setErrorCode(code);
      setStatus("error");
    }
  }

  return { url, setUrl, status, result, errorMessage, errorCode, submit };
}
