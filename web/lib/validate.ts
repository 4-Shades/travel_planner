// Checks made before a trip is sent to the planning service (TP-SRS-011 to TP-SRS-014).

export interface TripFields {
  origin: string;
  destination: string;
  startDate: string;
  endDate: string;
  budget: string;
  travellers: string;
}

export type FieldName = keyof TripFields;
export type Problems = Partial<Record<FieldName, string>>;

export const MIN_BUDGET = 100;
export const BUDGET_STEP = 50;
export const MAX_TRAVELLERS = 9;

const WHOLE_NUMBER = /^\d+$/;

export function travellersProblem(value: string): string | undefined {
  const count = Number(value);
  if (!WHOLE_NUMBER.test(value.trim()) || count < 1 || count > MAX_TRAVELLERS) {
    return `Travellers must be a whole number from 1 to ${MAX_TRAVELLERS}.`;
  }
  return undefined;
}

export function budgetProblem(value: string): string | undefined {
  const amount = Number(value);
  if (value.trim() === "" || !Number.isFinite(amount) || amount < MIN_BUDGET || amount % BUDGET_STEP !== 0) {
    return `Budget must be at least ${MIN_BUDGET} USD, in steps of ${BUDGET_STEP}.`;
  }
  return undefined;
}

/** Every problem with the trip, by field; empty when the trip can be sent. */
export function tripProblems(fields: TripFields): Problems {
  const problems: Problems = {};
  if (!fields.origin.trim()) problems.origin = "Origin is required.";
  if (!fields.destination.trim()) problems.destination = "Destination is required.";
  if (!fields.startDate) problems.startDate = "Start date is required.";
  if (!fields.endDate) problems.endDate = "End date is required.";
  // ISO dates (YYYY-MM-DD) compare correctly as text.
  if (fields.startDate && fields.endDate && fields.endDate <= fields.startDate) {
    problems.endDate = "The end date must be after the start date.";
  }
  const budget = budgetProblem(fields.budget);
  if (budget) problems.budget = budget;
  const travellers = travellersProblem(fields.travellers);
  if (travellers) problems.travellers = travellers;
  return problems;
}
