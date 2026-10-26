// A fake Host for browser tests: answers POST /run the way the scenario tells it to, and records
// every request. Scenarios configure it through /__control. Run with: node tests/bdd/fake-host.ts
import { createServer, type IncomingMessage } from "node:http";

import { plan } from "../fixtures.ts";

export const FAKE_HOST_PORT = 8790;

type Behaviour =
  | { kind: "plan"; plan: unknown; delayMs?: number }
  | { kind: "status"; status: number }
  | { kind: "hang" }
  | { kind: "drop" };

interface Received {
  path: string;
  headers: Record<string, string | string[] | undefined>;
  body: unknown;
}

let behaviour: Behaviour = { kind: "plan", plan: plan() };
let received: Received[] = [];

function readBody(request: IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    let body = "";
    request.on("data", (chunk) => (body += chunk));
    request.on("end", () => resolve(body));
  });
}

function json(response: import("node:http").ServerResponse, status: number, body: unknown) {
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(body));
}

const server = createServer(async (request, response) => {
  const body = await readBody(request);
  const path = request.url ?? "/";

  if (path === "/__control/health") return json(response, 200, { status: "ok" });
  if (path === "/__control/reset") {
    behaviour = { kind: "plan", plan: plan() };
    received = [];
    return json(response, 200, { status: "reset" });
  }
  if (path === "/__control/behaviour") {
    behaviour = JSON.parse(body) as Behaviour;
    return json(response, 200, { status: "set" });
  }
  if (path === "/__control/requests") return json(response, 200, received);

  received.push({ path, headers: request.headers, body: body ? JSON.parse(body) : null });
  switch (behaviour.kind) {
    case "plan": {
      const { plan: answer, delayMs = 0 } = behaviour;
      if (delayMs) await new Promise((resolve) => setTimeout(resolve, delayMs));
      return json(response, 200, answer);
    }
    case "status":
      return json(response, behaviour.status, { detail: "fake failure" });
    case "hang":
      return; // never answers
    case "drop":
      request.socket.destroy(); // as if the Host could not be reached
      return;
  }
});

server.listen(FAKE_HOST_PORT, "127.0.0.1", () => {
  console.log(`Fake Host listening on http://127.0.0.1:${FAKE_HOST_PORT}`);
});
