import clientPromise from "../lib/mongodb.js";
import { getBusiness, getLead, getConversationHistory, logAction } from "../lib/agentTools.js";
import { createBackendServer } from "./http.js";

async function main() {
  const client = await clientPromise;
  const port = Number(process.env.NOVA_BACKEND_PORT ?? 8000);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    await client.close();
    throw new Error("NOVA_BACKEND_PORT must be an integer between 1 and 65535");
  }
  const server = createBackendServer({ getBusiness, getLead, getConversationHistory }, { logAction });
  server.on("error", () => {
    console.error("Backend could not listen; check whether its port is already in use.");
    void client.close().finally(() => { process.exitCode = 1; });
  });
  server.listen(port, "127.0.0.1", () => {
    console.log(`Nova backend listening at http://127.0.0.1:${port}`);
  });
  for (const signal of ["SIGINT", "SIGTERM"] as const) {
    process.once(signal, () => {
      server.close(() => { void client.close(); });
    });
  }
}

main().catch(() => {
  console.error("Backend startup failed. Check MONGODB_URI and MongoDB network access.");
  process.exitCode = 1;
});
