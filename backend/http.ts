import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";
import type * as agentTools from "../lib/agentTools.js";
import { evaluateProposal, parseProposal, ProposalInputError } from "./evaluateProposal.js";
import { executeProposal } from "./executeProposal.js";
import type { ExecutionTools } from "./executeProposal.js";

type ReadTools = Pick<typeof agentTools, "getBusiness" | "getLead" | "getConversationHistory"> &
  Partial<Pick<typeof agentTools, "getAgentActions">>;

function json(response: ServerResponse, status: number, body: unknown) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(body));
}

async function readProposal(request: IncomingMessage) {
  if (request.headers["content-type"]?.split(";")[0]?.trim() !== "application/json") {
    throw new ProposalInputError("Content-Type must be application/json", 415);
  }
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request.iterator({ destroyOnReturn: false })) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > 65536) {
      request.resume();
      throw new ProposalInputError("Proposal exceeds 64 KiB", 413);
    }
    chunks.push(buffer);
  }
  let value: unknown;
  try { value = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
  catch { throw new ProposalInputError("Invalid JSON"); }
  return parseProposal(value);
}

// GET routes use only read tools. Execution is isolated behind its POST gate.
export function createBackendServer(tools: ReadTools, executionTools?: Pick<ExecutionTools, "logAction">) {
  return createServer(async (request, response) => {
    let parts: string[];
    try {
      const pathname = new URL(request.url ?? "/", "http://localhost").pathname;
      parts = pathname.split("/").slice(1).map(decodeURIComponent);
    } catch {
      json(response, 400, { error: "Invalid request URL" });
      return;
    }
    const evaluationRoute = parts.length === 2 && parts[0] === "proposals" && parts[1] === "evaluate";
    const executionRoute = parts.length === 2 && parts[0] === "proposals" && parts[1] === "execute";
    const allowedMethod = evaluationRoute || executionRoute ? "POST" : "GET";
    if (request.method !== allowedMethod) {
      response.setHeader("Allow", allowedMethod);
      json(response, 405, { error: `Only ${allowedMethod} requests are supported here` });
      return;
    }
    try {
      if (executionRoute) {
        if (!executionTools) throw new ProposalInputError("Execution tools are not configured", 503);
        const key = request.headers["idempotency-key"];
        if (typeof key !== "string") throw new ProposalInputError("Idempotency-Key is required");
        const proposal = await readProposal(request);
        const result = await executeProposal(proposal, key, { ...tools, ...executionTools });
        json(response, result.status, result.body);
        return;
      }
      if (evaluationRoute) {
        const proposal = await readProposal(request);
        const business = await tools.getBusiness(proposal.businessId);
        const lead = await tools.getLead(proposal.leadId);
        if (!business || !lead) {
          json(response, 404, { error: "Business or lead not found" });
          return;
        }
        if (lead.businessId !== business.id) {
          throw new ProposalInputError("Lead does not belong to the supplied business");
        }
        const history = await tools.getConversationHistory(lead.id);
        json(response, 200, evaluateProposal(proposal, business, lead, history));
        return;
      }
      if (parts.length === 1 && parts[0] === "health") {
        json(response, 200, { status: "ok" });
        return;
      }
      const id = parts[1];
      if (id && parts.length === 2 && parts[0] === "businesses") {
        const business = await tools.getBusiness(id);
        json(response, business ? 200 : 404, business ?? { error: "Business not found" });
      } else if (id && parts.length === 2 && parts[0] === "leads") {
        const lead = await tools.getLead(id);
        json(response, lead ? 200 : 404, lead ?? { error: "Lead not found" });
      } else if (id && parts.length === 3 && parts[0] === "leads" && parts[2] === "messages") {
        // A known lead with no messages returns []; an unknown lead returns 404.
        if (!await tools.getLead(id)) {
          json(response, 404, { error: "Lead not found" });
          return;
        }
        json(response, 200, await tools.getConversationHistory(id));
      } else if (id && parts.length === 3 && parts[0] === "leads" && parts[2] === "actions") {
        if (!await tools.getLead(id)) {
          json(response, 404, { error: "Lead not found" });
          return;
        }
        if (!tools.getAgentActions) throw new ProposalInputError("Action reads are not configured", 503);
        json(response, 200, await tools.getAgentActions(id));
      } else {
        json(response, 404, { error: "Endpoint not found" });
      }
    } catch (error) {
      if (error instanceof ProposalInputError) {
        json(response, error.status, { error: error.message });
        return;
      }
      // Do not expose connection strings or database internals over HTTP.
      json(response, 503, { error: "Backend data is temporarily unavailable" });
    }
  });
}
