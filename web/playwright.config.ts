import { defineConfig, devices } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

// Copies of the built app with different settings: with a key, without one, and with the
// sentinel key that the key-exposure checks look for.
export const APP_WITH_KEY = "http://127.0.0.1:3100";
export const APP_WITHOUT_KEY = "http://127.0.0.1:3101";
export const APP_WITH_SENTINEL_KEY = "http://127.0.0.1:3102";
export const FAKE_HOST = "http://127.0.0.1:8790";
export const TEST_HOST_API_KEY = "test-key-123";
export const SENTINEL_HOST_API_KEY = "sentinel-9f2c";

const bddDir = defineBddConfig({
  // The feature files live with the Python ones, in the repository's features/ folder.
  featuresRoot: "../features",
  features: ["../features/web/*.feature"],
  steps: ["tests/bdd/steps/*.ts"],
});

// The planning service "does not answer within 180 seconds" is shortened to this, so the
// scenario takes seconds; the 180-second default is checked by the unit tests.
const appEnv = { HOST_SERVICE_URL: FAKE_HOST, HOST_TIMEOUT_SECONDS: "8", NEXT_TELEMETRY_DISABLED: "1" };

function app(port: number, key: string) {
  return {
    command: `npx next start -p ${port} -H 127.0.0.1`,
    url: `http://127.0.0.1:${port}`,
    env: { ...appEnv, HOST_API_KEY: key },
    reuseExistingServer: false,
  };
}

const chrome = { ...devices["Desktop Chrome"] };

export default defineConfig({
  // One fake Host is shared by every test, so tests run one at a time.
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
  projects: [
    { name: "bdd", testDir: bddDir, use: chrome },
    { name: "e2e", testDir: "tests/e2e", use: chrome },
  ],
  webServer: [
    {
      command: "node tests/bdd/fake-host.ts",
      url: `${FAKE_HOST}/__control/health`,
      reuseExistingServer: false,
    },
    app(3100, TEST_HOST_API_KEY),
    app(3101, ""),
    app(3102, SENTINEL_HOST_API_KEY),
  ],
});
