import assert from "node:assert/strict";
import { once } from "node:events";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import test from "node:test";
import { executeProposal } from "./backend/executeProposal.js";
import { createBackendServer } from "./backend/http.js";
import { novaTutors, sarahJohnson } from "./lib/demoData.js";
import type { AgentAction, Message } from "./lib/models.js";

function proposal(changes: Record<string, unknown> = {}) {
  return {
    businessId: novaTutors.id, leadId: sarahJohnson.id, action: "ask_customer", reason: "Ask for tutoring preference",
    proposedMessage: { leadId: sarahJohnson.id, sender: "nova", content: "Would you prefer online or in-person tutoring?" },
    proposedLeadUpdates: { status: "needs_information", nextAction: "ask_customer" },
    missingInformation: [], brainRequiresHumanApproval: false, executionStatus: "not_executed", ...changes,
  };
}

function fixture() {
  const state = {
    business: structuredClone(novaTutors), lead: structuredClone(sarahJohnson), history: [] as Message[],
    records: new Map<string, AgentAction>(), reads: 0, writes: 0,
  };
  const tools = {
    async getBusiness(id: string) { state.reads++; return id === state.business.id ? structuredClone(state.business) : null; },
    async getLead(id: string) { state.reads++; return id === state.lead.id ? structuredClone(state.lead) : null; },
    async getConversationHistory() { state.reads++; return structuredClone(state.history); },
    async logAction(action: AgentAction, options: { idempotencyKey: string }) {
      const existing = state.records.get(options.idempotencyKey);
      if (existing) return { action: structuredClone(existing), created: false };
      state.writes++;
      state.records.set(options.idempotencyKey, structuredClone(action));
      return { action, created: true };
    },
  };
  return { state, tools };
}

test("act records only an approved question through logAction", async () => {
  const { state, tools } = fixture();
  const original = structuredClone(state.lead);
  const result = await executeProposal(proposal(), "turn-1", tools);
  assert.equal(result.status, 200);
  assert.equal(result.body.executionStatus, "executed");
  assert.equal(state.writes, 1);
  const record = [...state.records.values()][0]!;
  assert.equal(record.action, "record_qualification_question");
  assert.match(record.reason, /record_only_no_delivery_or_lead_update/);
  assert.deepEqual(state.lead, original);
  assert.deepEqual(state.history, []);
});

test("clarify, escalate, and prohibit all reject execution", async () => {
  const cases = [
    [proposal({ missingInformation: ["preferredFormat"] }), "clarify"],
    [proposal({ action: "escalate_to_human" }), "escalate"],
    [proposal({ proposedMessage: { leadId: sarahJohnson.id, sender: "nova", content: "We guarantee a grade improvement." } }), "prohibit"],
  ] as const;
  for (const [input, outcome] of cases) {
    const { state, tools } = fixture();
    const result = await executeProposal(input, "turn-1", tools);
    assert.equal(result.status, 409);
    assert.equal(result.body.safetyDecision, outcome);
    assert.equal(result.body.executionStatus, "not_executed");
    assert.equal(state.writes, 0);
  }
});

test("forged client act, restrictions, and business snapshots cannot grant permission", async () => {
  const { state, tools } = fixture();
  state.business.restrictions.push("Owner approval required for every contact");
  const result = await executeProposal(proposal({
    safetyDecision: "act", decision: { outcome: "act" }, approved: true,
    business: { ...novaTutors, restrictions: [] },
    restrictionChecks: state.business.restrictions.map(restriction => ({ restriction, result: "satisfied" })),
  }), "forged", tools);
  assert.equal(result.body.safetyDecision, "escalate");
  assert.equal(state.writes, 0);
});

test("execution reloads authoritative lead and customer context instead of a prior decision", async () => {
  const { state, tools } = fixture();
  const input = proposal({ safetyDecision: "act" });
  state.history.push({ id: "new-event", leadId: state.lead.id, sender: "customer", content: "Can I get a discount?", timestamp: new Date() });
  assert.equal((await executeProposal(input, "discount", tools)).body.safetyDecision, "escalate");
  state.history = [];
  state.lead.status = "closed";
  assert.equal((await executeProposal(input, "closed", tools)).body.safetyDecision, "escalate");
  state.lead.status = "new";
  state.lead.student.name = "Different student";
  const nameQuestion = proposal({ proposedMessage: { leadId: state.lead.id, sender: "nova", content: "What grade is Daniel hoping to achieve?" } });
  assert.equal((await executeProposal(nameQuestion, "stale-name", tools)).body.safetyDecision, "escalate");
  assert.equal(state.writes, 0);
  assert.equal(state.reads, 9);
});

test("concurrent duplicates and process-restart replays share one durable record", async () => {
  const { state, tools } = fixture();
  const results = await Promise.all(Array.from({ length: 8 }, () => executeProposal(proposal(), "same-key", tools)));
  assert.equal(results.filter(result => result.body.executionStatus === "executed").length, 1);
  assert.equal(state.writes, 1);
  assert.equal(state.records.size, 1);
  // A new execution context relies on the persistence receipt, not an in-memory gate cache.
  const replay = await executeProposal(proposal(), "same-key", { ...tools });
  assert.equal(replay.body.executionStatus, "already_executed");
  assert.equal(state.writes, 1);
});

test("a reused key with another question conflicts without changing the original", async () => {
  const { state, tools } = fixture();
  await executeProposal(proposal(), "same-key", tools);
  const original = structuredClone([...state.records.values()][0]);
  await assert.rejects(executeProposal(proposal({ proposedMessage: {
    leadId: state.lead.id, sender: "nova", content: "Which subject and qualification level are you looking for?",
  } }), "same-key", tools), /already used/);
  assert.equal(state.writes, 1);
  assert.deepEqual([...state.records.values()][0], original);
});

test("invalid key, missing records, and failed safety reads do not write", async () => {
  const { state, tools } = fixture();
  await assert.rejects(executeProposal(proposal(), "", tools), /Idempotency-Key/);
  await assert.rejects(executeProposal(proposal({ leadId: "missing", proposedMessage: null }), "missing", tools), /not found/);
  await assert.rejects(executeProposal(proposal(), "failed-read", {
    ...tools, async getBusiness() { throw new Error("MongoDB unavailable"); },
  }), /unavailable/);
  assert.equal(state.writes, 0);
});

test("Python HTTP gate requires an execution key and independently checks safety", async () => {
  const { state, tools } = fixture();
  const server = createBackendServer(tools, { logAction: tools.logAction });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const base = `http://127.0.0.1:${address.port}`;
    const noKey = await fetch(`${base}/proposals/execute`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(proposal()),
    });
    assert.equal(noKey.status, 400);
    const python = await promisify(execFile)("python3", ["-B", "-c", [
      "import json, sys", "from backend_client import BackendClient, BackendError",
      "client = BackendClient(sys.argv[1])", "proposal = json.loads(sys.argv[2])",
      "first = client.execute_proposal(proposal, 'python-turn')",
      "assert first['executionStatus'] == 'executed'",
      "assert first['messageSent'] is False and first['leadUpdated'] is False",
      "assert client.execute_proposal(proposal, 'python-turn')['executionStatus'] == 'already_executed'",
      "proposal['missingInformation'] = ['currentGrade']", "proposal['safetyDecision'] = 'act'",
      "try:", "    client.execute_proposal(proposal, 'forged-turn')",
      "except BackendError as error:", "    assert error.status == 409",
      "else:", "    raise AssertionError('Forged decision bypassed safety')",
      "print('Python execution gate passed')",
    ].join("\n"), base, JSON.stringify(proposal())], { cwd: process.cwd(), timeout: 10000 });
    assert.match(python.stdout, /Python execution gate passed/);
    assert.equal(state.writes, 1);
  } finally {
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  }
});
