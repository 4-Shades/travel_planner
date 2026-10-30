"use client";

import { useEffect, useState } from "react";

import { WARNING } from "@/components/styles";
import { UNAVAILABLE_MESSAGE } from "@/lib/messages";

export type ProgressState = "running" | "complete" | "partial" | "failed";

interface Props {
  state: ProgressState;
  startedAt: number;
  finishedAt?: number;
}

// TP-SRS-023
export const PROGRESS_NOTE =
  "The flight, stay, and activities agents are working in parallel. With a local model this usually takes one to two minutes.";

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
      <div
        role="status"
        aria-live="polite"
        data-state={state}
        className="flex items-center gap-2 rounded-md border border-border bg-surface px-4 py-3 font-semibold data-[state=complete]:text-success data-[state=failed]:text-danger data-[state=partial]:text-warning"
      >
        {state === "running" ? (
          <span
            aria-hidden="true"
            className="size-4 animate-spin rounded-full border-2 border-border border-t-accent motion-reduce:animate-none"
          />
        ) : null}
        {text}
      </div>
      {state === "running" ? <p className="mt-2 text-sm text-muted">{PROGRESS_NOTE}</p> : null}
      {state === "failed" ? (
        <p role="alert" className={WARNING}>
          {UNAVAILABLE_MESSAGE}
        </p>
      ) : null}
    </>
  );
}
