// Steps for usability, page reloads, and keeping the Host key out of the browser.
import AxeBuilder from "@axe-core/playwright";
import { expect } from "@playwright/test";

import { APP_WITH_SENTINEL_KEY, SENTINEL_HOST_API_KEY } from "../../../playwright.config";
import { Given, Then, When, staticAssetText, tabTo } from "./fixtures";

// axe rules about form fields that have no label.
const LABEL_RULES = ["label", "label-title-only", "label-content-name-mismatch", "select-name"];

Then("an accessibility check finds no form fields without a label", async ({ page }) => {
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter((v) => LABEL_RULES.includes(v.id))).toEqual([]);
});

Then("I can reach every form field and the submit button with the Tab key", async ({ app, page }) => {
  await page.locator("body").focus();
  for (const id of ["origin", "destination", "startDate", "endDate", "budget", "travellers"]) {
    await tabTo(page, id);
  }
  await page.keyboard.press("Tab");
  await expect(app.submitButton()).toBeFocused();
});

Given("my screen is {int} pixels wide", async ({ page }, width: number) => {
  await page.setViewportSize({ width, height: 800 });
});

When("I open the travel planner and plan a valid trip", async ({ app, host }) => {
  // Long unbroken text is what usually pushes a narrow page wider than the screen.
  await host.answerWithPlan({
    activities: [
      {
        name: "Ryōgoku Kokugikan sumo tournament day pass",
        description: "https://en.wikivoyage.org/wiki/Tokyo/Ryogoku#Sumo_wrestling_tournaments_and_stables",
        price: 120,
        currency: "USD",
        notes: "Tickets_sell_out_quickly_so_buy_them_early_from_the_official_vendor",
      },
    ],
  });
  await app.open();
  app.overflowBefore = await app.horizontalOverflow();
  await app.fillValidTrip();
  await app.submitButton().click();
  await app.waitForPlan();
});

Then("the page has no horizontal scrolling before or after the results appear", async ({ app, page }) => {
  await expect(page.getByRole("region", { name: "Results" })).toBeVisible();
  expect(app.overflowBefore).toBe(0);
  expect(await app.horizontalOverflow()).toBe(0);
});

Then("the page was not reloaded", async ({ app }) => {
  expect(await app.wasReloaded()).toBe(false);
});

Given(
  "the web application was built and started with HOST_API_KEY set to {string}",
  async ({ app }, key: string) => {
    expect(key).toBe(SENTINEL_HOST_API_KEY);
    app.baseURL = APP_WITH_SENTINEL_KEY;
  },
);

Given("the planning service returns a complete plan", async ({ host }) => {
  await host.answerWithPlan({ errors: [] });
});

When("I open the travel planner and submit a valid trip", async ({ app }) => {
  await app.open();
  await app.fillValidTrip();
  await app.submitButton().click();
  await app.waitForPlan();
});

Then("{string} appears in no page, script, or response my browser receives", async ({ app, host }, key: string) => {
  // The key did reach the Host, so its absence in the browser is not an accident of setup.
  const [received] = await host.requests();
  expect(received.headers["x-api-key"]).toBe(key);
  expect(app.browserResponses.length).toBeGreaterThan(1);
  expect(await app.receivedText()).not.toContain(key);
  expect(staticAssetText()).not.toContain(key);
});
