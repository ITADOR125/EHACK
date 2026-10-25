# Nova | AI Customer Growth Agent

Nova is an AI customer growth assistant prototype built for the EHACK hackathon. It helps a small business capture its operating knowledge, understand prospective customers, prepare relevant responses, and identify when an enquiry should move to a human.

The demonstration is built around Nova Tutors, a small tutoring business. The owner supplies the business facts and rules that guide the agent. A Streamlit workflow coordinates six focused AI tasks, presents recommendations for review, and keeps customer communications simulated within the application.

## The problem Nova addresses

Small businesses often handle enquiries across multiple steps: collecting business information, responding to prospective customers, deciding whether a service is suitable, and arranging a conversation with a team member. Nova brings those steps into one guided workspace. It aims to reduce repetitive work while keeping the business owner responsible for decisions that affect customers.

## How it works

The owner completes and reviews a business profile before activating Nova. For each lead, Nova uses the conversation to extract customer details, assess service fit and qualification, and recommend a next step. It may ask for missing information, prepare a response for owner review, or close the enquiry or flag it for a human. The language model performs structured extraction, assessment, and drafting; the Streamlit application controls the workflow and lead statuses. Nova does not have unrestricted access to external tools or customer systems.

## Agent capabilities

The six Groq-backed AI functions are defined in `agent.py` and invoked by `front.py`:

| Capability | Function | What it does |
| --- | --- | --- |
| Business knowledge extraction | `extract_profile_fields` | Extracts profile facts clearly stated in an owner's answer. It can populate multiple relevant fields from one answer and is instructed not to infer missing facts. |
| Lead assessment | `analyse_lead` | Assesses service fit, need, urgency, and intent as **HIGH**, **MEDIUM**, **LOW**, or **UNKNOWN**. Returns a short rationale, missing information, and a recommended next action. |
| First-contact drafting | `draft_outreach` | Drafts a concise, personalized first message using the lead details and business profile. The draft is presented for owner review. |
| Customer reply extraction | `extract_reply_info` | Extracts details such as student year, subject, current and target grades, motivation, pricing interest, other useful facts, questions, and whether a consultation was accepted or declined. Unknown information is returned as null or left unstated. |
| Customer response drafting | `draft_reply` | Drafts a response based on the latest customer message, conversation history, profile, and lead status. It can signal that a human should respond and provide a reason. |
| Draft guardrail review | `check_guardrails` | Checks a draft for unsupported claims about prices, services, availability, or policies; guaranteed outcomes; unauthorized discounts; unconfirmed bookings; and assumptions stated as fact. |

For structured tasks, the agent requests JSON output. The interface adapts common response formats before using the results. AI results are cached within a Streamlit session to avoid repeating the same request after every interface rerun. Selected temporary API errors are retried once; if an AI call still fails, the application records the error and uses its demo fallback for that operation.

## Lead assessment and qualification

Each assessment considers four dimensions:

- **Service fit:** does the requested subject and level match the services the business says it offers?
- **Need:** is there a customer need the business can address?
- **Urgency:** how soon does the customer appear to need support?
- **Intent:** how strongly do the customer's details and responses indicate interest in proceeding?

The assessment can identify missing qualification details and recommend what to ask next. Missing facts are meant to remain unknown rather than be guessed.

In the application workflow, automatic qualification requires **HIGH** service fit. Need, urgency, and intent must all be **HIGH** or **MEDIUM**, and at least two of those three must be **HIGH**. The owner can choose **Qualify anyway** as an explicit override.

## Human oversight and customer safeguards

Nova's prompts direct it to use only the business profile, avoid inventing prices, services, policies, discounts, or availability, avoid guaranteeing outcomes, and never confirm a booking that has not happened. The application includes human review at key points:

- The owner can review, edit, approve, or reject the first outreach draft.
- Suggested customer replies are editable and require owner approval before they are added to the demo conversation.
- The Rachel scenario pauses for owner approval before a consultation invitation is added.
- When Nova cannot answer reliably, it can flag the need for a human and show the reason.
- A customer who declines can be closed without further follow-up. A confirmed service mismatch can be closed as **NOT A FIT**.
- If a conversation reaches ten customer messages without a terminal outcome, the workflow changes it to **NEEDS HUMAN**.
- If a customer accepts a consultation invitation, the workflow records **CONSULTATION REQUESTED** and leaves scheduling to a team member.

The guardrail review is advisory: it displays flagged issues for the owner and does not itself guarantee that a draft is correct or prevent an owner from approving it. AI-generated content should be reviewed before it is used with a real customer.

## Demonstration scenarios

The app includes three sample leads that show different outcomes:

1. **Sarah — a GCSE Maths enquiry.** Review and approve personalized first outreach, use the sample customer response to add grade and pricing details, review a suggested reply, and continue to a consultation request. The final next step is for a team member to confirm a time.
2. **Rachel — an enquiry that needs qualification and owner approval.** Gather more detail about the student's needs, review the updated assessment, then approve or reject the consultation invitation recommendation.
3. **James — a university-level Maths enquiry.** Clarify what level of support he needs, identify that the demo business does not offer university tutoring, and close the lead without continuing sales follow-up.

Use the sample-reply buttons to advance each conversation without typing. **Reset this lead**, **Reset leads**, and **Reset demo** let you replay the workflows.

## Technology

- **Python** for application logic and Groq integration.
- **Streamlit** for the interactive web interface and session-based workflow.
- **Groq Python SDK** for optional hosted language-model responses.
- **Default model:** `openai/gpt-oss-120b`; the model can be selected with `GROQ_MODEL`.

Without a Groq API key, Nova uses built-in mock responses to demonstrate the workflows. Mock behavior is intended for the demo and is not equivalent to live model-based extraction or assessment.

## Setup and run

### Requirements

- Python 3.10 or newer.
- A Groq API key and internet access for live AI responses. Both are optional for mock/demo mode.

### 1. Clone the repository

```bash
git clone https://github.com/ITADOR125/EHACK.git
cd EHACK
```

### 2. Create an environment and install dependencies

**Windows PowerShell:**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell activation is unavailable, use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run front.py
```

**macOS or Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Start Nova

```bash
streamlit run front.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`. Leave the terminal running while using the app.

### Optional: enable live Groq responses

Create an API key in the [Groq Console](https://console.groq.com/keys). Set it in the same terminal session before starting Streamlit.

**Windows PowerShell:**

```powershell
$env:GROQ_API_KEY = "your_groq_api_key"
streamlit run front.py
```

**macOS or Linux:**

```bash
export GROQ_API_KEY="your_groq_api_key"
streamlit run front.py
```

The default model is `openai/gpt-oss-120b`. To use another model supported by your Groq account, set `GROQ_MODEL` before launching, for example:

```powershell
$env:GROQ_MODEL = "openai/gpt-oss-20b"
```

```bash
export GROQ_MODEL="openai/gpt-oss-20b"
```

Check Groq's current documentation for available model identifiers. Do not commit API keys or other secrets to the repository.

## Project structure

```text
EHACK/
├── agent.py          # Groq client and six AI capabilities
├── front.py          # Streamlit UI, workflow logic, and mock fallbacks
├── requirements.txt  # Streamlit and Groq Python dependencies
├── .gitignore        # Local environment, key, and profile exclusions
└── README.md         # Project and setup documentation
```

## Data, privacy, and current scope

The owner-reviewed business profile is written to `nova_profile.json` when Nova is activated. Lead conversations and activity events are kept in Streamlit session state and are not saved to a persistent lead database. When live AI is enabled, profile facts, lead details, and conversation text used for a task are included in requests to Groq.

This is a hackathon prototype. Customer messages are simulated inside the interface; the app does not send email or SMS, connect to a CRM, process payments, or book calendar appointments. It does not currently provide authentication, multi-user access control, or persistent lead storage. Review the data-handling requirements of any real deployment before entering customer information.

## Repository

[ITADOR125/EHACK on GitHub](https://github.com/ITADOR125/EHACK)

---

## Purpose (V3)

Nova is an AI customer-growth agent demo for small businesses. This proof of concept uses Nova Tutors, a fictional tutoring business, and three leads with different outcomes. Nova uses known business information to recognise needs, extract facts, classify the fit of a lead, decide a next action, and provide a customer-facing draft. It is **not** a verified tutor scheduling or booking engine.

## Architecture and decision-making process (V3)

1. **Input:** The confirmed `BUSINESS` profile, one lead record, and that lead's conversation messages (`customer` / `agent`). Do not mix records between leads.
2. **Groq extraction:** For the latest customer message, `groq_extract()` requests JSON `facts` and verbatim `quotes`. Groq does **not** directly decide qualification or update the database in V3.
3. **Validation and update proposal:** `safe_patch()` checks allowed field names, quoted evidence, normalisation, and changed values; the resulting `extracted_information` is a proposed *delta*. `apply_extraction()` produces a proposed updated lead.
4. **Python qualification and guardrails:** `service_fit()`, `explicit_intent()`, `missing_information()`, `question_kind()` and `decide_next_action()` apply business eligibility, needs, interest, and safety rules. In V3, **Python templates produce the customer-facing message**, drawing on the lead and business data.
5. **Structured JSON:** `decide_next_action(business, lead, conversation)` returns a decision with `lead_status`, `next_action`, `message`, `reason`, `qualification`, `missing_information`, `extracted_information`, `updated_lead`, `review_status`, `requires_human_approval`, and `escalation`.
6. **Human control:** Initial outreach, consultation arrangements, and unverified matters require review where flagged. The decision **proposes** an action; it does not itself send a real message, route a review to a person, or confirm a booking.

## Three demo journeys (V3)

| Lead | What Nova knows | Expected decision | Why |
|---|---|---|---|
| **Sarah Johnson** | Daniel, Year 11, GCSE Maths; grade 4 to 6, Edexcel Higher, interested in a free consultation | `qualified` + `recommend_consultation` after explicit interest | Supported service, real need and enough interest |
| **Rachel Thompson** | Oliver, Year 10, exam-technique challenges, Edexcel Maths; price, tutor and progress concerns | `consultation_needed` + a price answer or consultation recommendation | Suitable service but unresolved questions needing discussion |
| **James Carter** | University-level Calculus and Linear Algebra tutoring | `not_qualified` + `close_lead` | University **subject tutoring** is not offered, even though university *admissions/application support* is a different offering |

## Eligibility and guardrails (V3)

- GCSE Maths and specified GCSE Sciences: supported; confirmed GCSE rate is **£30 per 60-minute session**.
- A-Level subjects/prices and university admissions/application support price: **not yet confirmed**; do not invent price or coverage.
- University-level Maths tutoring is **unsupported**. Do not conflate it with university admissions support.
- Online tutoring can be considered UK-wide; in-person tutoring needs customer location, tutor location and verified tutor availability, especially outside selected London areas.
- Do not guarantee grades, tutor slots, prices for unconfirmed services, discounts, message delivery, or bookings.
- Consultation is a **free 15-minute conversation**, but must not be described as booked until the backend has confirmed it.
- Messages generated by the agent are only drafts/proposals until the actual workflow confirms approval/sending.
- An `escalation` with `status: requested_not_routed` is **not** proof that a human was notified.

## State and limitation disclosure (V3)

V3's terminal app stores separate sessions in `data/sessions.json` through `load_sessions()` and `save_sessions()`. This is **local demo persistence**, not MongoDB. `/approve` simulates approval only. There is currently no verified real-time tutor calendar, consultation booking, external delivery, or human-review routing in this code. Integrating Groq with the deployed website must be checked separately by verifying the network request, backend endpoint, and logs.

## Reproduce offline tests (V3)

Run the offline test suite with:

```powershell
python -m unittest -v test_brain.py
```

The supplied V3 report records **16 offline tests passing**. These use `extraction_override` to bypass Groq, so they test Python rules but **do not prove** live Groq inference or frontend/backend integration.
