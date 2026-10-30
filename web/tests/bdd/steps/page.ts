// Steps a traveller takes on the page, and what they see.
import { type Page, expect } from "@playwright/test";

import { PART_LABELS, UNAVAILABLE_MESSAGE } from "../../../lib/messages";
import type { Part } from "../../../lib/types";
import { TEST_HOST_API_KEY } from "../../../playwright.config";
import { Given, Then, When, tabTo } from "./fixtures";

// Steps match whatever keyword they are written with (Given, When, or Then).
Given("I open the travel planner", async ({ app }) => {
  await app.open();
});

Given("I have filled in the form with a valid trip", async ({ app }) => {
  await app.fillValidTrip();
});

When("I submit a valid trip", async ({ app, page }) => {
  if (!page.url().startsWith(app.baseURL)) await app.open();
  await app.fillValidTrip();
  await app.submitButton().click();
  await app.waitForPlan();
});

When("I clear the {string} field", async ({ page }, label: string) => {
  await page.getByLabel(label).fill("");
});

When("I submit the form", async ({ app }) => {
  await app.submitButton().click();
});

When("I set the start date to {string}", async ({ page }, date: string) => {
  await page.getByLabel("Start date").fill(date);
});

When("I set the end date to {string}", async ({ page }, date: string) => {
  await page.getByLabel("End date").fill(date);
});

When("I enter {string} in the {string} field", async ({ page }, value: string, label: string) => {
  await page.getByLabel(label).fill(value);
});

When("the plan arrives", async ({ app }) => {
  await app.waitForPlan();
});

When("{int} seconds pass", async ({ page }, seconds: number) => {
  await page.waitForTimeout(seconds * 1000);
});

// Next.js adds a route announcer with role="alert" to every page, so alerts are looked for in main.
function formProblems(page: Page) {
  return page.locator("main form").getByRole("alert");
}

When("I fill in and submit the form using only the keyboard", async ({ app, page }) => {
  await app.open();
  const keyboard = page.keyboard;
  await page.locator("body").focus();
  await tabTo(page, "origin");
  await keyboard.type("Manila");
  await tabTo(page, "destination");
  await keyboard.type("Tokyo");
  // Browsers order a date field's parts by the system's regional settings. Dates whose day and
  // month are the same number type the same way in day-month and month-day order.
  await tabTo(page, "startDate");
  await keyboard.type("12122026");
  await tabTo(page, "endDate");
  await keyboard.type("01012027");
  await expect(page.getByLabel("Start date")).toHaveValue("2026-12-12");
  await expect(page.getByLabel("End date")).toHaveValue("2027-01-01");
  await tabTo(page, "budget");
  await tabTo(page, "travellers");
  await keyboard.press("Tab");
  await expect(app.submitButton()).toBeFocused();
  await keyboard.press("Enter");
  await app.waitForPlan();
});

When("I expand the {string} section", async ({ app }, name: string) => {
  await app.section(name).click();
});

Then("I see a form with these labelled fields:", async ({ page }, table) => {
  for (const { label } of table.hashes() as { label: string }[]) {
    await expect(page.getByText(label, { exact: true })).toBeVisible();
    await expect(page.getByLabel(label)).toBeVisible();
  }
});

Then("the {string} field shows {string}", async ({ page }, label: string, value: string) => {
  await expect(page.getByLabel(label)).toHaveValue(value);
});

Then("the {string} field is {word}", async ({ page }, label: string, validity: string) => {
  expect(["valid", "invalid"]).toContain(validity);
  await expect(page.getByLabel(label)).toHaveAttribute("aria-invalid", String(validity === "invalid"));
});

Then("I see a warning that the {word} is required", async ({ page }, field: string) => {
  await expect(formProblems(page)).toContainText(`${field} is required.`);
});

Then("I see a warning that the end date must be after the start date", async ({ page }) => {
  await expect(formProblems(page)).toContainText("The end date must be after the start date.");
});

Then("the submit button is disabled", async ({ app }) => {
  await expect(app.submitButton()).toBeDisabled();
});

Then("the submit button is enabled", async ({ app }) => {
  await expect(app.submitButton()).toBeEnabled();
});

Then("I see the trip results", async ({ page }) => {
  await expect(page.getByRole("table", { name: "Flights" })).toBeVisible();
});

Then("a progress indicator is shown at the top of the results area", async ({ page }) => {
  const first = page.getByRole("region", { name: "Results" }).locator("> :first-child");
  await expect(first).toHaveAttribute("role", "status");
});

Then("it shows an elapsed time of {int} seconds", async ({ app }, seconds: number) => {
  await expect(app.progress()).toContainText(new RegExp(`\\b${seconds} s\\b`));
});

Then("the progress indicator shows the plan is complete", async ({ app }) => {
  await expect(app.progress()).toHaveAttribute("data-state", "complete");
});

Then("the progress indicator shows the plan is partial", async ({ app }) => {
  await expect(app.progress()).toHaveAttribute("data-state", "partial");
});

Then("the progress indicator shows the plan failed", async ({ app }) => {
  await expect(app.progress()).toHaveAttribute("data-state", "failed");
});

Then("I see the message {string}", async ({ page }, message: string) => {
  expect(message).toBe(UNAVAILABLE_MESSAGE);
  await expect(page.getByText(message, { exact: true })).toBeVisible();
});

Then("the message mentions no provider name, stack trace, or key", async ({ page }) => {
  const text = await page.locator("main").innerText();
  for (const word of ["Ollama", "OpenAI", "Traceback", "Error:", "status 5", "status 4", TEST_HOST_API_KEY]) {
    expect(text).not.toContain(word);
  }
});

Then(/^I see an? "([^"]+)" table with (\d+) rows$/, async ({ page }, name: string, count: string) => {
  const table = page.getByRole("table", { name });
  await expect(table.locator("tbody tr")).toHaveCount(Number(count));
});

Then("I see a warning naming {string} with {string}", async ({ page }, part: string, message: string) => {
  await expect(page.locator("main").getByRole("alert").filter({ hasText: `${PART_LABELS[part as Part]}: ${message}` })).toBeVisible();
});

Then("I see a collapsed {string} section", async ({ app, page }, name: string) => {
  const details = page.locator("details", { has: app.section(name) });
  await expect(details).toBeVisible();
  await expect(details).not.toHaveAttribute("open");
});

Then("I do not see a {string} section", async ({ app, page }, name: string) => {
  await expect(page.getByRole("table", { name: "Flights" })).toBeVisible();
  await expect(app.section(name)).toHaveCount(0);
});

Then("the {string} section is headed with {int} sources", async ({ app }, name: string, count: number) => {
  await expect(app.section(name)).toHaveText(`${name} (${count})`);
});

Then("I see the caption {string}", async ({ page }, caption: string) => {
  await expect(page.getByText(caption, { exact: true })).toBeVisible();
});

Then("the {string} field shows the placeholder {string}", async ({ page }, label: string, placeholder: string) => {
  await expect(page.getByLabel(label)).toHaveAttribute("placeholder", placeholder);
});

Then("I see a note that the agents work in parallel and can take one to two minutes", async ({ page }) => {
  await expect(page.getByRole("region", { name: "Results" })).toContainText(
    "The flight, stay, and activities agents are working in parallel. With a local model this usually takes one to two minutes.",
  );
});

Then("I see a hint to adjust the travel dates or budget", async ({ page }) => {
  await expect(page.getByText("No trip options were returned. Try adjusting the travel dates or budget.")).toBeVisible();
});

Then(
  "I see a link {string} to {string} with license {string}",
  async ({ page }, title: string, url: string, license: string) => {
    const link = page.getByRole("link", { name: title, exact: true });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", url);
    await expect(page.locator("li", { has: link })).toContainText(license);
  },
);

Then("I see a notice that suggestions are illustrative and not live or bookable", async ({ page }) => {
  const notice = page.getByText(/illustrative/);
  await expect(notice).toBeVisible();
  await expect(notice).toContainText("not live");
  await expect(notice).toContainText("not bookable");
});
