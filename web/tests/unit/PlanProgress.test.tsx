// The planning progress indicator (TDD plan, iteration 12: WEB-P01 to WEB-P04).
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PlanProgress from "@/components/PlanProgress";
import { UNAVAILABLE_MESSAGE } from "@/lib/messages";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-24T09:00:00Z"));
});
afterEach(() => vi.useRealTimers());

const status = () => screen.getByRole("status");

describe("PlanProgress", () => {
  // WEB-P01 (TP-SRS-020)
  it("shows elapsed time while planning, updated every second", () => {
    render(<PlanProgress state="running" startedAt={Date.now()} />);
    expect(status()).toHaveTextContent("0 s");
    act(() => vi.advanceTimersByTime(3_000));
    expect(status()).toHaveTextContent("3 s");
    act(() => vi.advanceTimersByTime(1_000));
    expect(status()).toHaveTextContent("4 s");
    expect(status()).toHaveAttribute("data-state", "running");
  });

  // WEB-P02 (TP-SRS-021)
  it("marks complete when no part failed", () => {
    const startedAt = Date.now();
    render(<PlanProgress state="complete" startedAt={startedAt} finishedAt={startedAt + 12_000} />);
    expect(status()).toHaveAttribute("data-state", "complete");
    expect(status()).toHaveTextContent("Plan complete");
    expect(status()).toHaveTextContent("12 s");
  });

  // WEB-P03 (TP-SRS-021)
  it("marks partial when a part failed", () => {
    render(<PlanProgress state="partial" startedAt={Date.now()} finishedAt={Date.now() + 5_000} />);
    expect(status()).toHaveAttribute("data-state", "partial");
    expect(status()).toHaveTextContent("Plan partly complete");
  });

  // WEB-P04 (TP-SRS-022)
  it("marks failed when the service is unavailable", () => {
    render(<PlanProgress state="failed" startedAt={Date.now()} finishedAt={Date.now()} />);
    expect(status()).toHaveAttribute("data-state", "failed");
    expect(status()).toHaveTextContent("Planning failed");
    expect(screen.getByRole("alert")).toHaveTextContent(UNAVAILABLE_MESSAGE);
  });

  // The elapsed time stops once the plan has arrived.
  it("stops counting when finished", () => {
    const startedAt = Date.now();
    render(<PlanProgress state="complete" startedAt={startedAt} finishedAt={startedAt + 2_000} />);
    act(() => vi.advanceTimersByTime(10_000));
    expect(status()).toHaveTextContent("2 s");
  });
});
