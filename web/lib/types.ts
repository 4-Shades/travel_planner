// The Host's data contracts, as defined in shared/schemas.py (TP-SRS-162).

export type Part = "flights" | "stay" | "activities";

export interface Trip {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  travellers: number;
  currency: string;
}

export interface FlightOffer {
  airline: string;
  route: string;
  departure_date: string;
  return_date: string | null;
  price: number;
  currency: string;
  notes: string;
}

export interface StayOffer {
  name: string;
  area: string;
  nights: number;
  price: number;
  currency: string;
  notes: string;
}

export interface ActivityOffer {
  name: string;
  description: string;
  price: number;
  currency: string;
  notes: string;
}

export interface PartError {
  part: Part;
  message: string;
}

export interface Source {
  title: string;
  url: string;
  license: string;
}

export interface TripPlan {
  request_id: string;
  trip_id: string;
  flights: FlightOffer[];
  stay: StayOffer[];
  activities: ActivityOffer[];
  errors: PartError[];
  sources: Source[];
}

export type PlanResult = { ok: true; plan: TripPlan } | { ok: false; message: string };
