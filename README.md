# Nova — AI Customer Growth Agent

Nova is a prototype AI customer growth agent built for the EHACK hackathon. It helps a small business configure a business profile, understand incoming enquiries, prepare relevant customer communications, and decide when a lead is ready for a human-led next step.

The prototype demonstrates a human-supervised customer journey for Nova Tutors. Its AI uses business-provided information to guide each interaction, while the interface keeps owners in control of outbound communication and important decisions.

## Project objectives

Small businesses often handle enquiries across multiple steps: collecting business information, responding to prospective customers, deciding whether a service is suitable, and arranging a conversation with a team member. Nova brings those steps into one guided workspace. It is designed to:

- Capture a clear, owner-reviewed profile of the business, its services, pricing, tone, policies, and approval requirements.
- Turn customer messages into structured lead information that can be reviewed and acted on.
- Help the owner prioritize enquiries and identify missing information before recommending a next step.
- Prepare concise, personalized communication that reflects the business profile.
- Escalate decisions that require human judgment and avoid representing unconfirmed details as facts.

## What Nova can do

### 1. Guided business onboarding

The owner selects a quick, recommended, or in-depth setup and answers questions in natural language. Nova organizes the information into profile fields covering areas such as services, pricing, ideal customers, qualification criteria, business goals, tone, guardrails, approval rules, FAQs, availability, and policies. The owner can review and edit the profile before activation. Required fields must be supplied before Nova can be activated.

When Groq is enabled, one answer can populate multiple clearly stated fields. Nova does not fill in details that the owner has not provided. Answers such as “I don't know” are recorded as requiring clarification.

### 2. Lead workspace and conversation history

The dashboard displays leads, their current status, and a human-readable activity history. Each lead has a conversation view, structured customer facts, an assessment, and a recommended next action. The demo includes three sample journeys: Sarah, Rachel, and James.

Customer replies are added to the conversation and used to update the lead profile. The application tracks details including student year, subject, current and target grades, motivation, pricing interest, and additional facts such as exam board or availability.

### 3. Lead assessment and qualification

Nova assesses each lead across four dimensions:

- **Service fit:** whether the requested service and level match the business's stated offering.
- **Need:** whether the customer has a problem the business can address.
- **Urgency:** how soon support appears to be needed.
- **Intent:** how strongly the customer's messages indicate interest in proceeding.

Each dimension is scored **HIGH**, **MEDIUM**, **LOW**, or **UNKNOWN**. The assessment also provides a short rationale, missing qualification information, and a suggested next action. Unknown information remains unknown instead of being assumed.

In the application workflow, automatic qualification requires **HIGH** service fit, no **LOW** or **UNKNOWN** scores for need, urgency, and intent, and at least two of those three scores to be **HIGH**. The owner can explicitly override this assessment in the interface.

### 4. Personalized first-contact drafts

Nova drafts an initial message using the lead's known situation and the business profile. Drafts are intended to be specific, concise, and consistent with the business's stated tone. The owner can edit, approve, or reject the draft. The workflow remains paused until the owner takes action.

### 5. Reply understanding and suggested responses

Nova extracts structured information from customer replies and uses the conversation history to draft a response. When qualification information is missing, it can ask focused follow-up questions. When the lead is qualified, it can suggest an invitation to the business's stated next step. It recognizes acceptance or rejection in the consultation flow and updates the lead status accordingly.

Suggested responses are editable and require owner approval in the interface. If the AI indicates that it cannot answer reliably or that a decision requires human judgment, the app surfaces that handoff rather than presenting the response as ready to send.

### 6. Draft guardrail review

When Groq is enabled, Nova can review an outreach or reply draft against the business profile and flag issues such as unsupported prices, services, availability, or policies; guaranteed outcomes; unauthorized discounts; unconfirmed bookings; and assumptions presented as facts. A guardrail result is an aid to review, not a guarantee that a message is error-free.

### 7. Human handoff and respectful closure

Nova can recommend a human handoff for matters such as discounts, complaints, policy exceptions, unsupported requests, or missing reliable information. A customer who declines can be closed without further follow-up. A lead with a confirmed service mismatch can be marked **NOT A FIT**. The demo also hands a conversation to a human after ten customer messages if it has not reached a terminal outcome.

If a customer accepts a consultation invitation, Nova records **CONSULTATION REQUESTED** and tells the owner that a team member must confirm the exact time based on availability. Nova does not book a slot or confirm an appointment.

## AI functions

The Groq-backed functions are implemented in `agent.py` and called by the Streamlit app in `front.py`:

| Function | Purpose | Output |
| --- | --- | --- |
| `extract_profile_fields` | Extracts business facts clearly stated in an onboarding answer, including other relevant fields mentioned in that answer. | JSON mapping profile field keys to short values. |
| `analyse_lead` | Assesses service fit, need, urgency, and intent using lead facts and the conversation. | Scores, summary, missing information, and next action. |
| `draft_outreach` | Prepares an initial customer message personalized to the lead and business profile. | Plain-text draft under 120 words. |
| `extract_reply_info` | Extracts customer and student details, questions, pricing interest, and conversation outcome from a reply. | Structured JSON fields, with unknown details left null. |
| `draft_reply` | Prepares the next customer response, adapting to lead status and qualification, or signals that a human should respond. | Reply text, `needs_human` flag, and reason. |
| `check_guardrails` | Reviews a draft against business facts and communication rules. | Pass/fail result and a list of issues. |

The UI normalizes common structured response envelopes before displaying results. AI calls use the configured Groq model, request JSON output for structured tasks, and retry once for selected temporary service errors. The interface caches results during a Streamlit session to avoid repeating the same call on every rerun.

## Human oversight and operating principles

Nova's prompts instruct it to use only facts in the business profile, avoid inventing prices, services, availability, discounts, or policies, avoid guarantees, and never confirm a booking that has not occurred. It is directed to seek clarification or hand off when information is insufficient or a decision requires human judgment.

The prototype reflects these principles through its workflow: initial outreach, suggested replies, and consultation invitations are presented for owner review; customer replies and lead assessments are visible; and a human team member remains responsible for consultation scheduling. AI-generated content can still be inaccurate and should be checked before use with a real customer.

## Demo journeys

The sample data illustrates three different outcomes:

1. **Sarah — qualified GCSE Maths enquiry:** review and approve initial outreach, provide a sample customer reply, review Nova's suggested response, and follow the consultation invitation through to a human scheduling handoff.
2. **Rachel — enquiry requiring more information and owner approval:** clarify the student's needs, assess the lead after the conversation, then review a consultation recommendation before an invitation is added to the demo conversation.
3. **James — unsupported service:** clarify the level of tutoring required, identify the mismatch with the demo business's GCSE Maths and Science services, and close the lead without continuing sales follow-up.

The sample-reply buttons can be used to move through the journeys without entering customer messages manually. Use **Reset this lead**, **Reset leads**, or **Reset demo** to replay the scenarios.

## Technology

- **Python** — application logic and agent integration.
- **Streamlit** — interactive web interface and session-based demo workflow.
- **Groq Python SDK** — optional connection to Groq-hosted language models.
- **Default model:** `openai/gpt-oss-120b`, configurable through `GROQ_MODEL`.

When Groq is unavailable or no API key is configured, the app uses built-in mock functions for its demo workflow. These deterministic demo responses are intended to demonstrate the interface; they are not equivalent to live model-based extraction or reasoning. If a live AI call fails, the app records the error in the sidebar and falls back to its mock behavior for that operation.

## Installation and execution

### Requirements

- Python 3.10 or newer.
- Internet access and a Groq API key for live model responses. The key is optional for demo mode.

### Clone the repository

```bash
git clone https://github.com/ITADOR125/EHACK.git
cd EHACK
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run front.py
```

If PowerShell does not allow environment activation, run Streamlit using the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run front.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run front.py
```

Streamlit prints a local address, usually `http://localhost:8501`. Open it in a browser and leave the terminal running while using the app.

### Enable live AI responses (optional)

Create an API key in the [Groq Console](https://console.groq.com/keys), then set it in the terminal session before launching Streamlit.

PowerShell:

```powershell
$env:GROQ_API_KEY = "your_groq_api_key"
streamlit run front.py
```

macOS or Linux:

```bash
export GROQ_API_KEY="your_groq_api_key"
streamlit run front.py
```

The default model is `openai/gpt-oss-120b`. To use another model supported by Groq, set `GROQ_MODEL` before launching the app. For example:

```powershell
$env:GROQ_MODEL = "openai/gpt-oss-20b"
```

```bash
export GROQ_MODEL="openai/gpt-oss-20b"
```

Refer to Groq's current model documentation for available model identifiers. Keep API keys out of source control; `.env` files and local environment files are excluded by `.gitignore`.

## Project structure

```text
EHACK/
├── agent.py          # Groq client and AI capabilities
├── front.py          # Streamlit interface, workflows, and mock fallbacks
├── requirements.txt  # Python package requirements
├── .gitignore        # Excludes local environments, keys, and profile data
└── README.md         # Project and setup documentation
```

## Data handling and scope

The owner-reviewed business profile is written to `nova_profile.json` in the application directory when Nova is activated. Demo lead conversations and activity events are held in Streamlit session state; they are not stored in a persistent lead database. The project does not currently integrate with a CRM, email or messaging provider, calendar, payment service, or booking platform. Customer communications in the prototype are simulated in the interface.

This project is a hackathon prototype and is not a production deployment. In particular, it does not provide persistent lead storage, authentication, multi-user access control, external message delivery, appointment scheduling, or an automated guarantee of AI accuracy.

## Repository

[ITADOR125/EHACK](https://github.com/ITADOR125/EHACK)
