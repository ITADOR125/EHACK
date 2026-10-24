import assert from "node:assert/strict";
import test from "node:test";
import { novaTutors, sarahJohnson, jamesCarter } from "./lib/demoData.js";
import { checkSafety, decisionToAgentAction } from "./lib/safety.js";
import type { SafetyRequest } from "./lib/safety.js";

function request(updates: Partial<SafetyRequest> = {}): SafetyRequest {
  return {
    action: "send_outreach", issue: "Contact Sarah about GCSE Maths support",
    context: ["Sarah is seeking tutoring for Daniel in Year 11."],
    restrictionChecks: novaTutors.restrictions.map(restriction => ({ restriction, result: "satisfied" })),
    ...updates,
  };
}

test("routine outreach acts without owner approval despite incomplete lead qualification", () => {
  assert.equal(checkSafety(novaTutors, sarahJohnson, request()).outcome, "act");
});

test("missing configured qualification fields result in clarify", () => {
  const result = checkSafety(novaTutors, sarahJohnson, request({ action: "qualify_lead" }));
  assert.equal(result.outcome, "clarify");
  if (result.outcome !== "clarify") throw new Error("Expected clarify");
  assert.deepEqual(result.missingInformation, ["currentGrade", "targetGrade", "examBoard", "tier"]);
  assert.match(result.question, /currentGrade/);
});

test("safe customer ambiguity is clarified instead of escalated", () => {
  const result = checkSafety(novaTutors, sarahJohnson, request({
    ambiguous: true, safeClarificationQuestion: "Do you mean GCSE or university Maths?",
  }));
  assert.equal(result.outcome, "clarify");
});

test("discount escalation includes useful context and a recommended action", () => {
  const input = request({ discountOrPriceException: true, issue: "Customer requests £20/hour", context: ["Configured price is £30/hour."] });
  const result = checkSafety(novaTutors, sarahJohnson, input);
  assert.equal(result.outcome, "escalate");
  if (result.outcome !== "escalate") throw new Error("Expected escalation");
  assert.equal(result.escalation.leadId, sarahJohnson.id);
  assert.equal(result.escalation.issue, input.issue);
  assert.ok(result.escalation.reason);
  assert.ok(result.escalation.context.includes("Configured price is £30/hour."));
  assert.match(result.escalation.recommendedAction, /owner/i);
});

test("discount escalation takes precedence over missing customer information", () => {
  assert.equal(checkSafety(novaTutors, sarahJohnson, request({
    discountOrPriceException: true, missingInformation: ["targetGrade"],
  })).outcome, "escalate");
});

test("grade guarantees are prohibited by Nova Tutors restrictions", () => {
  const result = checkSafety(novaTutors, sarahJohnson, request({ guaranteesOutcome: true }));
  assert.equal(result.outcome, "prohibit");
  assert.match(result.reason, /restrictions.*guaranteeing/i);
});

test("arbitrary business restrictions are enforced through explicit review", () => {
  const business = { ...novaTutors, restrictions: ["Do not contact customers on Sundays"] };
  assert.equal(checkSafety(business, sarahJohnson, request({ restrictionChecks: [
    { restriction: business.restrictions[0]!, result: "violated" },
  ] })).outcome, "prohibit");
  assert.equal(checkSafety(business, sarahJohnson, request({ restrictionChecks: [] })).outcome, "escalate");
});

test("unknown FAQ facts escalate and no invented answer is returned", () => {
  const result = checkSafety(novaTutors, sarahJohnson, request({
    action: "answer_faq", claims: [{ fact: "availability", value: "Tomorrow at 4pm" }],
  }));
  assert.equal(result.outcome, "escalate");
  assert.equal("answer" in result, false);
});

test("known service pricing supports an autonomous FAQ answer", () => {
  assert.equal(checkSafety(novaTutors, sarahJohnson, request({
    action: "answer_faq", claims: [{ fact: "price:GCSE Maths Tutoring", value: "30/hour" }],
  })).outcome, "act");
});

test("supplemental facts cannot override core business pricing", () => {
  assert.equal(checkSafety(novaTutors, sarahJohnson, request({
    action: "answer_faq", claims: [{ fact: "price:GCSE Maths Tutoring", value: "20/hour" }],
  }), { facts: { "price:GCSE Maths Tutoring": "20/hour" } }).outcome, "escalate");
});

test("FAQ without supporting facts escalates", () => {
  assert.equal(checkSafety(novaTutors, sarahJohnson, request({ action: "answer_faq" })).outcome, "escalate");
});

test("known unsupported service can be explained autonomously", () => {
  const input = request({ action: "explain_unsupported_service", requestedService: "University Mathematics" });
  assert.equal(checkSafety(novaTutors, jamesCarter, input, {
    unsupportedServices: ["University Mathematics"],
  }).outcome, "act");
  // Absence from the service list alone is not proof of unsupported coverage.
  assert.equal(checkSafety(novaTutors, jamesCarter, input).outcome, "escalate");
});

test("qualify and reject require matching configured rules", () => {
  const lead = { ...sarahJohnson, currentGrade: 4, targetGrade: 6, examBoard: "AQA", tier: "Higher" };
  const input = request({ action: "qualify_lead" });
  assert.equal(checkSafety(novaTutors, lead, input).outcome, "escalate");
  assert.equal(checkSafety(novaTutors, lead, input, { decisionRules: [
    { id: "gcse-maths-year11", action: "qualify_lead", when: { subject: "Maths", year: "Year 11" } },
  ] }).outcome, "act");
  assert.equal(checkSafety(novaTutors, jamesCarter, request({ action: "reject_lead" }), { decisionRules: [
    { id: "university-not-offered", action: "reject_lead", when: { subject: "University Mathematics" } },
  ] }).outcome, "act");
});

test("unconfigured and disabled actions escalate", () => {
  assert.equal(checkSafety(novaTutors, sarahJohnson, request({ action: "sign_contract" })).outcome, "escalate");
  assert.equal(checkSafety(novaTutors, sarahJohnson, request(), { disabledActions: ["send_outreach"] }).outcome, "escalate");
});

test("fabrication, false completion claims and unauthorised commitments are prohibited", () => {
  for (const flag of ["fabricatesInformation", "claimsUnperformedAction", "unauthorisedCommitment"] as const) {
    assert.equal(checkSafety(novaTutors, sarahJohnson, request({ [flag]: true })).outcome, "prohibit");
  }
});

test("missing business facts, conflicts, judgement and exceptions escalate", () => {
  for (const flag of ["missingBusinessInformation", "unresolvedConflict", "potentiallyMisleading", "requiresOwnerJudgement", "businessRuleException"] as const) {
    assert.equal(checkSafety(novaTutors, sarahJohnson, request({ [flag]: true })).outcome, "escalate");
  }
});

test("decisions produce AgentAction-compatible audit records without claiming execution", () => {
  for (const input of [request(), request({ action: "qualify_lead" }), request({ discountOrPriceException: true }), request({ guaranteesOutcome: true })]) {
    const decision = checkSafety(novaTutors, sarahJohnson, input);
    const audit = decisionToAgentAction(sarahJohnson.id, input, decision);
    assert.equal(audit.leadId, sarahJohnson.id);
    assert.equal(audit.action, `safety:${input.action}:${decision.outcome}`);
    assert.equal(audit.status, "completed");
    assert.deepEqual(JSON.parse(audit.reason).decision, decision);
    assert.ok(audit.timestamp instanceof Date);
  }
});
