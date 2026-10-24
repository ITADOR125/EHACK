import assert from "node:assert/strict";
import { once } from "node:events";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import test from "node:test";
import { evaluateProposal, parseProposal } from "./backend/evaluateProposal.js";
import { createBackendServer } from "./backend/http.js";
import { novaTutors, sarahJohnson } from "./lib/demoData.js";

function proposal(overrides: Record<string, unknown> = {}) {
  return parseProposal({
    businessId: novaTutors.id, leadId: sarahJohnson.id, action: "ask_customer",
    reason: "Ask for delivery preference", proposedLeadUpdates: { status: "needs_information", nextAction: "ask_customer" },
    proposedMessage: { leadId: sarahJohnson.id, sender: "nova", content: "Would you prefer online or in-person tutoring?" },
    missingInformation: [], brainRequiresHumanApproval: false,
    executionStatus: "not_executed", ...overrides,
  });
}
function draft(content: string) { return { leadId: sarahJohnson.id, sender: "nova", content }; }

test("routine question is allowed, or clarified when customer information is missing", () => {
  assert.equal(evaluateProposal(proposal(), novaTutors, sarahJohnson, []).safetyDecision, "act");
  const result = evaluateProposal(proposal({ missingInformation: ["preferredFormat"] }), novaTutors, sarahJohnson, []);
  assert.equal(result.safetyDecision, "clarify");
  assert.equal(result.decision.outcome === "clarify" && result.decision.question, "Would you prefer online or in-person tutoring?");
});

test("discount and price exceptions escalate using actual customer history", () => {
  const result = evaluateProposal(proposal(), novaTutors, sarahJohnson, [{
    id: "discount", leadId: sarahJohnson.id, sender: "customer",
    content: "Can I have a discount?", timestamp: new Date(),
  }]);
  assert.equal(result.safetyDecision, "escalate");
  assert.equal(result.escalation?.leadId, sarahJohnson.id);
  assert.match(result.escalation?.recommendedAction ?? "", /owner/);
  assert.equal(evaluateProposal(proposal({ reason: "Customer requests a price exception" }),
    novaTutors, sarahJohnson, []).safetyDecision, "escalate");
});

test("a prohibited grade guarantee is blocked even when framed as a question action", () => {
  const result = evaluateProposal(proposal({ proposedMessage: draft("We guarantee Daniel will improve by two grades.") }),
    novaTutors, sarahJohnson, []);
  assert.equal(result.safetyDecision, "prohibit");
});

test("unknown facts and arbitrary restrictions are never assumed safe", () => {
  assert.equal(evaluateProposal(proposal({ action: "answer_customer", proposedMessage: draft("We have a tutor tomorrow at 6pm."),
    restrictionChecks: novaTutors.restrictions.map(restriction => ({ restriction, result: "satisfied" })),
    claims: [{ fact: "availability", value: "Tomorrow at 6pm" }],
  }), novaTutors, sarahJohnson, []).safetyDecision, "escalate");
  assert.equal(evaluateProposal(proposal(), { ...novaTutors, restrictions: ["No contact on Sundays"] },
    sarahJohnson, []).safetyDecision, "escalate");
});

test("brain escalation and requested human approval cannot be downgraded", () => {
  const result = evaluateProposal(proposal({ action: "escalate_to_human", brainRequiresHumanApproval: false }),
    novaTutors, sarahJohnson, []);
  assert.equal(result.mappedSafetyAction, "recommend_next_action");
  assert.equal(result.safetyDecision, "escalate");
  assert.equal(evaluateProposal(proposal({ brainRequiresHumanApproval: true }), novaTutors,
    sarahJohnson, []).safetyDecision, "escalate");
});

test("action mapping and unverified lead changes stay conservative", () => {
  const expected = {
    ask_customer: "ask_qualification_question", answer_customer: "answer_faq", draft_outreach: "send_outreach",
    close_lead: "reject_lead", recommend_consultation: "recommend_next_action", escalate_to_human: "recommend_next_action",
  };
  for (const [action, mapped] of Object.entries(expected)) {
    assert.equal(evaluateProposal(proposal({ action }), novaTutors, sarahJohnson, []).mappedSafetyAction, mapped);
  }
  for (const changes of [{ currentGrade: 4 }, { status: "qualified" }, { nextAction: "sign_contract" }]) {
    assert.equal(evaluateProposal(proposal({ proposedLeadUpdates: changes }), novaTutors, sarahJohnson, []).safetyDecision, "escalate");
  }
  assert.equal(evaluateProposal(proposal({ action: "sign_contract" }), novaTutors, sarahJohnson, []).safetyDecision, "escalate");
});

test("POST evaluation works from Python and never invokes persistence", async () => {
  const original = structuredClone({ business: novaTutors, lead: sarahJohnson });
  let writes = 0;
  const write = async () => { writes++; throw new Error("Persistence must not be called"); };
  const tools = {
    async getBusiness(id: string) { return id === novaTutors.id ? novaTutors : null; },
    async getLead(id: string) { return id === sarahJohnson.id ? sarahJohnson : null; },
    async getConversationHistory() { return []; },
    updateLead: write, saveMessage: write, logAction: write,
  };
  const server = createBackendServer(tools);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const base = `http://127.0.0.1:${address.port}`;
    const post = (body: unknown) => fetch(`${base}/proposals/evaluate`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const response = await post(proposal());
    assert.equal(response.status, 200);
    const result = await response.json() as { executionStatus: string; safetyDecision: string };
    assert.equal(result.executionStatus, "not_executed");
    assert.equal(result.safetyDecision, "act");
    assert.equal((await post({})).status, 400);
    assert.equal((await post({ ...proposal(), businessId: "missing" })).status, 404);
    assert.equal((await fetch(`${base}/proposals/evaluate`)).status, 405);
    assert.equal((await fetch(`${base}/proposals/evaluate`, { method: "POST", body: "{}" })).status, 415);
    assert.equal((await fetch(`${base}/proposals/evaluate`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{invalid",
    })).status, 400);
    assert.equal((await post({ ...proposal(), reason: "x".repeat(65536) })).status, 413);
    const python = await promisify(execFile)("python3", ["-B", "-c", [
      "import sys",
      "from backend_client import BackendClient",
      "from brain_adapter import propose",
      "client = BackendClient(sys.argv[1])",
      "business = client.get_business('nova-tutors')",
      "lead = client.get_lead('sarah-johnson')",
      "messages = [{'leadId':lead['id'], 'sender':'customer', 'content':'Hello'}]",
      "proposal = propose(business, lead, messages, extraction_override={'facts':{}, 'quotes':{}})",
      "result = client.evaluate_proposal(proposal)",
      "assert result['safetyDecision'] == 'clarify', result",
      "assert result['mappedSafetyAction'] == 'ask_qualification_question'",
      "assert result['executionStatus'] == 'not_executed'",
      "print('Python proposal safety evaluation passed')",
    ].join("\n"), base], { cwd: process.cwd(), timeout: 10000 });
    assert.match(python.stdout, /Python proposal safety evaluation passed/);
    assert.equal(writes, 0);
    assert.deepEqual({ business: novaTutors, lead: sarahJohnson }, original);
  } finally {
    await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  }
});
