import clientPromise from "./mongodb.js";
import type { AgentAction, Business, Lead, Message } from "./models.js";

async function database() {
  return (await clientPromise).db("nova");
}

export async function getBusiness(businessId: string): Promise<Business | null> {
  return (await database()).collection<Business>("businesses").findOne(
    { id: businessId },
    { projection: { _id: 0 } },
  );
}

export async function getLead(leadId: string): Promise<Lead | null> {
  return (await database()).collection<Lead>("leads").findOne(
    { id: leadId },
    { projection: { _id: 0 } },
  );
}

// Preserve the lead's identity and business association. Missing leads return null.
export async function updateLead(
  leadId: string,
  updates: Partial<Omit<Lead, "id" | "businessId">>,
): Promise<Lead | null> {
  const leads = (await database()).collection<Lead>("leads");
  return leads.findOneAndUpdate(
    { id: leadId },
    { $set: updates },
    { returnDocument: "after", projection: { _id: 0 } },
  );
}

export async function saveMessage(message: Message): Promise<Message> {
  await (await database()).collection<Message>("messages").insertOne({ ...message });
  return message;
}

export async function getConversationHistory(leadId: string): Promise<Message[]> {
  return (await database()).collection<Message>("messages")
    .find({ leadId }, { projection: { _id: 0 } })
    .sort({ timestamp: 1, id: 1 })
    .toArray();
}

export async function logAction(action: AgentAction): Promise<AgentAction> {
  await (await database()).collection<AgentAction>("agent_actions").insertOne({ ...action });
  return action;
}
