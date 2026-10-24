import { createHash } from "node:crypto";
import type { AgentAction } from "../lib/models.js";
import type * as agentTools from "../lib/agentTools.js";
import { evaluateProposal, parseProposal, ProposalInputError } from "./evaluateProposal.js";

export type ExecutionTools = Pick<
  typeof agentTools,
  "getBusiness" | "getLead" | "getConversationHistory"
> & {
  logAction(action: AgentAction, options: { idempotencyKey: string }): Promise<{ action: AgentAction; created: boolean }>;
};

export async function executeProposal(value: unknown, executionKey: string, tools: ExecutionTools) {
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(executionKey)) {
    throw new ProposalInputError("Idempotency-Key must contain 1–128 letters, digits, underscores, or hyphens");
  }
  const proposal = parseProposal(value);
  // Always reload. Submitted decisions, business snapshots, and approval flags
  // are never accepted as evidence of a previous safety approval.
  const business = await tools.getBusiness(proposal.businessId);
  const lead = await tools.getLead(proposal.leadId);
  if (!business || !lead) throw new ProposalInputError("Business or lead not found", 404);
  if (lead.businessId !== business.id) throw new ProposalInputError("Lead does not belong to the supplied business");
  const history = await tools.getConversationHistory(lead.id);
  const evaluation = evaluateProposal(proposal, business, lead, history);
  if (evaluation.safetyDecision !== "act") {
    return { status: 409, body: { ...evaluation, executed: false } };
  }
  if (proposal.action !== "ask_customer" || !proposal.proposedMessage) {
    throw new ProposalInputError("Only recording qualification questions is supported", 422);
  }
  const key = createHash("sha256").update(JSON.stringify([business.id, lead.id, executionKey])).digest("hex");
  const action: AgentAction = {
    id: `qualification-question:${key}`, leadId: lead.id,
    action: "record_qualification_question", status: "completed", timestamp: new Date(),
    reason: JSON.stringify({
      businessId: business.id, question: proposal.proposedMessage.content,
      proposalReason: proposal.reason, safetyDecision: "act", safetyReason: evaluation.reason,
      scope: "record_only_no_delivery_or_lead_update",
    }),
  };
  const saved = await tools.logAction(action, { idempotencyKey: key });
  if (saved.action.id !== action.id || saved.action.reason !== action.reason ||
      saved.action.leadId !== action.leadId || saved.action.action !== action.action) {
    throw new ProposalInputError("Idempotency-Key was already used for a different question; no action was performed", 409);
  }
  return {
    status: 200,
    body: {
      ...evaluation, executionStatus: saved.created ? "executed" : "already_executed",
      executed: saved.created, executedAction: "record_qualification_question", actionId: saved.action.id,
      messageSent: false, leadUpdated: false, proposedLeadUpdatesApplied: false,
    },
  };
}
