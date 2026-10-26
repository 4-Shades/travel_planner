import { PART_LABELS } from "@/lib/messages";
import type { ActivityOffer, FlightOffer, StayOffer, TripPlan } from "@/lib/types";

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
  if (rows.length === 0) return <p className="empty">{empty}</p>;
  return (
    <table>
      <caption>{caption}</caption>
      <thead>
        <tr>
          {headings.map((heading) => (
            <th key={heading} scope="col">
              {heading}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>
            {cells(row).map((cell, column) => (
              // data-label lets narrow screens show each cell with its heading.
              <td key={column} data-label={headings[column]}>
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
  return (
    <div className="results">
      {plan.errors.map((error) => (
        // One warning per failed part, naming it (TP-SRS-031).
        <p role="alert" className="warning" key={error.part}>
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

      {plan.sources.length > 0 ? (
        // Collapsed by default; each source with its title, link, and license (TP-SRS-032, TP-SRS-170).
        <details className="sources">
          <summary>Sources</summary>
          <ul>
            {plan.sources.map((source) => (
              <li key={source.url}>
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {source.title}
                </a>{" "}
                <span className="license">({source.license})</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
