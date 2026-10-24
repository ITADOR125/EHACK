import assert from "node:assert/strict";
import { once } from "node:events";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import test from "node:test";
import { createBackendServer } from "./backend/http.js";
import { novaTutors, sarahJohnson } from "./lib/demoData.js";

test("HTTP read routes, errors, and method boundaries", async () => {
  const calls: string[] = [];
  const server = createBackendServer({
    async getBusiness(id) {
      calls.push(`business:${id}`);
      return id === novaTutors.id ? novaTutors : null;
    },
    async getLead(id) {
      calls.push(`lead:${id}`);
      if (id === "database-error") throw new Error("private connection detail");
      return id === sarahJohnson.id ? sarahJohnson : null;
    },
    async getConversationHistory(id) {
      calls.push(`messages:${id}`);
      return [];
    },
    async getAgentActions(id) {
      calls.push(`actions:${id}`);
      return [{ id: "recorded-question", leadId: id, action: "record_qualification_question",
        reason: "A previously recorded question", status: "completed", timestamp: new Date("2026-01-01T10:00:00Z") }];
    },
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const base = `http://127.0.0.1:${address.port}`;
    assert.deepEqual(await (await fetch(`${base}/health`)).json(), { status: "ok" });
    assert.equal(calls.length, 0);
    assert.deepEqual(await (await fetch(`${base}/businesses/nova-tutors`)).json(), novaTutors);
    assert.deepEqual(await (await fetch(`${base}/leads/sarah-johnson`)).json(), sarahJohnson);
    assert.deepEqual(await (await fetch(`${base}/leads/sarah-johnson/messages`)).json(), []);
    assert.ok(calls.includes("messages:sarah-johnson"));
    const actions = await (await fetch(`${base}/leads/sarah-johnson/actions`)).json() as { id: string }[];
    assert.equal(actions[0]?.id, "recorded-question");
    // Exercise the real Python client against HTTP independently of Atlas access.
    // The separate test_backend_bridge.py checks the live MongoDB path.
    const python = await promisify(execFile)("python3", ["-B", "-c", [
      "import sys",
      "from backend_client import BackendClient, BackendError",
      "client = BackendClient(sys.argv[1])",
      "assert client.health() == {'status': 'ok'}",
      "assert client.get_business('nova-tutors')['name'] == 'Nova Tutors'",
      "assert client.get_lead('sarah-johnson')['name'] == 'Sarah Johnson'",
      "assert client.get_conversation_history('sarah-johnson') == []",
      "assert client.get_agent_actions('sarah-johnson')[0]['id'] == 'recorded-question'",
      "from lead_inspection import load_inspection",
      "assert load_inspection(client, 'sarah-johnson')['actions'][0]['id'] == 'recorded-question'",
      "try:",
      "    client.get_lead('missing')",
      "except BackendError as error:",
      "    assert error.status == 404",
      "else:",
      "    raise AssertionError('Expected HTTP 404')",
      "print('Python HTTP client passed (fixture-backed route test).')",
    ].join("\n"), base], { cwd: process.cwd(), timeout: 10000 });
    assert.match(python.stdout, /Python HTTP client passed/);
    for (const path of ["/businesses/missing", "/leads/missing", "/leads/missing/messages", "/leads/missing/actions", "/unknown"]) {
      assert.equal((await fetch(base + path)).status, 404);
    }
    assert.equal((await fetch(`${base}/leads/%ZZ`)).status, 400);
    const failure = await fetch(`${base}/leads/database-error`);
    assert.equal(failure.status, 503);
    assert.deepEqual(await failure.json(), { error: "Backend data is temporarily unavailable" });
    const before = calls.length;
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      const response = await fetch(`${base}/leads/sarah-johnson`, { method });
      assert.equal(response.status, 405);
      assert.equal(response.headers.get("allow"), "GET");
    }
    assert.equal(calls.length, before);
    assert.equal((await fetch(`${base}/leads/sarah-johnson/actions`, { method: "POST" })).status, 405);
  } finally {
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  }
});
