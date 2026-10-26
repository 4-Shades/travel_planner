// Calling the Host, from server-side code only (TP-SRS-040 to TP-SRS-043).
// "server-only" makes the build fail if this module is ever imported into browser code, so
// HOST_SERVICE_URL and HOST_API_KEY cannot reach a page or script (TP-SRS-042).
import "server-only";

import { UNAVAILABLE_MESSAGE } from "@/lib/messages";
import type { PlanResult, TripPlan } from "@/lib/types";

// The web application waits this long for the Host (TP-SRS-022, TP-SRS-142).
const DEFAULT_TIMEOUT_SECONDS = 180;

function timeoutMillis(): number {
  const seconds = Number(process.env.HOST_TIMEOUT_SECONDS);
  return (Number.isFinite(seconds) && seconds > 0 ? seconds : DEFAULT_TIMEOUT_SECONDS) * 1000;
}

function unavailable(reason: string): PlanResult {
  // The reason goes to the server log only; the traveller sees a plain sentence.
  console.warn(`Planning service unavailable: ${reason}`);
  return { ok: false, message: UNAVAILABLE_MESSAGE };
}

export async function planTrip(trip: unknown): Promise<PlanResult> {
  const baseUrl = process.env.HOST_SERVICE_URL;
  if (!baseUrl) return unavailable("HOST_SERVICE_URL is not set");

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const apiKey = process.env.HOST_API_KEY;
  if (apiKey) headers["X-API-Key"] = apiKey;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMillis());
  try {
    const response = await fetch(`${baseUrl.replace(/\/+$/, "")}/run`, {
      method: "POST",
      headers,
      body: JSON.stringify(trip),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) return unavailable(`the Host answered with status ${response.status}`);
    const plan = (await response.json()) as TripPlan;
    return { ok: true, plan };
  } catch (error) {
    const name = error instanceof Error ? error.name : "unknown error";
    return unavailable(controller.signal.aborted ? "no answer before the timeout" : name);
  } finally {
    clearTimeout(timer);
  }
}
