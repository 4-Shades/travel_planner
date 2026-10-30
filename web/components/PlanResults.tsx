import { WARNING } from "@/components/styles";
import { PART_LABELS } from "@/lib/messages";
import type { ActivityOffer, FlightOffer, StayOffer, TripPlan } from "@/lib/types";

// TP-SRS-034
export const EMPTY_PLAN_HINT = "No trip options were returned. Try adjusting the travel dates or budget.";

const EMPTY = {
  flights: "No flight suggestions.",
  stay: "No accommodation suggestions.",
  activities: "No activity suggestions.",
};

function price(amount: number, currency: string) {
  return `${amount.toLocaleString("en-US", { maximumFractionDigits: 2 })} ${currency}`;
}

function Table<T>({ caption, headings, rows, empty, cells }: {
  caption: string;
  headings: string[];
  rows: T[];
  empty: string;
  cells: (row: T) => string[];
}) {
  if (rows.length === 0) return <p className="mt-5 text-muted">{empty}</p>;
  return (
    // Narrow screens show each row as a card, with each value under its heading (TP-SRS-131).
    <table className="mt-5 w-full border-collapse border border-border bg-surface max-sm:block max-sm:border-0 max-sm:bg-transparent">
      <caption className="pb-2 text-left text-lg font-bold max-sm:block">{caption}</caption>
      <thead className="max-sm:sr-only">
        <tr>
          {headings.map((heading) => (
            <th key={heading} scope="col" className="border-t border-border px-3 py-2 text-left align-top wrap-anywhere max-sm:border-0 bg-background">
              {heading}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="max-sm:block">
        {rows.map((row, index) => (
          <tr key={index} className="max-sm:mb-3 max-sm:block max-sm:rounded-md max-sm:border max-sm:border-border max-sm:bg-surface">
            {cells(row).map((cell, column) => (
              // data-label lets narrow screens show each cell with its heading.
              <td
                key={column}
                data-label={headings[column]}
                className="border-t border-border px-3 py-2 text-left align-top wrap-anywhere max-sm:border-0 max-sm:block max-sm:py-1.5 max-sm:before:block max-sm:before:text-xs max-sm:before:font-semibold max-sm:before:text-muted max-sm:before:content-[attr(data-label)]"
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function PlanResults({ plan }: { plan: TripPlan }) {
  const empty = plan.flights.length === 0 && plan.stay.length === 0 && plan.activities.length === 0;
  return (
    <div>
      {plan.errors.map((error) => (
        // One warning per failed part, naming it (TP-SRS-031).
        <p role="alert" className={WARNING} key={error.part}>
          {PART_LABELS[error.part]}: {error.message}
        </p>
      ))}

      <Table<FlightOffer>
        caption={PART_LABELS.flights}
        headings={["Airline", "Route", "Dates", "Price", "Notes"]}
        rows={plan.flights}
        empty={EMPTY.flights}
        cells={(f) => [f.airline, f.route, f.return_date ? `${f.departure_date} to ${f.return_date}` : f.departure_date, price(f.price, f.currency), f.notes]}
      />
      <Table<StayOffer>
        caption={PART_LABELS.stay}
        headings={["Name", "Area", "Nights", "Price", "Notes"]}
        rows={plan.stay}
        empty={EMPTY.stay}
        cells={(s) => [s.name, s.area, String(s.nights), price(s.price, s.currency), s.notes]}
      />
      <Table<ActivityOffer>
        caption={PART_LABELS.activities}
        headings={["Name", "Description", "Price", "Notes"]}
        rows={plan.activities}
        empty={EMPTY.activities}
        cells={(a) => [a.name, a.description, price(a.price, a.currency), a.notes]}
      />

      {empty ? <p className="mt-5 font-semibold">{EMPTY_PLAN_HINT}</p> : null}

      {plan.sources.length > 0 ? (
        // Collapsed by default; each source with its title, link, and license (TP-SRS-032, TP-SRS-170).
        <details className="mt-6">
          <summary className="cursor-pointer font-semibold">Sources ({plan.sources.length})</summary>
          <p className="mt-2 text-sm text-muted">Suggestions drew on these travel-guide excerpts.</p>
          <ul className="mt-2 list-disc pl-5">
            {plan.sources.map((source) => (
              <li key={source.url}>
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.title}
                </a>{" "}
                <span className="text-sm text-muted">({source.license})</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
