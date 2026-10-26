// POST /api/plan: the browser's only way to the Host (TP-SRS-040).
import { planTrip } from "@/lib/host";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Longer than the 180-second wait for the Host, so the platform does not cut the request off first.
export const maxDuration = 190;

export async function POST(request: Request): Promise<Response> {
  let trip: unknown;
  try {
    trip = await request.json();
  } catch {
    return Response.json({ error: "The trip could not be read." }, { status: 400 });
  }
  const result = await planTrip(trip);
  if (result.ok) return Response.json({ plan: result.plan });
  return Response.json({ error: result.message }, { status: 502 });
}
