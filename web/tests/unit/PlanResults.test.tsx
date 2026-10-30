// The results: tables, warnings, and sources (TDD plan, iteration 12: WEB-T01 to WEB-T05).
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import PlanResults from "@/components/PlanResults";
import TripPlanner, { ILLUSTRATIVE_NOTICE } from "@/components/TripPlanner";
import { activity, flight, plan, stay } from "@/tests/fixtures";

function rows(tableName: string) {
  const table = screen.getByRole("table", { name: tableName });
  return within(table).getAllByRole("row").slice(1); // without the header row
}

describe("PlanResults", () => {
  // WEB-T01 (TP-SRS-030)
  it("shows three result tables with one row per offer", () => {
    render(
      <PlanResults
        plan={plan({
          flights: [flight("A"), flight("B"), flight("C")],
          stay: [stay("D"), stay("E")],
          activities: [activity("F"), activity("G"), activity("H")],
        })}
      />,
    );
    expect(rows("Flights")).toHaveLength(3);
    expect(rows("Accommodation")).toHaveLength(2);
    expect(rows("Activities")).toHaveLength(3);
    expect(rows("Flights")[0]).toHaveTextContent("A");
    expect(rows("Flights")[0]).toHaveTextContent("420 USD");
  });

  // WEB-T01: a part with no offers says so instead of showing an empty table.
  it("says when a part has no suggestions", () => {
    render(<PlanResults plan={plan({ stay: [] })} />);
    expect(screen.queryByRole("table", { name: "Accommodation" })).not.toBeInTheDocument();
    expect(screen.getByText("No accommodation suggestions.")).toBeVisible();
  });

  // WEB-T02 (TP-SRS-031)
  it("shows a warning per failed part, naming it", () => {
    render(
      <PlanResults
        plan={plan({
          flights: [],
          activities: [],
          errors: [
            { part: "flights", message: "Service is temporarily unavailable." },
            { part: "activities", message: "Activity planner is temporarily unavailable." },
          ],
        })}
      />,
    );
    const warnings = screen.getAllByRole("alert");
    expect(warnings).toHaveLength(2);
    expect(warnings[0]).toHaveTextContent("Flights: Service is temporarily unavailable.");
    expect(warnings[1]).toHaveTextContent("Activities: Activity planner is temporarily unavailable.");
    expect(rows("Accommodation")).toHaveLength(1);
  });

  // WEB-T03 (TP-SRS-032, TP-SRS-170)
  it("lists sources collapsed, with links and licenses", async () => {
    const user = userEvent.setup();
    render(
      <PlanResults
        plan={plan({
          sources: [
            { title: "Tokyo", url: "https://en.wikivoyage.org/wiki/Tokyo", license: "CC BY-SA 4.0" },
            { title: "Kyoto", url: "https://en.wikivoyage.org/wiki/Kyoto", license: "CC BY-SA 4.0" },
          ],
        })}
      />,
    );
    const summary = screen.getByText("Sources (2)");
    const details = summary.closest("details")!;
    expect(details).not.toHaveAttribute("open");
    await user.click(summary);
    expect(details).toHaveAttribute("open");
    expect(within(details).getByText("Suggestions drew on these travel-guide excerpts.")).toBeVisible();
    const link = within(details).getByRole("link", { name: "Kyoto" });
    expect(link).toHaveAttribute("href", "https://en.wikivoyage.org/wiki/Kyoto");
    expect(link.closest("li")).toHaveTextContent("CC BY-SA 4.0");
  });

  // WEB-T04 (TP-SRS-032)
  it("hides sources when there are none", () => {
    render(<PlanResults plan={plan({ sources: [] })} />);
    expect(screen.queryByText(/^Sources/)).not.toBeInTheDocument();
  });

  // WEB-T06 (TP-SRS-034)
  it("suggests changing the trip when nothing was returned", () => {
    const hint = "No trip options were returned. Try adjusting the travel dates or budget.";
    const { rerender } = render(<PlanResults plan={plan({ flights: [], stay: [], activities: [], sources: [] })} />);
    expect(screen.getByText(hint)).toBeVisible();
    rerender(<PlanResults plan={plan({ flights: [], stay: [] })} />);
    expect(screen.queryByText(hint)).not.toBeInTheDocument();
  });

  // WEB-T05 (TP-SRS-033)
  it("states that suggestions are illustrative", () => {
    render(<TripPlanner />);
    expect(screen.getByText(ILLUSTRATIVE_NOTICE)).toBeVisible();
    expect(ILLUSTRATIVE_NOTICE).toMatch(/illustrative/);
    expect(ILLUSTRATIVE_NOTICE).toMatch(/not live/);
    expect(ILLUSTRATIVE_NOTICE).toMatch(/not bookable/);
  });
});
