import { checkSafety } from "../lib/safety.js";
import type { SafetyRequest } from "../lib/safety.js";
import type { Business, Lead, Message } from "../lib/models.js";

export class ProposalInputError extends Error {
  constructor(message: string, public status = 400) { super(message); }
}

const actionMap: Record<string, string> = {
  ask_customer: "ask_qualification_question", answer_customer: "answer_faq",
  draft_outreach: "send_outreach", close_lead: "reject_lead",
  recommend_consultation: "recommend_next_action",
  escalate_to_human: "recommend_next_action",
};

type Proposal = {
  businessId: string; leadId: string; action: string; reason: string;
  proposedMessage: { leadId: string; sender: "nova"; content: string } | null;
  proposedLeadUpdates: Record<string, unknown>;
  missingInformation: string[]; brainRequiresHumanApproval: boolean;
  escalation?: unknown;
};

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseProposal(value: unknown): Proposal {
  if (!object(value) || !["businessId", "leadId", "action", "reason"].every(
    key => typeof value[key] === "string" && (value[key] as string).trim().length > 0,
  )) throw new ProposalInputError("Proposal requires businessId, leadId, action, and reason strings");
  const message = value.proposedMessage;
  if (message !== null && (!object(message) || message.leadId !== value.leadId ||
      message.sender !== "nova" || typeof message.content !== "string")) {
    throw new ProposalInputError("proposedMessage must be null or a Nova draft for the same lead");
  }
  if (!object(value.proposedLeadUpdates) || !Array.isArray(value.missingInformation) ||
      !value.missingInformation.every(field => typeof field === "string") ||
      typeof value.brainRequiresHumanApproval !== "boolean" || value.executionStatus !== "not_executed") {
    throw new ProposalInputError("Invalid proposal updates, missing information, approval flag, or execution status");
  }
  for (const key of ["status", "nextAction"]) {
    if (key in value.proposedLeadUpdates && typeof value.proposedLeadUpdates[key] !== "string") {
      throw new ProposalInputError("Proposed status and nextAction must be strings");
    }
  }
  return value as unknown as Proposal;
}

// Deliberately narrow: these exact questions make no business claims. Arbitrary
// prose is NOT declared safe by keyword checks or client-supplied attestations.
function routineQuestion(text: string, lead: Lead): boolean {
  const student = lead.student.name || "the student";
  return [
    "Which subject and qualification level would you like tutoring or support with?",
    "Which subject and qualification level are you looking for?",
    "Would you prefer online or in-person tutoring?",
    `What is ${student} finding most difficult right now?`,
    `Roughly what grade is ${student} currently working at?`,
    `What grade is ${student} hoping to achieve?`,
    `Do you know which exam board ${student} is studying?`,
    `Is ${student} taking Foundation or Higher Maths, if you know?`,
    "Which area would in-person tutoring need to take place in?",
  ].includes(text);
}

export function evaluateProposal(proposal: Proposal, business: Business, lead: Lead, history: Message[]) {
  const action = Object.hasOwn(actionMap, proposal.action) ? actionMap[proposal.action]! : "unconfigured_action";
  const text = proposal.proposedMessage?.content ?? "";
  const question = proposal.action === "ask_customer" && routineQuestion(text, lead);
  const routineOutreach =
    proposal.action === "draft_outreach" &&
    business.services.some(service =>
      text === `Hi ${lead.name.split(" ")[0]}, I'm getting in touch from ${business.name} about ${lead.student.name}'s ${service.name.replace(/ tutoring$/i, "")}. What would you most like some support with?`
    );
  // Read customer context from MongoDB, not client-supplied owner notes or flags.
  const latestCustomer = history.filter(message => message.sender === "customer").at(-1)?.content ?? "";
  const contextText = [text, proposal.reason, latestCustomer, JSON.stringify(proposal.escalation ?? null)].join("\n");
  const discount = /\b(discount|price exception|price reduction|special price|cheaper|reduce (?:the |your )?price)\b/i.test(contextText);
  const guarantee = text.split(/[.!?\n]/).some(sentence => {
    // Exempt the brain's explicit denial, not arbitrary sentences containing 'no'.
    if (/^\s*no grade improvement or particular lesson slot can be guaranteed\s*$/i.test(sentence)) return false;
    return /\bguarantee(?:s|d)?\b/i.test(sentence) && /\b(grade|grades|improvement|outcome|results?)\b/i.test(sentence);
  });
  const unsupportedUpdates = Object.keys(proposal.proposedLeadUpdates).some(key => !["status", "nextAction"].includes(key));
  const conflictingAction = proposal.proposedLeadUpdates.nextAction !== undefined &&
    proposal.proposedLeadUpdates.nextAction !== proposal.action;
  const status = proposal.proposedLeadUpdates.status;
  const decisionChange = typeof status === "string" && status !== lead.status &&
    !["new", "needs_information", "responded", "contacted"].includes(status);
  const request: SafetyRequest = {
    action, issue: proposal.reason,
    context: [`Brain action: ${proposal.action}`, `Draft: ${text}`, `Latest customer message: ${latestCustomer}`],
    restrictionChecks: business.restrictions.map(restriction => ({
      restriction,
      // Exact routine questions can satisfy these two known restrictions. Other
      // configured restrictions require actual review and remain unknown.
      result: (question || routineOutreach) && [
        "do not guarantee specific grade improvements",
        "do not invent information about the tutoring service",
      ].includes(restriction.trim().toLowerCase()) ? "satisfied" : "unknown",
    })),
    guaranteesOutcome: guarantee,
    discountOrPriceException: discount,
          requiresOwnerJudgement:
        proposal.action === "escalate_to_human" ||
        (proposal.brainRequiresHumanApproval && !routineOutreach) ||
        Boolean(proposal.escalation) ||
        decisionChange ||
        ["closed", "not_qualified", "not a fit", "needs human", "needs_human", "consultation_requested"]
          .includes(lead.status.toLowerCase()),
    // No evidence is supplied for changed learned facts or arbitrary prose.
    potentiallyMisleading: unsupportedUpdates || conflictingAction || !(question || routineOutreach),
    missingInformation: proposal.action === "ask_customer" ? proposal.missingInformation : [],
  };
  if (question) request.safeClarificationQuestion = text;
  const decision = checkSafety(business, lead, request);
  return {
    proposedAction: proposal.action, mappedSafetyAction: action,
    safetyDecision: decision.outcome, reason: decision.reason, decision,
    escalation: decision.outcome === "escalate" ? decision.escalation : null,
    executionStatus: "not_executed" as const,
    evaluationScope: "proposal_preflight_only",
  };
}
