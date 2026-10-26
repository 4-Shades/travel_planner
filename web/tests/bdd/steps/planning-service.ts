// Steps that set up the planning service (the fake Host) and check what it received.
import { expect } from "@playwright/test";

import { APP_WITHOUT_KEY, APP_WITH_KEY, FAKE_HOST, TEST_HOST_API_KEY } from "../../../playwright.config";
import { activity, flight, stay } from "../../fixtures";
import type { Part } from "../../../lib/types";
import { Given, Then } from "./fixtures";

function times<T>(count: number, make: (n: number) => T): T[] {
  return Array.from({ length: count }, (_, n) => make(n + 1));
}

Given("the planning service is available", async ({ host }) => {
  await host.answerWithPlan();
});

Given("the planning service takes {int} seconds to answer", async ({ host }, seconds: number) => {
  await host.answerWithPlan({}, seconds * 1000);
});

Given("the planning service returns a plan with no errors", async ({ host }) => {
  await host.answerWithPlan({ errors: [] });
});

Given("the planning service returns a plan in which the flights part failed", async ({ host }) => {
  await host.answerWithPlan({ flights: [], errors: [{ part: "flights", message: "Service is temporarily unavailable." }] });
});

Given(
  "the planning service returns a plan with {int} flights, {int} stays, and {int} activities",
  async ({ host }, flights: number, stays: number, activities: number) => {
    await host.answerWithPlan({
      flights: times(flights, (n) => flight(`Airline ${n}`)),
      stay: times(stays, (n) => stay(`Hotel ${n}`)),
      activities: times(activities, (n) => activity(`Activity ${n}`)),
    });
  },
);

Given("the planning service returns a plan with these errors:", async ({ host }, table) => {
  const errors = table.hashes().map((row: { part: Part; message: string }) => ({ part: row.part, message: row.message }));
  const emptied = Object.fromEntries(errors.map((error: { part: Part }) => [error.part, []]));
  await host.answerWithPlan({ ...emptied, errors });
});

Given("the plan has {int} stays", async ({ host }, stays: number) => {
  await host.answerWithPlan({ stay: times(stays, (n) => stay(`Hotel ${n}`)) });
});

Given("the planning service returns a plan with these sources:", async ({ host }, table) => {
  await host.answerWithPlan({ sources: table.hashes() });
});

Given("the planning service returns a plan with no sources", async ({ host }) => {
  await host.answerWithPlan({ sources: [] });
});

Given("the planning service cannot be reached", async ({ host }) => {
  await host.drop();
});

Given("the planning service returns status {int}", async ({ host }, status: number) => {
  await host.answerWithStatus(status);
});

// The test servers give up after HOST_TIMEOUT_SECONDS=8 rather than 180 (see playwright.config.ts).
Given("the planning service does not answer within {int} seconds", async ({ host }, _seconds: number) => {
  await host.hang();
});

Given("HOST_SERVICE_URL points at the planning service", async ({ app }) => {
  // Both test servers are started with HOST_SERVICE_URL set to the fake Host.
  app.baseURL = APP_WITH_KEY;
  expect(FAKE_HOST).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
});

Given("HOST_API_KEY is set to {string}", async ({ app }, key: string) => {
  expect(key).toBe(TEST_HOST_API_KEY);
  app.baseURL = APP_WITH_KEY;
});

Given("HOST_API_KEY is not set", async ({ app }) => {
  app.baseURL = APP_WITHOUT_KEY;
});

Then("no request is sent to the planning service", async ({ host, page }) => {
  // Long enough for a request that was going to be sent to have arrived.
  await page.waitForTimeout(500);
  expect(await host.requests()).toEqual([]);
});

Then("the planning service receives the trip at {string}", async ({ host }, path: string) => {
  const [received] = await host.requests();
  expect(received.path).toBe(path);
  expect(received.body).toMatchObject({ origin: "Manila", destination: "Tokyo", travellers: 2 });
});

Then("the planning service receives the header {string}", async ({ host }, header: string) => {
  const [name, value] = header.split(": ");
  const [received] = await host.requests();
  expect(received.headers[name.toLowerCase()]).toBe(value);
});

Then("the planning service receives no {string} header", async ({ host }, name: string) => {
  const [received] = await host.requests();
  expect(received.headers[name.toLowerCase()]).toBeUndefined();
});

Then("my browser sends no request to the planning service's address", async ({ app }) => {
  expect(app.browserRequests.length).toBeGreaterThan(0);
  expect(app.browserRequests.filter((url) => url.startsWith(FAKE_HOST))).toEqual([]);
});
