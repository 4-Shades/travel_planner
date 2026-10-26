// The trip form (TDD plan, iteration 12: WEB-F01 to WEB-F07).
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import TripForm from "@/components/TripForm";

const LABELS = ["Origin", "Destination", "Start date", "End date", "Budget (USD)", "Travellers"];

function setup(busy = false) {
  const onSubmit = vi.fn();
  const user = userEvent.setup();
  render(<TripForm onSubmit={onSubmit} busy={busy} />);
  return { onSubmit, user };
}

async function fillValidTrip(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Origin"), "Manila");
  await user.type(screen.getByLabelText("Destination"), "Tokyo");
  await user.type(screen.getByLabelText("Start date"), "2026-12-01");
  await user.type(screen.getByLabelText("End date"), "2026-12-06");
  await user.clear(screen.getByLabelText("Budget (USD)"));
  await user.type(screen.getByLabelText("Budget (USD)"), "1500");
}

async function setField(user: ReturnType<typeof userEvent.setup>, label: string, value: string) {
  const field = screen.getByLabelText(label);
  await user.clear(field);
  if (value) await user.type(field, value);
}

const submit = () => screen.getByRole("button", { name: "Plan my trip" });

describe("TripForm", () => {
  // WEB-F01 (TP-SRS-010, TP-SRS-130)
  it("shows every field with a visible label", () => {
    setup();
    for (const label of LABELS) {
      const field = screen.getByLabelText(label);
      expect(field).toBeVisible();
      expect(screen.getByText(label, { selector: "label" })).toBeVisible();
    }
  });

  // WEB-F02 (TP-SRS-011)
  it("defaults travellers to 1", () => {
    setup();
    expect(screen.getByLabelText("Travellers")).toHaveValue(1);
  });

  // WEB-F02 (TP-SRS-011)
  it.each([
    ["1", true],
    ["9", true],
    ["0", false],
    ["10", false],
    ["2.5", false],
  ])("travellers %s is valid: %s", async (value, valid) => {
    const { onSubmit, user } = setup();
    await fillValidTrip(user);
    await setField(user, "Travellers", value);
    expect(screen.getByLabelText("Travellers")).toHaveAttribute("aria-invalid", String(!valid));
    await user.click(submit());
    expect(onSubmit).toHaveBeenCalledTimes(valid ? 1 : 0);
  });

  // WEB-F03 (TP-SRS-012)
  it.each([
    ["100", true],
    ["150", true],
    ["5000", true],
    ["99", false],
    ["125", false],
    ["50", false],
  ])("budget %s is valid: %s", async (value, valid) => {
    const { onSubmit, user } = setup();
    await fillValidTrip(user);
    await setField(user, "Budget (USD)", value);
    expect(screen.getByLabelText("Budget (USD)")).toHaveAttribute("aria-invalid", String(!valid));
    await user.click(submit());
    expect(onSubmit).toHaveBeenCalledTimes(valid ? 1 : 0);
  });

  // WEB-F04 (TP-SRS-013)
  it.each(["Origin", "Destination"])("warns and does not send when %s is empty", async (label) => {
    const { onSubmit, user } = setup();
    await fillValidTrip(user);
    await setField(user, label, "");
    await user.click(submit());
    expect(screen.getByRole("alert")).toHaveTextContent(`${label} is required.`);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  // WEB-F04: a place name of only spaces counts as empty.
  it("treats a blank origin as empty", async () => {
    const { onSubmit, user } = setup();
    await fillValidTrip(user);
    await setField(user, "Origin", "   ");
    await user.click(submit());
    expect(screen.getByRole("alert")).toHaveTextContent("Origin is required.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  // WEB-F05 (TP-SRS-014)
  it.each(["2026-12-06", "2026-12-05"])("warns and does not send when the end date is %s", async (end) => {
    const { onSubmit, user } = setup();
    await fillValidTrip(user);
    await setField(user, "Start date", "2026-12-06");
    await setField(user, "End date", end);
    await user.click(submit());
    expect(screen.getByRole("alert")).toHaveTextContent("The end date must be after the start date.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  // WEB-F05: a valid trip is sent with the fields the Host expects.
  it("sends a valid trip", async () => {
    const { onSubmit, user } = setup();
    await fillValidTrip(user);
    await setField(user, "Travellers", "2");
    await user.click(submit());
    expect(onSubmit).toHaveBeenCalledWith({
      origin: "Manila",
      destination: "Tokyo",
      start_date: "2026-12-01",
      end_date: "2026-12-06",
      budget: 1500,
      travellers: 2,
      currency: "USD",
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  // WEB-F06 (TP-SRS-015)
  it("disables submit while planning", () => {
    setup(true);
    expect(submit()).toBeDisabled();
  });

  // WEB-F07 (TP-SRS-130)
  it("can be completed with the keyboard alone", async () => {
    const { onSubmit, user } = setup();
    await user.tab();
    expect(screen.getByLabelText("Origin")).toHaveFocus();
    await user.keyboard("Manila");
    await user.tab();
    await user.keyboard("Tokyo");
    await user.tab();
    await user.keyboard("2026-12-01");
    await user.tab();
    await user.keyboard("2026-12-06");
    await user.tab();
    expect(screen.getByLabelText("Budget (USD)")).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText("Travellers")).toHaveFocus();
    await user.tab();
    expect(submit()).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
