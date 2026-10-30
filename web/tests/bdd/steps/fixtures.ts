// Fixtures shared by the browser scenarios: the fake Host, the app under test, and the page.
import fs from "node:fs";
import path from "node:path";

import { type Page, type Request, type Response } from "@playwright/test";
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
  /** Every response the browser received: pages, scripts, styles, and API answers. */
  browserResponses: Response[] = [];
  /** Horizontal overflow, in pixels, measured before a plan was requested. */
  overflowBefore: number | null = null;

  constructor(readonly page: Page) {
    page.on("request", (request: Request) => this.browserRequests.push(request.url()));
    page.on("response", (response: Response) => this.browserResponses.push(response));
  }

  async open() {
    await this.page.goto(`${this.baseURL}/`);
    // A marker that a full page reload would wipe out (TP-SRS-133).
    await this.page.evaluate(() => ((window as unknown as { plannerMarker: string }).plannerMarker = "set"));
  }

  async wasReloaded() {
    return this.page.evaluate(() => (window as unknown as { plannerMarker?: string }).plannerMarker !== "set");
  }

  /** How far the page is wider than the window; 0 when nothing scrolls sideways (TP-SRS-131). */
  async horizontalOverflow() {
    return this.page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  }

  /** The text of everything the browser received, for checking that a secret never reached it. */
  async receivedText() {
    const bodies = await Promise.all(this.browserResponses.map((response) => response.text().catch(() => "")));
    const headers = this.browserResponses.map((response) => JSON.stringify(response.headers()));
    return [...bodies, ...headers].join("\n");
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

  /** A collapsible section's summary, such as "Sources (2)", found by its first word. */
  section(name: string) {
    return this.page.locator("summary").filter({ hasText: new RegExp(`^${name}\\b`) });
  }

  async waitForPlan() {
    await this.page.locator('[role="status"]:not([data-state="running"])').waitFor();
  }
}

/** Press Tab until the element with this id has focus; date fields take several Tabs to leave. */
export async function tabTo(page: Page, id: string) {
  for (let presses = 0; presses < 8; presses++) {
    await page.keyboard.press("Tab");
    if (await page.evaluate((wanted) => document.activeElement?.id === wanted, id)) return;
  }
  throw new Error(`Tab never reached #${id}`);
}

/** Every file the built app serves as a static asset: scripts, styles, and fonts. */
export function staticAssetText(): string {
  const root = path.join(process.cwd(), ".next", "static");
  const files = fs.readdirSync(root, { recursive: true, withFileTypes: true }).filter((entry) => entry.isFile());
  return files.map((entry) => fs.readFileSync(path.join(entry.parentPath, entry.name), "utf8")).join("\n");
}

export const test = base.extend<{ host: FakeHost; app: App }>({
  // Automatic, so every test starts with a reset Host, even one that never configures it.
  host: [
    async ({}, use) => {
      const host = new FakeHost();
      await host.reset();
      await use(host);
    },
    { auto: true },
  ],
  app: async ({ page }, use) => {
    await use(new App(page));
  },
});

export const { Given, When, Then } = createBdd(test);
