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

The execution gate adds `POST /proposals/execute` with the proposal JSON and an
`Idempotency-Key` header (1–128 letters, digits, underscores, or hyphens). Python
can call `client.execute_proposal(proposal, execution_key)` and reuse the same key
on retries. The backend reloads business, lead, and message data and reruns safety;
client-supplied safety decisions never authorize execution.

Only an `act` decision for `ask_customer` can record a qualification question in
`agent_actions` using `logAction`. This records a question; it does not deliver it,
add it to conversation history, or apply proposed lead changes. Non-act decisions
return HTTP 409. Replays return `already_executed`; reusing a key for another
question returns 409. MongoDB's unique `_id` stores the action and replay receipt
atomically, including across concurrent requests and backend restarts.

Include `dist/test-proposal-safety.js` and `dist/test-execution-gate.js` in the
`node --test` command above to run the evaluation and execution-gate tests.



##Edit by Fatima
# Nova Brain V3 — Copy/Paste Edition

**No real messages, bookings or human escalations are sent.** This is a local, multi-lead Groq-powered demo with deterministic business rules. One customer per session; all conversation/lead state is stored in `data/sessions.json`.

## Files

- `brain.py` — customer seeds, business profile, Groq structured extraction, qualification and safe action rules, local storage helpers.
- `demo.py` — interactive terminal, `/users`, `/switch`, `/new`, `/restart`, `/inquiry`, `/show`, `/start`, `/approve` (simulation), `/quit`.
- `test_brain.py` — offline tests; no API key required.
- `.env.example` — Groq configuration template.
- `requirements.txt` — dependencies.
- `START_NOVA.bat` — installation/start shortcut.

## Install into a NEW folder

Open PowerShell:

```powershell
$base = "C:\Users\hello\OneDrive - City St George's, University of London\ENCODE HACKATHON"
Expand-Archive "$HOME\Downloads\Nova-Brain-V3-CopyPaste.zip" -DestinationPath "$base\Nova-Brain-V3" -Force
Copy-Item "$base\Nova-Brain-V1\.env" "$base\Nova-Brain-V3\.env" -ErrorAction SilentlyContinue
cd "$base\Nova-Brain-V3"
python -m pip install -r requirements.txt
python demo.py
```

If `.env` is missing, run `Copy-Item .env.example .env` and `notepad .env` and set GROQ_API_KEY. If the old `.env` used another model, make sure GROQ_MODEL is a model your Groq account can access; `openai/gpt-oss-120b` worked in your recent screenshot.

## Try it

```
/users
/switch rachel
/inquiry
How much does GCSE Maths cost?
Could we have the free consultation?
/show
/switch james
/inquiry
/switch sarah
He's doing Edexcel Higher.
/restart
```

Tests: `python -m unittest -v test_brain.py`

## Integration contract

Use `decide_next_action(business, lead, conversation)` and read:

```json
{
  "lead_id": "rachel",
  "lead_status": "consultation_needed",
  "review_status": "pending",
  "extracted_information": {},
  "updated_lead": {},
  "missing_information": [],
  "next_action": "recommend_consultation",
  "message": "...",
  "reason": "...",
  "qualification": {
    "service_fit": "confirmed",
    "need": "confirmed",
    "intent": "confirmed",
    "delivery": "online_supported",
    "evidence": [],
    "blockers": []
  },
  "requires_human_approval": true,
  "escalation": null
}
```

`lead_status` and `updated_lead.lead_status` always match. `extracted_information` is a patch of newly quoted facts, not an entire record. `review_status` is independent of `lead_status`. If `escalation.status` is `requested_not_routed`, it has NOT been sent to a human. A booking or message has NOT occurred unless a separate workflow confirms it.

## Engineering limitations

- Live model outputs are not tested here; local offline tests passed. Quote checks reduce but do not eliminate model extraction errors. A production backend needs independent factual validation, authenticated access controls, concurrency handling and consent/privacy safeguards.
- Multi-customer data persists locally; MongoDB integration is still a team task.
- Consultation approvals in the CLI are mock actions only.
- A-Level service subjects/prices and admissions pricing are deliberately left unconfirmed.
- University Mathematics tuition is unsupported, distinct from university admissions/application support.
