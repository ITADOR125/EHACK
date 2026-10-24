"""
Nova's AI brain (Groq).

Setup:
    pip install groq
    $env:GROQ_API_KEY="your_key_here"      (PowerShell, same terminal you run Streamlit from)

Get a free key at https://console.groq.com/keys

Every function takes the stored business profile (dict of text fields) and
grounds its answer in it.
"""
import json
import os
import time

from groq import Groq

# Check https://console.groq.com/docs/models for current model names.
# Override without touching code:  $env:GROQ_MODEL="openai/gpt-oss-20b"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

_client = None


def available():
    return bool(os.getenv("GROQ_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        _client = Groq(timeout=20.0)  # reads GROQ_API_KEY; gives up after 20s
    return _client


RULES = """You are Nova, an AI customer growth agent working for a small business.

Hard rules:
- Use ONLY facts in the business profile below. If something is not there, say you will check with the team. Never guess.
- Never invent prices, availability, services, policies, or discounts.
- Never guarantee outcomes (for example, exam grades).
- Never confirm a booking that has not actually happened.
- Follow the business's own guardrails, tone and approval rules in the profile.
- If a request needs human judgement (discounts, complaints, policy exceptions, unsupported services, anything you lack reliable information for), flag it for a human instead of improvising.
- Understand first, recommend second, sell third. Do not be pushy or generic."""


def _profile_text(profile):
    if not profile:
        return "(empty)"
    return "\n".join(f"- {k}: {v}" for k, v in profile.items())


def _facts(lead):
    return {k: v for k, v in lead.items() if k not in ("thread", "drafts")}


def _transcript(lead):
    lines = [("Nova" if who == "Nova" else "Customer") + ": " + text for who, text in lead.get("thread", [])]
    return "\n".join(lines) or "(no messages yet)"


def _system(profile):
    return f"{RULES}\n\nBUSINESS PROFILE\n{_profile_text(profile)}"


def _call(system, prompt, as_json=False, temperature=0.3):
    kwargs = dict(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=temperature,
    )
    if as_json:
        kwargs["response_format"] = {"type": "json_object"}
    if "gpt-oss" in MODEL:
        kwargs["reasoning_effort"] = "low"  # less thinking = faster replies

    last_error = None
    for _ in range(2):  # one retry for temporary errors (rate limit / overload)
        try:
            resp = _get_client().chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_error = e
            if not any(code in str(e) for code in ("429", "503", "504", "overloaded", "timed out")):
                raise
            time.sleep(1.5)
    raise last_error


def _json(system, prompt):
    text = _call(system, prompt, as_json=True, temperature=0.1)
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


# ---------------------------------------------------------------
# 1. ONBOARDING: pull several profile fields out of one answer
# ---------------------------------------------------------------
def extract_profile_fields(profile, field_labels, asked_key, answer):
    """field_labels: {key: human label}. Returns {key: value} for fields clearly stated."""
    prompt = f"""You are helping onboard a business owner. Nova just asked about: "{field_labels.get(asked_key, asked_key)}".

Owner's answer:
\"\"\"{answer}\"\"\"

Fields Nova can fill (key: label):
{json.dumps(field_labels, indent=2)}

Already known (do not repeat): {json.dumps(profile)}

Return a JSON object mapping field keys to short text values for every field the owner's answer CLEARLY states.
Include "{asked_key}" with a clean summary of the answer. Do not guess or invent anything not said.
Do not include fields that are not mentioned."""
    return _json("You extract structured business facts. Output JSON only.", prompt)


# ---------------------------------------------------------------
# 2. LEAD ANALYSIS
# ---------------------------------------------------------------
def analyse_lead(profile, lead):
    prompt = f"""Assess this lead for the business using BOTH the facts and the conversation so far.

LEAD FACTS:
{json.dumps(_facts(lead), indent=2)}

CONVERSATION SO FAR:
{_transcript(lead)}

Score each as HIGH, MEDIUM, LOW or UNKNOWN:
- service_fit: does the business actually offer what this person needs? LOW if they want something the profile says is NOT offered (or the wrong level/year).
- need: is there a real problem the business can solve?
- urgency: how soon do they appear to need help (deadlines, exams, results)?
- intent: how strongly their behaviour suggests they want to buy. Strong signals: asking about price, availability or how to start, giving specific details about the student, mentioning a deadline, engaging with questions. Weak signals: vague curiosity, "just looking", not answering, objecting without engaging.
Use UNKNOWN when the information is not there. Do not assume.

Return JSON with keys: service_fit, need, urgency, intent, summary (1-2 sentences about this person and why you scored them this way), missing (list of qualification info the business needs that is still unknown), next_action (one sentence)."""
    return _json(_system(profile), prompt)


# ---------------------------------------------------------------
# 3. OUTREACH
# ---------------------------------------------------------------
def draft_outreach(profile, lead):
    prompt = f"""Write the FIRST outreach message to this lead. A human will review it before sending.

LEAD:
{json.dumps({k: v for k, v in lead.items() if k not in ('thread', 'drafts')}, indent=2)}

Requirements:
- Match the business's customer-facing tone from the profile.
- Reference the lead's real situation, not generic marketing.
- Move gently toward the business's goal from the profile.
- Do not mention price unless the profile makes it appropriate. Do not promise outcomes or availability.
- Short: under 120 words. Plain text, sign off with the business name.
Output only the message text."""
    return _call(_system(profile), prompt, temperature=0.6)


# ---------------------------------------------------------------
# 4. UNDERSTAND THE CUSTOMER'S REPLY
# ---------------------------------------------------------------
def extract_reply_info(lead, message):
    prompt = f"""A customer wrote: \"\"\"{message}\"\"\"

Known so far: {json.dumps(_facts(lead))}

Conversation so far:
{_transcript(lead)}

Return JSON with these keys (use null when not stated or unclear; never guess):
- student_name (string)
- year (number: the student's school year)
- subject (string: exactly what they want tutoring in, e.g. "GCSE Maths" or "A-Level English")
- current_grade (string)
- target_grade (string)
- motivation (short string: why they need help, or by when)
- pricing_interest (true/false: they asked about or discussed price)
- other_facts (object of short label -> value for anything else useful, e.g. exam board, location, availability, online or in-person, areas of weakness, start date)
- outcome ("accepted_consultation" ONLY if Nova already invited them to a consultation and they now agree; "declined" if they clearly say they are not interested or want to stop; otherwise "continuing")
- questions (list of questions they asked)"""
    return _json("You extract structured facts from customer messages. Output JSON only.", prompt)


# ---------------------------------------------------------------
# 5. ANSWER THE CUSTOMER (grounded in the profile)
# ---------------------------------------------------------------
def draft_reply(profile, lead, message, qualified=False):
    status = lead.get("status")
    if status == "CONSULTATION REQUESTED":
        hint = ("The customer ACCEPTED the free consultation. This is the FINAL message: thank them, say a team "
                "member will confirm the exact time based on tutor availability. Do NOT confirm a booking or a time.")
    elif status == "CLOSED":
        hint = ("The customer is not interested right now. This is the FINAL message: thank them politely, "
                "leave the door open, do not push.")
    elif status == "NOT A FIT":
        hint = ("The business cannot help with what they need. This is the FINAL message: say so politely and "
                "honestly, without pretending to offer it. Do not try to sell anything else.")
    elif status == "NEEDS HUMAN":
        hint = ("This conversation is being handed to a team member. This is the FINAL message: say a team member "
                "will be in touch. Do not make any promises.")
    elif qualified:
        hint = ("The lead is QUALIFIED: gently move toward the business's goal from the profile "
                "(for example inviting them to the free consultation). Do not confirm any specific time or slot; "
                "say exact options are confirmed based on availability.")
    else:
        hint = ("Do not push for the goal yet. If key qualification information is missing, ask for ONE or TWO "
                "of the most useful missing items naturally.")
    prompt = f"""Reply to the customer's latest message.

LEAD FACTS: {json.dumps(_facts(lead))}

CONVERSATION SO FAR:
{_transcript(lead)}

LATEST CUSTOMER MESSAGE: \"\"\"{message}\"\"\"

{hint}
Answer their questions using ONLY the business profile. Match the tone. Acknowledge what they told you.
If they want something the business does not offer, say so politely and do not pretend otherwise.
Never guarantee results or invent details. If you cannot answer reliably, or it needs a human decision
(discounts, complaints, policy exceptions), set needs_human true.
Keep it under 120 words.

Return JSON: {{"reply": "message text", "needs_human": true/false, "reason": "why, if needs_human"}}"""
    return _json(_system(profile), prompt)


# ---------------------------------------------------------------
# 6. GUARDRAIL CHECK (review a draft before a human sees it)
# ---------------------------------------------------------------
def check_guardrails(profile, draft):
    prompt = f"""Review this draft customer message against the business profile and rules.

DRAFT: \"\"\"{draft}\"\"\"

Flag anything that: states a price/availability/service/policy not in the profile, guarantees an outcome,
offers an unauthorised discount, confirms a booking that has not happened, breaks the profile's guardrails,
or presents an assumption as fact.

Return JSON: {{"ok": true/false, "issues": ["short description", ...]}}"""
    return _json(_system(profile), prompt)


if __name__ == "__main__":
    # Quick self-test: python agent.py
    demo_profile = {"name": "Nova Tutors", "pricing": "£30 per hour", "guardrails": "Never guarantee grades"}
    print(check_guardrails(demo_profile, "We guarantee a grade 7 for just £20 an hour!"))