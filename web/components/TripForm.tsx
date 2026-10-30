"use client";

import { type FormEvent, useState } from "react";

import type { Trip } from "@/lib/types";
import {
  BUDGET_STEP,
  type FieldName,
  MAX_TRAVELLERS,
  MIN_BUDGET,
  type TripFields,
  budgetProblem,
  travellersProblem,
  tripProblems,
} from "@/lib/validate";

interface Props {
  onSubmit: (trip: Trip) => void;
  busy: boolean;
}

const INITIAL: TripFields = { origin: "", destination: "", startDate: "", endDate: "", budget: "1000", travellers: "1" };

export default function TripForm({ onSubmit, busy }: Props) {
  const [fields, setFields] = useState<TripFields>(INITIAL);
  const [attempted, setAttempted] = useState(false);

  // Number fields are checked as they change; the others when the form is submitted.
  const problems = tripProblems(fields);
  const shown: Partial<Record<FieldName, string>> = attempted
    ? problems
    : { budget: budgetProblem(fields.budget), travellers: travellersProblem(fields.travellers) };

  function update(name: FieldName, value: string) {
    setFields((current) => ({ ...current, [name]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAttempted(true);
    if (Object.keys(problems).length > 0) return;
    onSubmit({
      origin: fields.origin.trim(),
      destination: fields.destination.trim(),
      start_date: fields.startDate,
      end_date: fields.endDate,
      budget: Number(fields.budget),
      travellers: Number(fields.travellers),
      currency: "USD",
    });
  }

  function field(name: FieldName, label: string, input: Record<string, string | number>) {
    const problem = shown[name];
    const problemId = `${name}-problem`;
    return (
      <div>
        <label htmlFor={name} className="mb-1 block font-semibold">
          {label}
        </label>
        <input
          id={name}
          name={name}
          value={fields[name]}
          onChange={(event) => update(name, event.target.value)}
          aria-invalid={problem ? "true" : "false"}
          aria-describedby={problem ? problemId : undefined}
          className="w-full min-w-0 rounded-md border border-border bg-background p-2 text-fg aria-[invalid=true]:border-danger"
          {...input}
        />
        {problem && name !== "origin" && name !== "destination" && name !== "endDate" ? (
          <p id={problemId} className="mt-1 text-sm text-danger">
            {problem}
          </p>
        ) : null}
      </div>
    );
  }

  const summary = attempted ? Object.values(problems) : [];

  return (
    <form className="rounded-lg border border-border bg-surface p-4" onSubmit={handleSubmit} noValidate aria-label="Trip">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(14rem,1fr))] gap-x-4 gap-y-3">
        {/* Example places, as the Streamlit interface showed (TP-SRS-016). */}
        {field("origin", "Origin", { type: "text", autoComplete: "off", maxLength: 120, placeholder: "e.g., New York" })}
        {field("destination", "Destination", { type: "text", autoComplete: "off", maxLength: 120, placeholder: "e.g., Paris" })}
        {field("startDate", "Start date", { type: "date" })}
        {field("endDate", "End date", { type: "date" })}
        {field("budget", "Budget (USD)", { type: "number", min: MIN_BUDGET, step: BUDGET_STEP, inputMode: "numeric" })}
        {field("travellers", "Travellers", { type: "number", min: 1, max: MAX_TRAVELLERS, step: 1, inputMode: "numeric" })}
      </div>
      {summary.length > 0 ? (
        <div role="alert" className="mt-4 text-danger">
          <ul className="list-disc pl-5">
            {summary.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <button
        type="submit"
        disabled={busy}
        className="mt-4 cursor-pointer rounded-md bg-accent px-5 py-2.5 font-semibold text-accent-fg disabled:cursor-progress disabled:opacity-55"
      >
        Plan my trip
      </button>
    </form>
  );
}
