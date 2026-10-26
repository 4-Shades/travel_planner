// Fixtures shared by the browser scenarios: the fake Host, the app under test, and the page.
import { type Page, type Request } from "@playwright/test";
import { createBdd, test as base } from "playwright-bdd";

import { APP_WITH_KEY, FAKE_HOST } from "../../../playwright.config";
import { plan } from "../../fixtures";
import type { TripPlan } from "../../../lib/types";

export interface HostRequest {
  path: string;
  headers: Record<string, string | undefined>;
  body: Record<string, unknown> | null;
}

/** Tells the fake Host how to answer, and reads back what it received. */
export class FakeHost {
  /** The plan the Host will return; steps adjust it before the trip is submitted. */
  plan: TripPlan = plan();
  private delayMs = 0;

  async reset() {
    this.plan = plan();
    this.delayMs = 0;
    await fetch(`${FAKE_HOST}/__control/reset`, { method: "POST" });
  }

  async answerWithPlan(changes: Partial<TripPlan> = {}, delayMs = this.delayMs) {
    this.plan = { ...this.plan, ...changes };
    this.delayMs = delayMs;
    await this.setBehaviour({ kind: "plan", plan: this.plan, delayMs });
  }

  async answerWithStatus(status: number) {
    await this.setBehaviour({ kind: "status", status });
  }

  async hang() {
    await this.setBehaviour({ kind: "hang" });
  }

  async drop() {
    await this.setBehaviour({ kind: "drop" });
  }

  async requests(): Promise<HostRequest[]> {
    return (await fetch(`${FAKE_HOST}/__control/requests`)).json();
  }

  private async setBehaviour(behaviour: unknown) {
    await fetch(`${FAKE_HOST}/__control/behaviour`, { method: "POST", body: JSON.stringify(behaviour) });
  }
}

/** The web application under test: which copy of it, and what the browser has sent. */
export class App {
  baseURL = APP_WITH_KEY;
  browserRequests: string[] = [];

  constructor(readonly page: Page) {
    page.on("request", (request: Request) => this.browserRequests.push(request.url()));
  }

  async open() {
    await this.page.goto(`${this.baseURL}/`);
  }

  async fillValidTrip() {
    const page = this.page;
    await page.getByLabel("Origin").fill("Manila");
    await page.getByLabel("Destination").fill("Tokyo");
    await page.getByLabel("Start date").fill("2026-12-01");
    await page.getByLabel("End date").fill("2026-12-06");
    await page.getByLabel("Budget (USD)").fill("1500");
    await page.getByLabel("Travellers").fill("2");
  }

  submitButton() {
    return this.page.getByRole("button", { name: "Plan my trip" });
  }

  progress() {
    return this.page.getByRole("status");
  }

  async waitForPlan() {
    await this.page.locator('[role="status"]:not([data-state="running"])').waitFor();
  }
}

export const test = base.extend<{ host: FakeHost; app: App }>({
  host: async ({}, use) => {
    const host = new FakeHost();
    await host.reset();
    await use(host);
  },
  app: async ({ page }, use) => {
    await use(new App(page));
  },
});

export const { Given, When, Then } = createBdd(test);
