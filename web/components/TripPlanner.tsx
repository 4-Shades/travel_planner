"use client";

import { useState } from "react";

import PlanProgress, { type ProgressState } from "@/components/PlanProgress";
import PlanResults from "@/components/PlanResults";
import TripForm from "@/components/TripForm";
import { UNAVAILABLE_MESSAGE } from "@/lib/messages";
import type { PlanResult, Trip, TripPlan } from "@/lib/types";

// TP-SRS-033
export const ILLUSTRATIVE_NOTICE =
  "Suggestions are illustrative: they are not live availability or prices, and they are not bookable.";

async function requestPlan(trip: Trip): Promise<PlanResult> {
  try {
    // The page talks only to its own server, never to the Host (TP-SRS-040).
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(trip),
    });
    const body = await response.json();
    if (response.ok && body.plan) return { ok: true, plan: body.plan as TripPlan };
    return { ok: false, message: UNAVAILABLE_MESSAGE };
  } catch {
    return { ok: false, message: UNAVAILABLE_MESSAGE };
  }
}

interface Progress {
  state: ProgressState;
  startedAt: number;
  finishedAt?: number;
}

export default function TripPlanner() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [plan, setPlan] = useState<TripPlan | null>(null);

  async function submitTrip(trip: Trip) {
    setPlan(null);
    setProgress({ state: "running", startedAt: Date.now() });
    const result = await requestPlan(trip);
    const finishedAt = Date.now();
    if (result.ok) {
      setPlan(result.plan);
      setProgress((p) => ({ startedAt: p!.startedAt, finishedAt, state: result.plan.errors.length ? "partial" : "complete" }));
    } else {
      setProgress((p) => ({ startedAt: p!.startedAt, finishedAt, state: "failed" }));
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 pt-6 pb-12">
      <header className="mb-4 space-y-3">
        <h1 className="mb-1 text-[1.75rem] font-bold">Travel planner</h1>
        <p>Suggestions for flights, places to stay, and things to do on your trip.</p>
        <p className="text-sm text-muted">{ILLUSTRATIVE_NOTICE}</p>
      </header>

      <TripForm onSubmit={submitTrip} busy={progress?.state === "running"} />

      {progress ? (
        // Results appear in place, without reloading the page (TP-SRS-133).
        <section aria-label="Results" className="mt-6">
          <PlanProgress {...progress} />
          {plan ? <PlanResults plan={plan} /> : null}
        </section>
      ) : null}
    </main>
  );
}
