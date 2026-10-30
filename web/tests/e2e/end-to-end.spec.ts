// End-to-end checks of the built app in a browser, against the fake Host (TDD plan, iteration 13).
import AxeBuilder from "@axe-core/playwright";
import { expect } from "@playwright/test";

import { APP_WITH_SENTINEL_KEY, FAKE_HOST, SENTINEL_HOST_API_KEY } from "../../playwright.config";
import { staticAssetText, tabTo, test } from "../bdd/steps/fixtures";
import { UNAVAILABLE_MESSAGE } from "../../lib/messages";

test.describe("end to end", () => {
  // E2E-01 (TP-SRS-042)
  for (const answer of ["plan", 401, 500] as const) {
    test(`key never reaches the browser (Host answers ${answer})`, async ({ app, host, page }) => {
      if (answer === "plan") await host.answerWithPlan();
      else await host.answerWithStatus(answer);
      app.baseURL = APP_WITH_SENTINEL_KEY;
      await app.open();
      await app.fillValidTrip();
      await app.submitButton().click();
      await app.waitForPlan();

      expect((await host.requests())[0].headers["x-api-key"]).toBe(SENTINEL_HOST_API_KEY);
      expect(await page.content()).not.toContain(SENTINEL_HOST_API_KEY);
      expect(await app.receivedText()).not.toContain(SENTINEL_HOST_API_KEY);
      expect(staticAssetText()).not.toContain(SENTINEL_HOST_API_KEY);
    });
  }

  // E2E-02 (TP-SRS-040)
  test("browser never calls the Host", async ({ app }) => {
    await app.open();
    await app.fillValidTrip();
    await app.submitButton().click();
    await app.waitForPlan();
    expect(app.browserRequests.some((url) => url.endsWith("/api/plan"))).toBe(true);
    expect(app.browserRequests.filter((url) => url.startsWith(FAKE_HOST))).toEqual([]);
  });

  // E2E-03 (TP-SRS-130)
  test("form is accessible and keyboard operable", async ({ app, page }) => {
    await app.open();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);

    await page.locator("body").focus();
    for (const id of ["origin", "destination", "startDate", "endDate", "budget", "travellers"]) {
      await tabTo(page, id);
    }

    await app.fillValidTrip();
    await page.getByLabel("Travellers").focus();
    await page.keyboard.press("Tab");
    await expect(app.submitButton()).toBeFocused();
    await page.keyboard.press("Enter");
    await app.waitForPlan();
    await app.section("Sources").click();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  });

  // E2E-03: the failure state is accessible too.
  test("failure message is accessible", async ({ app, host, page }) => {
    await host.answerWithStatus(500);
    await app.open();
    await app.fillValidTrip();
    await app.submitButton().click();
    await expect(page.getByText(UNAVAILABLE_MESSAGE)).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  });

  // E2E-07 (TP-SRS-130): the dark palette is accessible too, with results, warnings, and sources shown.
  test("accessible in dark mode", async ({ app, host, page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await host.answerWithPlan({
      flights: [],
      errors: [{ part: "flights", message: "Service is temporarily unavailable." }],
    });
    await app.open();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await app.fillValidTrip();
    await app.submitButton().click();
    await app.waitForPlan();
    await app.section("Sources").click();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  });

  // E2E-04 (TP-SRS-131)
  for (const width of [360, 768, 1280]) {
    test(`no horizontal scrolling at ${width} pixels`, async ({ app, host, page }) => {
      await page.setViewportSize({ width, height: 800 });
      await host.answerWithPlan({
        errors: [{ part: "stay", message: "Stay planner is temporarily unavailable." }],
        stay: [],
      });
      await app.open();
      expect(await app.horizontalOverflow()).toBe(0);
      await app.fillValidTrip();
      await app.submitButton().click();
      await app.waitForPlan();
      await app.section("Sources").click();
      expect(await app.horizontalOverflow()).toBe(0);
    });
  }

  // E2E-05 (TP-SRS-133)
  test("results appear without a full reload", async ({ app, page }) => {
    let navigations = 0;
    await app.open();
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame()) navigations++;
    });
    await app.fillValidTrip();
    await app.submitButton().click();
    await expect(page.getByRole("table", { name: "Flights" })).toBeVisible();
    expect(await app.wasReloaded()).toBe(false);
    expect(navigations).toBe(0);
  });

  // E2E-06 (TP-SRS-021, TP-SRS-031, TP-SRS-032)
  test("partial plan end to end", async ({ app, host, page }) => {
    await host.answerWithPlan({
      flights: [],
      errors: [{ part: "flights", message: "Service is temporarily unavailable." }],
    });
    await app.open();
    await app.fillValidTrip();
    await app.submitButton().click();
    await app.waitForPlan();
    await expect(app.progress()).toHaveAttribute("data-state", "partial");
    await expect(page.locator("main").getByRole("alert")).toHaveText("Flights: Service is temporarily unavailable.");
    await expect(page.getByRole("table", { name: "Accommodation" })).toBeVisible();
    await app.section("Sources").click();
    await expect(page.getByRole("link", { name: "Tokyo" })).toHaveAttribute("href", "https://en.wikivoyage.org/wiki/Tokyo");
  });
});
