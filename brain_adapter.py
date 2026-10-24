"""Proposal-only bridge for canonical backend JSON and Fatima's brain.

No HTTP, database, safety evaluation, delivery, or local session storage occurs
here. Messages must be supplied in backend chronological order. Every result
still requires backend validation and safety checks before any execution.
"""
from copy import deepcopy
import math
import re

import brain


FIELD_MAP = {
    "student_name": "student.name", "reason": "need",
    "current_grade": "currentGrade", "target_grade": "targetGrade",
    "exam_board": "examBoard", "tier": "tier", "subject": "subject",
    "year": "year", "customer_location": "location",
    "delivery_preference": "preferredFormat",
}
STATUS_MAP = {
    "new": "new", "awaiting_approval": "new", "contacted": "needs_information",
    "responded": "needs_information", "needs_information": "needs_information",
    "qualified": "qualified", "consultation_needed": "consultation_needed",
    "not_qualified": "not_qualified", "not_a_fit": "not_qualified",
}
MATHS_SERVICES = {"gcse maths", "gcse maths tutoring", "gcse mathematics tutoring"}


def _format(value):
    if not value:
        return None
    text = str(value).lower()
    if any(term in text for term in ("in-person", "in person", "face to face", "in_person")):
        return "in_person"
    return "online" if "online" in text else None


def to_brain_inputs(business, lead, messages):
    """Map canonical records without changing them; retain owner notes separately.

    Owner notes are neither customer facts nor evidence of customer intent, and
    are never interpreted as permission. Unknown roles/statuses fail explicitly.
    """
    if business["id"] != lead["businessId"]:
        raise ValueError("Lead does not belong to the supplied business")
    status = str(lead["status"]).strip().lower().replace(" ", "_")
    if status not in STATUS_MAP:
        raise ValueError("Unsupported or terminal backend status: " + status)

    warnings = [
        "Brain service rules and response templates are hardcoded; backend business facts and safety remain authoritative.",
        "Brain qualification is a proposal and may not satisfy backend required fields or decision rules.",
    ]
    services = business["services"]
    demo_maths = business["id"] == "nova-tutors" and any(
        service["name"].strip().lower() in MATHS_SERVICES for service in services
    )
    # Only the existing demo service has an established alias/currency convention.
    # Do not import brain.BUSINESS: it would add unconfirmed services and policies.
    prices = [s["price"] for s in services if demo_maths
              and s["name"].strip().lower() in MATHS_SERVICES
              and s["priceUnit"] == "hour"]
    price = prices[0] if prices and all(p == prices[0] for p in prices) else None
    if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float))
                              or not math.isfinite(price) or price < 0):
        raise ValueError("Invalid demo service price")
    if price is None:
        warnings.append("No unambiguous hourly GCSE Maths price can be mapped to the brain's single GBP price field.")
    mapped_business = {
        "id": business["id"], "name": business["name"],
        "services": ["GCSE Maths" if demo_maths and s["name"].strip().lower() in MATHS_SERVICES
                     else s["name"] for s in services],
        "tone": business["tone"], "restrictions": deepcopy(business["restrictions"]),
        "qualificationRules": deepcopy(business["qualificationRules"]),
        "gcse_price_gbp": price,
    }
    subject = lead["subject"]
    if demo_maths and subject.strip().lower() in MATHS_SERVICES:
        subject = "GCSE Maths"
    elif (demo_maths and subject.strip().lower() in {"maths", "mathematics"}
          and re.search(r"\bgcse\b", lead["need"], re.I)):
        subject = "GCSE Maths"
    mapped_lead = {
        "id": lead["id"], "businessId": lead["businessId"], "name": lead["name"],
        "student_name": lead["student"]["name"], "reason": lead["need"],
        "subject": subject, "year": lead["year"],
        "current_grade": lead["currentGrade"], "target_grade": lead["targetGrade"],
        "exam_board": lead["examBoard"], "tier": lead["tier"],
        "customer_location": lead["location"],
        "delivery_preference": _format(lead["preferredFormat"]),
        "lead_status": STATUS_MAP[status], "intent_confirmed": False,
    }
    if lead["preferredFormat"] and mapped_lead["delivery_preference"] is None:
        warnings.append("Unrecognized preferredFormat was left unknown rather than guessed.")
    conversation, owner_messages = [], []
    for message in messages:
        if message["leadId"] != lead["id"]:
            raise ValueError("Conversation contains a message for another lead")
        if not isinstance(message["content"], str):
            raise ValueError("Message content must be text")
        sender = message["sender"]
        if sender == "owner":
            owner_messages.append(deepcopy(message))
        elif sender in ("nova", "customer"):
            conversation.append({"role": "agent" if sender == "nova" else "customer",
                                 "content": message["content"]})
        else:
            raise ValueError("Unsupported backend message sender: " + str(sender))
    if owner_messages:
        warnings.append("Owner messages excluded from reasoning; retained as ownerMessages context only.")
    return {"business": mapped_business, "lead": mapped_lead, "conversation": conversation,
            "ownerMessages": owner_messages, "warnings": warnings}


def decision_to_proposal(business, lead, decision, *, owner_messages=None, warnings=None):
    """Convert proposed changes to backend field names, never to an approval.

    Unrepresentable extracted values are retained separately rather than coerced
    (notably target grade '7+' versus the backend's numeric targetGrade).
    """
    if decision["lead_id"] != lead["id"] or business["id"] != lead["businessId"]:
        raise ValueError("Decision identity does not match the canonical records")
    notes = list(warnings or [])
    updates = {}
    unmapped = {}
    for field, value in decision["extracted_information"].items():
        target = FIELD_MAP.get(field)
        if target is None:
            unmapped[field] = deepcopy(value)
        elif field in ("current_grade", "target_grade") and not (
            value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)
                              and math.isfinite(value))
        ):
            unmapped[field] = deepcopy(value)
        elif field == "student_name":
            updates["student"] = {**deepcopy(lead["student"]), "name": value}
        else:
            updates[target] = deepcopy(value)
    if unmapped:
        notes.append("Some extracted facts cannot be represented by the existing Lead interface; see unmappedInformation.")
    # Use only extracted changes: do not write input aliases such as Maths → GCSE Maths back.
    updates["status"] = decision["lead_status"]
    updates["nextAction"] = decision["next_action"]
    escalation = None
    if decision["escalation"]:
        topic = decision["escalation"]["topic"]
        escalation = {
            "leadId": lead["id"], "issue": topic, "reason": decision["reason"],
            "context": ["Proposed action: " + decision["next_action"],
                        "Customer request concerns: " + str(lead["subject"])],
            "recommendedAction": "Ask the owner to verify " + topic + " before making a commitment.",
            "routingStatus": decision["escalation"]["status"],
        }
    return {
        "businessId": business["id"], "leadId": lead["id"],
        "action": decision["next_action"], "reason": decision["reason"],
        "proposedLeadUpdates": updates,
        "proposedMessage": {"leadId": lead["id"], "sender": "nova", "content": decision["message"]}
        if decision["message"] else None,
        "qualification": deepcopy(decision["qualification"]),
        "missingInformation": [FIELD_MAP.get(field, field) for field in decision["missing_information"]],
        "brainRequiresHumanApproval": decision["requires_human_approval"],
        "reviewStatus": decision["review_status"], "escalation": escalation,
        "unmappedInformation": unmapped,
        "brainState": {"intent_confirmed": decision["updated_lead"].get("intent_confirmed", False)},
        "ownerMessages": deepcopy(owner_messages or []), "warnings": notes,
        "requiresSafetyCheck": True, "executionStatus": "not_executed",
    }


def propose(business, lead, messages, *, client=None, extraction_override=None):
    """Canonical records → brain → proposal. Empty history requests an outreach draft.

    Existing histories must end with a customer event; do not reinterpret an
    owner note or a completed agent turn as a new customer message/outreach.
    """
    inputs = to_brain_inputs(business, lead, messages)
    if messages and messages[-1]["sender"] != "customer":
        raise ValueError("A new customer message is required; owner/agent messages do not trigger a turn")
    latest = inputs["conversation"][-1]["content"] if inputs["conversation"] else ""
    if (brain.question_kind(latest, inputs["lead"]["subject"]) == "known_gcse_price"
            and inputs["business"]["gcse_price_gbp"] is None):
        raise ValueError("Cannot propose a GCSE price answer without a confirmed hourly demo price")
    decision = brain.decide_next_action(
        inputs["business"], inputs["lead"], inputs["conversation"],
        client=client, extraction_override=extraction_override,
    )
    return decision_to_proposal(business, lead, decision,
                                owner_messages=inputs["ownerMessages"], warnings=inputs["warnings"])
