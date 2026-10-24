import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import clientPromise from "./lib/mongodb.js";
import {
  getBusiness, getLead, updateLead, saveMessage, getConversationHistory, logAction,
} from "./lib/agentTools.js";
import { novaTutors, sarahJohnson } from "./lib/demoData.js";
import type { AgentAction, Business, Lead, Message } from "./lib/models.js";
import { executeProposal } from "./backend/executeProposal.js";

async function main() {
  const client = await clientPromise;
  const db = client.db("nova");
  const prefix = `agent-tools-test-${randomUUID()}`;
  const business: Business = { ...novaTutors, id: `${prefix}-business` };
  const lead: Lead = { ...sarahJohnson, id: `${prefix}-lead`, businessId: business.id };
  const missingId = `${prefix}-missing`;

  try {
    // Isolated copies of the fixtures leave existing demo records untouched.
    await db.collection<Business>("businesses").insertOne({ ...business });
    await db.collection<Lead>("leads").insertOne({ ...lead });
    assert.deepEqual(await getBusiness(business.id), business);
    assert.deepEqual(await getLead(lead.id), lead);
    assert.equal(await getBusiness(missingId), null);
    assert.equal(await getLead(missingId), null);
    assert.deepEqual(await getConversationHistory(lead.id), []);

    const updated = await updateLead(lead.id, { currentGrade: 4, status: "contacted" });
    assert.deepEqual(updated, { ...lead, currentGrade: 4, status: "contacted" });
    assert.deepEqual(await getLead(lead.id), updated);
    assert.equal(await updateLead(missingId, { currentGrade: 4 }), null);
    assert.equal(await getLead(missingId), null);

    const first: Message = {
      id: `${prefix}-message-1`, leadId: lead.id, sender: "customer",
      content: "Daniel is currently getting a grade 4.", timestamp: new Date("2026-01-01T10:00:00Z"),
    };
    const second: Message = {
      id: `${prefix}-message-2`, leadId: lead.id, sender: "nova",
      content: "What grade is Daniel aiming for?", timestamp: new Date("2026-01-01T10:01:00Z"),
    };
    const unrelated: Message = { ...first, id: `${prefix}-message-other`, leadId: missingId };
    assert.deepEqual(await saveMessage(second), second);
    assert.deepEqual(await saveMessage(first), first);
    await saveMessage(unrelated);
    assert.deepEqual(await getConversationHistory(lead.id), [first, second]);

    const action: AgentAction = {
      id: `${prefix}-action`, leadId: lead.id, action: "update_lead",
      reason: "Customer shared current grade", status: "completed", timestamp: new Date(),
    };
    assert.deepEqual(await logAction(action), action);
    assert.deepEqual(
      await db.collection<AgentAction>("agent_actions").findOne({ id: action.id }, { projection: { _id: 0 } }),
      action,
    );
    const onceAction = { ...action, id: `${prefix}-once`, action: "record_qualification_question" };
    const attempts = await Promise.all(Array.from({ length: 6 }, () =>
      logAction(onceAction, { idempotencyKey: `${prefix}-receipt` })));
    assert.equal(attempts.filter(result => result.created).length, 1);
    assert.equal(await db.collection("agent_actions").countDocuments({ id: onceAction.id }), 1);
    const replay = await logAction({ ...onceAction, reason: "changed question" }, { idempotencyKey: `${prefix}-receipt` });
    assert.equal(replay.created, false);
    assert.equal(replay.action.reason, onceAction.reason);
    // Exercise the gate itself with authoritative reads and the real MongoDB tool.
    const proposal = {
      businessId: business.id, leadId: lead.id, action: "ask_customer", reason: "Ask tutoring preference",
      proposedMessage: { leadId: lead.id, sender: "nova", content: "Would you prefer online or in-person tutoring?" },
      proposedLeadUpdates: {}, missingInformation: [], brainRequiresHumanApproval: false,
      executionStatus: "not_executed", safetyDecision: "act", // ignored by the backend
    };
    const tools = { getBusiness, getLead, getConversationHistory, logAction };
    // Existing fixture messages contain no discount request.
    const before = await db.collection("agent_actions").countDocuments({ leadId: lead.id });
    const executions = await Promise.all(Array.from({ length: 4 }, () => executeProposal(proposal, "mongodb-turn", tools)));
    assert.equal(executions.filter(result => result.body.executionStatus === "executed").length, 1);
    assert.equal(await db.collection("agent_actions").countDocuments({ leadId: lead.id }), before + 1);
    assert.equal((await getLead(lead.id))?.status, "contacted");
    await updateLead(lead.id, { status: "closed" });
    const staleApproval = await executeProposal(proposal, "after-close", tools);
    assert.equal(staleApproval.body.safetyDecision, "escalate");
    assert.equal(staleApproval.body.executionStatus, "not_executed");
    assert.equal(await db.collection("agent_actions").countDocuments({ leadId: lead.id }), before + 1);
    console.log("All six agent tools passed MongoDB integration checks.");
    console.log("MongoDB execution gate passed: concurrent replay protection and authoritative closed-lead rejection.");
  } finally {
    try {
      await db.collection("messages").deleteMany({ leadId: { $in: [lead.id, missingId] } });
      await db.collection("agent_actions").deleteMany({ leadId: lead.id });
      await db.collection("leads").deleteOne({ id: lead.id });
      await db.collection("businesses").deleteOne({ id: business.id });
    } finally {
      await client.close();
    }
  }
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
