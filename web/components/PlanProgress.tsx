"use client";

import { useEffect, useState } from "react";

import { UNAVAILABLE_MESSAGE } from "@/lib/messages";

export type ProgressState = "running" | "complete" | "partial" | "failed";

interface Props {
  state: ProgressState;
  startedAt: number;
  finishedAt?: number;
}

// Several times a second, so the shown time is never more than a second behind (TP-SRS-020).
const TICK_MILLIS = 250;

export default function PlanProgress({ state, startedAt, finishedAt }: Props) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (state !== "running") return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), TICK_MILLIS);
    return () => clearInterval(timer);
  }, [state]);

  const end = state === "running" ? now : (finishedAt ?? now);
  const seconds = Math.max(0, Math.floor((end - startedAt) / 1000));
  const text = {
    running: `Planning your trip… ${seconds} s`,
    complete: `Plan complete in ${seconds} s`,
    partial: `Plan partly complete in ${seconds} s: some parts are unavailable.`,
    failed: `Planning failed after ${seconds} s.`,
  }[state];

  return (
    <>
      <div role="status" aria-live="polite" className={`progress progress-${state}`} data-state={state}>
        {state === "running" ? <span className="spinner" aria-hidden="true" /> : null}
        {text}
      </div>
      {state === "failed" ? (
        <p role="alert" className="warning">
          {UNAVAILABLE_MESSAGE}
        </p>
      ) : null}
    </>
  );
}
