# EHACK

Phase 6A provides a read-only localhost bridge. It does not yet change the Streamlit UI.

From the repository root, with Node.js 22+ and Python 3.9+ installed:

```sh
npm install
npm run start:backend
```

The start command compiles TypeScript and loads the existing `.env.local` using
Node's `--env-file` option. MongoDB must be reachable before the server starts.
The server binds only to `127.0.0.1:8000`; set `NOVA_BACKEND_PORT` to use another port.

Available GET endpoints:

- `/health` — process health (not a fresh MongoDB ping).
- `/businesses/:businessId` — business record.
- `/leads/:leadId` — lead record.
- `/leads/:leadId/messages` — chronological conversation history.

Missing businesses/leads return 404. Known leads without messages return `[]`.
Other HTTP methods return 405; database read failures return 503.
Message timestamps serialize as ISO strings. This is a local development service.

In another terminal, verify the existing seeded MongoDB records through Python:

```sh
python3 -B test_backend_bridge.py
```

The verification only reads data and expects `nova-tutors` and `sarah-johnson`
to exist. Set `NOVA_BACKEND_URL` when using a different port.

Python applications can import `BackendClient` from `backend_client.py` and call
`health()`, `get_business(id)`, `get_lead(id)`, or `get_conversation_history(id)`.
Failed requests raise `BackendError`; HTTP errors include a `status` attribute.
No additional Python dependencies are required.

Type-check and run the HTTP/Python-client fixture tests plus existing safety tests:

```sh
npm run typecheck
npx tsc --outDir dist --declaration false --declarationMap false --sourceMap false
node --test dist/test-backend.js dist/test-safety.js
```

These fixture tests do not require MongoDB. `test_backend_bridge.py` is the separate
live Python → HTTP → agentTools → MongoDB verification.
