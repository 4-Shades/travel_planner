// @vitest-environment node
// The server route that forwards trips to the Host (TDD plan, iteration 11).
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/plan/route";
import { UNAVAILABLE_MESSAGE } from "@/lib/messages";
import { plan, validTrip } from "@/tests/fixtures";

const HOST = "http://host.test";
const KEY = "sentinel-key-4471";

const received: Request[] = [];
const server = setupServer();

// Any request without a handler fails the test, so no test can reach a real service (TP-SRS-187).
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  server.resetHandlers();
  received.length = 0;
  vi.unstubAllEnvs();
  vi.useRealTimers();
});
afterAll(() => server.close());

beforeEach(() => {
  vi.stubEnv("HOST_SERVICE_URL", HOST);
  vi.stubEnv("HOST_API_KEY", "");
});

function hostAnswers(response: () => Response | Promise<Response>) {
  server.use(
    http.post(`${HOST}/run`, async ({ request }) => {
      received.push(request.clone());
      return response();
    }),
  );
}

function post(body: unknown = validTrip) {
  return POST(new Request("http://web.test/api/plan", { method: "POST", body: JSON.stringify(body) }));
}

describe("plan route", () => {
  // WEB-R01 (TP-SRS-040, TP-SRS-041)
  it("forwards the trip to HOST_SERVICE_URL/run", async () => {
    hostAnswers(() => HttpResponse.json(plan()));
    const response = await post();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ plan: plan() });
    expect(received).toHaveLength(1);
    expect(await received[0].json()).toEqual(validTrip);
  });

  // WEB-R01: a trailing slash on HOST_SERVICE_URL is allowed.
  it("accepts a HOST_SERVICE_URL with a trailing slash", async () => {
    vi.stubEnv("HOST_SERVICE_URL", `${HOST}/`);
    hostAnswers(() => HttpResponse.json(plan()));
    expect((await post()).status).toBe(200);
  });

  // WEB-R02 (TP-SRS-043)
  it("sends X-API-Key when HOST_API_KEY is set", async () => {
    vi.stubEnv("HOST_API_KEY", KEY);
    hostAnswers(() => HttpResponse.json(plan()));
    await post();
    expect(received[0].headers.get("X-API-Key")).toBe(KEY);
  });

  // WEB-R03 (TP-SRS-043)
  it("sends no X-API-Key when HOST_API_KEY is unset", async () => {
    hostAnswers(() => HttpResponse.json(plan()));
    await post();
    expect(received[0].headers.has("X-API-Key")).toBe(false);
  });

  // WEB-R04 (TP-SRS-042)
  it.each([200, 401, 500])("never returns the key (Host status %i)", async (status) => {
    vi.stubEnv("HOST_API_KEY", KEY);
    hostAnswers(() => (status === 200 ? HttpResponse.json(plan()) : HttpResponse.json({ detail: KEY }, { status })));
    const response = await post();
    expect(await response.text()).not.toContain(KEY);
    expect([...response.headers.values()].join(" ")).not.toContain(KEY);
  });

  // WEB-R05 (TP-SRS-022)
  it.each([401, 422, 500, 503])("reports unavailable on Host error status %i", async (status) => {
    hostAnswers(() => HttpResponse.json({ detail: "failure" }, { status }));
    const response = await post();
    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ error: UNAVAILABLE_MESSAGE });
  });

  // WEB-R05: an answer that is not JSON counts as an error too.
  it("reports unavailable when the Host answers with something that is not JSON", async () => {
    hostAnswers(() => new HttpResponse("<html>proxy error</html>", { status: 200 }));
    expect(await (await post()).json()).toEqual({ error: UNAVAILABLE_MESSAGE });
  });

  // WEB-R06 (TP-SRS-022)
  it("reports unavailable when the Host cannot be reached", async () => {
    hostAnswers(() => HttpResponse.error());
    const response = await post();
    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ error: UNAVAILABLE_MESSAGE });
  });

  // WEB-R06: a missing HOST_SERVICE_URL is reported the same way.
  it("reports unavailable when HOST_SERVICE_URL is not set", async () => {
    vi.stubEnv("HOST_SERVICE_URL", "");
    expect(await (await post()).json()).toEqual({ error: UNAVAILABLE_MESSAGE });
  });

  // WEB-R07 (TP-SRS-022, TP-SRS-142)
  it("gives up after 180 seconds", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    hostAnswers(() => new Promise<Response>(() => {}));
    let settled = false;
    const pending = post().then((response) => {
      settled = true;
      return response;
    });
    await vi.advanceTimersByTimeAsync(179_000);
    expect(settled).toBe(false);
    await vi.advanceTimersByTimeAsync(1_000);
    const response = await pending;
    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ error: UNAVAILABLE_MESSAGE });
  });

  // WEB-R07: HOST_TIMEOUT_SECONDS can shorten the wait for tests and demonstrations.
  it("uses HOST_TIMEOUT_SECONDS when set", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    vi.stubEnv("HOST_TIMEOUT_SECONDS", "5");
    hostAnswers(() => new Promise<Response>(() => {}));
    const pending = post();
    await vi.advanceTimersByTimeAsync(5_000);
    expect((await pending).status).toBe(502);
  });

  // WEB-R08 (TP-SRS-132)
  it("error messages are plain", () => {
    expect(UNAVAILABLE_MESSAGE).toBe("The planning service is unavailable. Please try again later.");
    for (const text of ["Ollama", "OpenAI", "Traceback", "http", "X-API-Key", "Error:"]) {
      expect(UNAVAILABLE_MESSAGE).not.toContain(text);
    }
  });

  // A request body that is not JSON is never sent on.
  it("rejects a body that is not JSON", async () => {
    const response = await POST(new Request("http://web.test/api/plan", { method: "POST", body: "{not json" }));
    expect(response.status).toBe(400);
    expect(received).toHaveLength(0);
  });
});
