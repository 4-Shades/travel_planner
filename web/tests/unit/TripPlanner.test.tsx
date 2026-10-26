// The whole page: form, progress, and results together (TP-SRS-015, TP-SRS-021, TP-SRS-022, TP-SRS-133).
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import TripPlanner from "@/components/TripPlanner";
import { UNAVAILABLE_MESSAGE } from "@/lib/messages";
import { plan } from "@/tests/fixtures";

afterEach(() => vi.unstubAllGlobals());

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

async function submitTrip(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Origin"), "Manila");
  await user.type(screen.getByLabelText("Destination"), "Tokyo");
  await user.type(screen.getByLabelText("Start date"), "2026-12-01");
  await user.type(screen.getByLabelText("End date"), "2026-12-06");
  await user.click(screen.getByRole("button", { name: "Plan my trip" }));
}

describe("TripPlanner", () => {
  // WEB-F06 (TP-SRS-015), WEB-P02 (TP-SRS-021)
  it("posts the trip to /api/plan, disables submit until the plan arrives, then shows it", async () => {
    const answer = deferred<Response>();
    const fetchMock = vi.fn(() => answer.promise);
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<TripPlanner />);

    await submitTrip(user);
    expect(screen.getByRole("button", { name: "Plan my trip" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "running");
    expect(fetchMock).toHaveBeenCalledWith("/api/plan", expect.objectContaining({ method: "POST" }));

    answer.resolve(Response.json({ plan: plan() }));
    expect(await screen.findByRole("table", { name: "Flights" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Plan my trip" })).toBeEnabled();
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "complete");
  });

  // WEB-P03 (TP-SRS-021)
  it("marks the plan partial when a part failed", async () => {
    const failed = plan({ flights: [], errors: [{ part: "flights", message: "Service is temporarily unavailable." }] });
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ plan: failed })));
    const user = userEvent.setup();
    render(<TripPlanner />);
    await submitTrip(user);
    expect(await screen.findByText("Flights: Service is temporarily unavailable.")).toBeVisible();
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "partial");
  });

  // WEB-P04 (TP-SRS-022)
  it.each([
    ["an error answer", () => Promise.resolve(Response.json({ error: UNAVAILABLE_MESSAGE }, { status: 502 }))],
    ["a network failure", () => Promise.reject(new TypeError("Failed to fetch"))],
  ])("shows the unavailable message after %s", async (_, answer) => {
    vi.stubGlobal("fetch", vi.fn(answer));
    const user = userEvent.setup();
    render(<TripPlanner />);
    await submitTrip(user);
    expect(await screen.findByText(UNAVAILABLE_MESSAGE)).toBeVisible();
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "failed");
    expect(screen.getByRole("button", { name: "Plan my trip" })).toBeEnabled();
  });

  // The progress indicator is the first thing in the results area (TP-SRS-020).
  it("puts the progress indicator at the top of the results area", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ plan: plan() })));
    const user = userEvent.setup();
    render(<TripPlanner />);
    await submitTrip(user);
    await screen.findByRole("table", { name: "Flights" });
    const results = screen.getByRole("region", { name: "Results" });
    expect(results.firstElementChild).toBe(screen.getByRole("status"));
  });
});
