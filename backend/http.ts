import { createServer } from "node:http";
import type { ServerResponse } from "node:http";
import type * as agentTools from "../lib/agentTools.js";

type ReadTools = Pick<typeof agentTools, "getBusiness" | "getLead" | "getConversationHistory">;

function json(response: ServerResponse, status: number, body: unknown) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(body));
}

// Only exposes reads. Agent reasoning and workflow execution belong elsewhere.
export function createBackendServer(tools: ReadTools) {
  return createServer(async (request, response) => {
    if (request.method !== "GET") {
      response.setHeader("Allow", "GET");
      json(response, 405, { error: "Only GET requests are supported" });
      return;
    }
    let parts: string[];
    try {
      const pathname = new URL(request.url ?? "/", "http://localhost").pathname;
      parts = pathname.split("/").slice(1).map(decodeURIComponent);
    } catch {
      json(response, 400, { error: "Invalid request URL" });
      return;
    }
    try {
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
      } else {
        json(response, 404, { error: "Endpoint not found" });
      }
    } catch {
      // Do not expose connection strings or database internals over HTTP.
      json(response, 503, { error: "Backend data is temporarily unavailable" });
    }
  });
}
