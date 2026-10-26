import { defineConfig, devices } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

// Two copies of the built app, so scenarios can run with and without HOST_API_KEY.
export const APP_WITH_KEY = "http://127.0.0.1:3100";
export const APP_WITHOUT_KEY = "http://127.0.0.1:3101";
export const FAKE_HOST = "http://127.0.0.1:8790";
export const TEST_HOST_API_KEY = "test-key-123";

const testDir = defineBddConfig({
  // The feature files live with the Python ones, in the repository's features/ folder.
  featuresRoot: "../features",
  features: [
    "../features/web/trip_form.feature",
    "../features/web/planning_progress.feature",
    "../features/web/results_display.feature",
    "../features/web/host_access.feature",
  ],
  steps: ["tests/bdd/steps/*.ts"],
  // The two scenarios whose steps phase 12 defines (a full page reload and the API key in the
  // built pages) are reported as skipped until then.
  missingSteps: "skip-scenario",
});

// The planning service "does not answer within 180 seconds" is shortened to this, so the
// scenario takes seconds; the 180-second default is checked by the unit tests.
const appEnv = { HOST_SERVICE_URL: FAKE_HOST, HOST_TIMEOUT_SECONDS: "8", NEXT_TELEMETRY_DISABLED: "1" };

export default defineConfig({
  testDir,
  // One fake Host is shared by every scenario, so scenarios run one at a time.
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: APP_WITH_KEY,
    locale: "en-US",
    timezoneId: "UTC",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "node tests/bdd/fake-host.ts",
      url: `${FAKE_HOST}/__control/health`,
      reuseExistingServer: false,
    },
    {
      command: "npx next start -p 3100 -H 127.0.0.1",
      url: APP_WITH_KEY,
      env: { ...appEnv, HOST_API_KEY: TEST_HOST_API_KEY },
      reuseExistingServer: false,
    },
    {
      command: "npx next start -p 3101 -H 127.0.0.1",
      url: APP_WITHOUT_KEY,
      env: { ...appEnv, HOST_API_KEY: "" },
      reuseExistingServer: false,
    },
  ],
});
