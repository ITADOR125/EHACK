# Nova AI Agent

Nova is an AI customer-growth agent demo for small businesses. This proof of concept uses Nova Tutors, a fictional tutoring business, and three prospective customers with different outcomes. Nova uses confirmed business information and lead-specific conversation history to understand customer needs, extract facts, classify service fit, recommend a next action, and prepare a customer-facing draft.

Nova is not a verified tutor-scheduling or booking engine.

## Purpose

The demo explores how an AI agent can support the early stages of a customer enquiry while keeping business rules, evidence, and human review visible. It distinguishes information extraction from qualification and decision-making: Groq extracts candidate facts, while Python rules determine the proposed lead outcome and message.

## Architecture and decision-making process

1. **Input:** The confirmed `BUSINESS` profile, one lead record, and that lead's conversation messages (`customer` / `agent`). Lead records and their conversation histories must remain isolated.
2. **Groq extraction:** For the latest customer message, `groq_extract()` requests JSON containing candidate `facts` and verbatim `quotes`. Groq does not directly decide qualification or update persistent state in V3.
3. **Validation and update proposal:** `safe_patch()` checks allowed field names, quoted evidence, normalization, and changed values. The resulting `extracted_information` is a proposed delta. `apply_extraction()` creates a proposed updated lead from that delta.
4. **Python qualification and guardrails:** `service_fit()`, `explicit_intent()`, `missing_information()`, `question_kind()`, and `decide_next_action()` apply business eligibility, customer needs, interest, and safety rules. In V3, Python templates produce the customer-facing message using the lead and business data.
5. **Structured decision:** `decide_next_action(business, lead, conversation)` returns a decision containing `lead_status`, `next_action`, `message`, `reason`, `qualification`, `missing_information`, `extracted_information`, `updated_lead`, `review_status`, `requires_human_approval`, and `escalation`.
6. **Human control:** Initial outreach, consultation arrangements, and unverified matters require review where flagged. A decision proposes an action; it does not itself send a real message, route a review to a person, or confirm a booking.

## Three demo journeys

| Lead | What Nova knows | Expected decision | Why |
| --- | --- | --- | --- |
| **Sarah Johnson** | Daniel, Year 11, GCSE Maths; grade 4 to 6, Edexcel Higher; interested in a free consultation. | `qualified` + `recommend_consultation` after explicit interest. | Supported service, real need, and sufficient interest. |
| **Rachel Thompson** | Oliver, Year 10, exam-technique challenges, Edexcel Maths; questions about price, tutor suitability, and progress. | `consultation_needed` + a price answer or consultation recommendation. | Suitable service, with questions that may need discussion. |
| **James Carter** | Wants university-level Calculus and Linear Algebra tutoring. | `not_qualified` + `close_lead`. | University subject tutoring is not offered. This is distinct from university admissions or application support. |

## Eligibility and guardrails

- GCSE Maths and the specified GCSE Sciences are supported. The confirmed rate is **£30 per 60-minute session**.
- A-Level subjects and prices, and the price for university admissions or application support, are **not confirmed**. Do not invent a price or claim coverage.
- University-level Maths tutoring is **unsupported**. Do not conflate it with university admissions support.
- Online tutoring may be considered UK-wide. In-person tutoring requires the customer's location, tutor location, and verified tutor availability, particularly outside selected London areas.
- Do not guarantee grades, tutor availability, prices for unconfirmed services, discounts, message delivery, or bookings.
- A consultation is a **free 15-minute conversation**. Do not describe it as booked until the backend confirms it.
- Agent messages remain drafts or proposals until the actual workflow confirms approval and sending.
- An escalation with `status: requested_not_routed` is not proof that a human was notified.

## State and limitations

V3's terminal app stores separate sessions in `data/sessions.json` through `load_sessions()` and `save_sessions()`. This is local demo persistence, not MongoDB. `/approve` simulates approval only.

The application does not currently provide a verified real-time tutor calendar, consultation booking, external message delivery, or human-review routing. Groq integration with a deployed website must be verified separately by checking the network request, backend endpoint, and logs.

## Reproduce offline tests

Run the offline test suite with:

```powershell
python -m unittest -v test_brain.py
```

The supplied V3 test report records **16 offline tests passing**. These tests use `extraction_override` to bypass Groq, so they exercise Python rules but do not prove live Groq inference or frontend/backend integration.

## Repository

[ITADOR125/EHACK on GitHub](https://github.com/ITADOR125/EHACK)
