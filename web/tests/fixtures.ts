// Trip plans as the Host returns them, for unit tests and the fake Host.
import type { TripPlan } from "@/lib/types";

export function flight(airline = "Example Air") {
  return {
    airline,
    route: "MNL to HND",
    departure_date: "2026-12-01",
    return_date: "2026-12-06",
    price: 420,
    currency: "USD",
    notes: "Illustrative fare",
  };
}

export function stay(name = "Example Hotel Shinjuku") {
  return { name, area: "Shinjuku", nights: 5, price: 900, currency: "USD", notes: "Near the station" };
}

export function activity(name = "Senso-ji Temple") {
  return { name, description: "Tokyo's oldest temple", price: 0, currency: "USD", notes: "Free entry" };
}

export function plan(overrides: Partial<TripPlan> = {}): TripPlan {
  return {
    request_id: "req-1",
    trip_id: "trip-1",
    flights: [flight(), flight("Other Air")],
    stay: [stay()],
    activities: [activity(), activity("teamLab Planets")],
    errors: [],
    sources: [{ title: "Tokyo", url: "https://en.wikivoyage.org/wiki/Tokyo", license: "CC BY-SA 4.0" }],
    ...overrides,
  };
}

export const validTrip = {
  origin: "Manila",
  destination: "Tokyo",
  start_date: "2026-12-01",
  end_date: "2026-12-06",
  budget: 1500,
  travellers: 2,
  currency: "USD",
};
