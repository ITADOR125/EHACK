import { randomUUID } from "node:crypto";
import type { AgentAction, Business, Lead } from "./models.js";

export const autonomousActions = [
  "analyse_lead", "send_outreach", "ask_qualification_question", "answer_faq",
  "send_follow_up", "save_message", "update_lead_information", "update_lead_status",
  "qualify_lead", "reject_lead", "recommend_next_action", "explain_unsupported_service",
] as const;
export type NovaAction = typeof autonomousActions[number];

export interface SafetyPolicy {
  disabledActions?: NovaAction[];
  // Owner-supplied facts supplement the existing Business model (e.g. FAQs).
  facts?: Record<string, string>;
  unsupportedServices?: string[];
  decisionRules?: {
    id: string;
    action: "qualify_lead" | "reject_lead";
    when: Partial<Lead>;
  }[];
}

export interface SafetyRequest {
  action: string;
  issue: string;
  context: string[];
  restrictionChecks: { restriction: string; result: "satisfied" | "violated" | "unknown" }[];
  claims?: { fact: string; value: string }[];
  requestedService?: string;
  missingInformation?: string[];
  ambiguous?: boolean;
  safeClarificationQuestion?: string;
  discountOrPriceException?: boolean;
  businessRuleException?: boolean;
  requiresOwnerJudgement?: boolean;
  missingBusinessInformation?: boolean;
  unresolvedConflict?: boolean;
  potentiallyMisleading?: boolean;
  fabricatesInformation?: boolean;
  claimsUnperformedAction?: boolean;
  unauthorisedCommitment?: boolean;
  guaranteesOutcome?: boolean;
}

export interface Escalation {
  leadId: string;
  issue: string;
  reason: string;
  context: string[];
  recommendedAction: string;
}

export type SafetyDecision =
  | { outcome: "act"; reason: string }
  | { outcome: "clarify"; reason: string; question: string; missingInformation: string[] }
  | { outcome: "prohibit"; reason: string }
  | { outcome: "escalate"; reason: string; escalation: Escalation };

/** Pure preflight check. Trusted callers must assess the actual proposed action,
 * including every free-text Business restriction; this is not a text classifier.
 * Never execute a proposed action unless the result is `act`.
 */
export function checkSafety(
  business: Business, lead: Lead, request: SafetyRequest, policy: SafetyPolicy = {},
): SafetyDecision {
  const escalate = (reason: string, recommendedAction: string): SafetyDecision => ({
    outcome: "escalate", reason,
    escalation: {
      leadId: lead.id, issue: request.issue, reason,
      context: [`Proposed action: ${request.action}`, ...request.context], recommendedAction,
    },
  });
  const violated = business.restrictions.find(restriction => request.restrictionChecks.some(
    check => check.restriction === restriction && check.result === "violated",
  ));
  if (violated) return { outcome: "prohibit", reason: `Business restriction: ${violated}` };
  if (request.guaranteesOutcome && business.restrictions.some(r => /\bguarantee\b/i.test(r))) {
    return { outcome: "prohibit", reason: "Business restrictions prohibit guaranteeing outcomes." };
  }
  if (request.fabricatesInformation || request.claimsUnperformedAction || request.unauthorisedCommitment) {
    return { outcome: "prohibit", reason: "Fabrication, false completion claims, and unauthorised commitments are prohibited." };
  }
  if (lead.businessId !== business.id) return escalate("Lead belongs to another business.", "Verify the business and lead association.");
  if (!autonomousActions.some(action => action === request.action) ||
      policy.disabledActions?.some(action => action === request.action)) {
    return escalate("Action is outside Nova's permissions.", "Ask the owner to handle the action or explicitly configure permission.");
  }
  if (request.discountOrPriceException || request.businessRuleException || request.requiresOwnerJudgement) {
    return escalate("The request requires a business-owner decision.", "Ask the owner to approve or decline the requested exception before replying with a commitment.");
  }
  const unchecked = business.restrictions.filter(restriction => {
    const checks = request.restrictionChecks.filter(check => check.restriction === restriction);
    return checks.length !== 1 || checks[0]?.result !== "satisfied";
  });
  if (unchecked.length) return escalate(`Restriction compliance is unresolved: ${unchecked.join("; ")}`, "Review the proposed action against these restrictions.");
  if (request.missingBusinessInformation || request.unresolvedConflict || request.potentiallyMisleading) {
    return escalate("Reliable business information or a safe basis for acting is unavailable.", "Obtain verified business information or resolve the conflict with the owner.");
  }

  // Core facts always come from Business and cannot be overridden by supplemental facts.
  const facts: Record<string, string> = {
    ...policy.facts, name: business.name, tone: business.tone,
    ...Object.fromEntries(business.services.flatMap(service => [
      [`service:${service.name}`, service.name],
      [`price:${service.name}`, `${service.price}/${service.priceUnit}`],
    ])),
  };
  if (request.claims?.some(claim => !Object.hasOwn(facts, claim.fact) || facts[claim.fact] !== claim.value)) {
    return escalate("A proposed business claim is unknown or conflicts with verified facts.", "Confirm the fact with the owner; do not include the unsupported claim.");
  }
  if (request.action === "answer_faq" && !request.claims?.length) {
    return escalate("The FAQ answer has no verified supporting business facts.", "Obtain a verified answer from the owner.");
  }
  if (request.action === "explain_unsupported_service") {
    if (!request.requestedService) return {
      outcome: "clarify", reason: "The requested service is unclear.",
      question: "Which service are you looking for?", missingInformation: ["requestedService"],
    };
    if (!policy.unsupportedServices?.includes(request.requestedService)) {
      return escalate("This service is not explicitly configured as unsupported.", "Confirm service coverage with the owner before rejecting the request.");
    }
  }
  const missing = [...(request.missingInformation ?? [])];
  if (request.action === "qualify_lead") {
    for (const field of business.qualificationRules.requiredFields) {
      const value = (lead as unknown as Record<string, unknown>)[field];
      if (value === null || value === undefined || value === "") missing.push(field);
    }
  }
  if (missing.length || request.ambiguous) {
    if (request.ambiguous && !request.safeClarificationQuestion) {
      return escalate("Ambiguity has no identified safe clarification.", "Have the owner review the ambiguity and choose a safe next step.");
    }
    return {
      outcome: "clarify", reason: "More customer information is needed before this action.",
      question: request.safeClarificationQuestion ?? `Could you provide ${[...new Set(missing)].join(", ")}?`,
      missingInformation: [...new Set(missing)],
    };
  }
  if (request.action === "qualify_lead" || request.action === "reject_lead") {
    const rule = policy.decisionRules?.find(rule => rule.action === request.action &&
      Object.keys(rule.when).length > 0 && Object.entries(rule.when).every(([key, value]) =>
        JSON.stringify((lead as unknown as Record<string, unknown>)[key]) === JSON.stringify(value)));
    if (!rule) return escalate("No configured decision rule clearly supports this decision.", "Ask the owner to review the lead or configure an explicit decision rule.");
    return { outcome: "act", reason: `Configured decision rule matched: ${rule.id}` };
  }
  return { outcome: "act", reason: "Routine action is permitted and the supplied safety checks passed." };
}

/** Records the preflight decision, not completion of the proposed customer action.
 * Pass the result to Phase 3's logAction when persistence is wanted.
 */
export function decisionToAgentAction(
  leadId: string, request: SafetyRequest, decision: SafetyDecision,
): AgentAction {
  return {
    id: randomUUID(), leadId, action: `safety:${request.action}:${decision.outcome}`,
    reason: JSON.stringify({ issue: request.issue, context: request.context, decision }),
    status: "completed", timestamp: new Date(),
  };
}
