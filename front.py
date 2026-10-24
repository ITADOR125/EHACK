import json
import re
import streamlit as st

st.set_page_config(page_title="Nova", page_icon="✨", layout="wide")

# ---------------------------------------------------------------
# 1. WHAT NOVA NEEDS TO LEARN
# (key, section, label, question, level, required)
# level: 1 = Quick, 2 = Recommended, 3 = Deep
# ---------------------------------------------------------------
FIELDS = [
    ("name", "Business", "Business name",
     "Hi, I'm Nova. I'm going to learn how your business works so I can help you find and win customers. What's your business called?", 1, True),
    ("description", "Business", "Description",
     "Nice to meet you. In a sentence or two, what does {name} do?", 1, True),
    ("location", "Business", "Location",
     "Where do you operate? A city, a region, online, or a mix?", 2, False),
    ("services", "Services", "Services offered",
     "What services or products do you offer?", 1, True),
    ("unsupported", "Services", "Services NOT offered",
     "Is there anything people might ask for that you do NOT offer?", 2, False),
    ("pricing", "Pricing", "Pricing",
     "How do you price things? Include any rules, like different prices for different services.", 1, True),
    ("ideal_customer", "Customers", "Ideal customer",
     "Who is your ideal customer?", 1, True),
    ("qualification", "Qualification", "Qualification info",
     "What information do you normally need before deciding whether someone is a good fit?", 1, True),
    ("goal", "Goal", "Desired outcome",
     "What would you ultimately like me to help you achieve with a potential customer? For example: book a consultation, get a quote, make a sale.", 1, True),
    ("tone", "Tone", "Customer-facing tone",
     "How should I sound when I talk to your customers?", 1, True),
    ("guardrails", "Guardrails", "Never say / promise / do",
     "Is there anything I should never say, promise or do when speaking to a potential customer?", 1, True),
    ("approval", "Approval rules", "Approval and escalation",
     "What should I check with you before doing, and when should I hand over to a human?", 1, True),
    ("faqs", "Knowledge", "FAQs",
     "What questions do customers ask you most often, and how do you answer them?", 2, False),
    ("availability", "Knowledge", "Availability",
     "What are your operating hours and availability rules?", 2, False),
    ("policies", "Knowledge", "Policies",
     "Are there any policies customers should know about (cancellations, refunds, etc.)?", 3, False),
    ("objections", "Knowledge", "Common objections",
     "What reasons do customers give for hesitating, and how do you usually respond?", 3, False),
]
FIELD_BY_KEY = {f[0]: f for f in FIELDS}
SECTIONS = ["Business", "Services", "Pricing", "Customers", "Qualification",
            "Goal", "Tone", "Guardrails", "Approval rules", "Knowledge"]

MODES = {
    "Quick setup (about 3 min)": 1,
    "Recommended setup (about 5 min)": 2,
    "Deep setup (10+ min)": 3,
}

# One-click demo data from the Nova Tutors case study
DEMO = {
    "name": "Nova Tutors",
    "description": "Small independent tutoring company offering personalised one-to-one GCSE tutoring.",
    "location": "London, plus online across the UK",
    "services": "GCSE Maths, Biology, Chemistry, Physics and Combined Science",
    "unsupported": "English, History, Geography, Languages, Computer Science, A-Level, university, primary school, SATs",
    "pricing": "£30 per hour (60 min sessions). Free 15-minute initial consultation.",
    "ideal_customer": "Parents or guardians of Year 10 and 11 students who want extra GCSE Maths or Science support.",
    "qualification": "Student year, subject, current grade, target grade, areas of weakness, exam board, online or in-person, location, availability.",
    "goal": "Book a free 15-minute consultation.",
    "tone": "Friendly, reassuring and professional.",
    "guardrails": "Never guarantee grades. Never invent prices, availability or services. Never offer unauthorised discounts. Never confirm a booking that has not happened.",
    "approval": "Human approval for first outreach, discounts, complaints, policy exceptions and anything outside known information.",
    "faqs": "Sessions are 60 minutes. Online tutoring is available across the UK.",
    "availability": "Mon-Fri 4-8pm, Sat 10am-5pm, Sun 10am-4pm. Exact tutor availability varies.",
    "policies": "",
    "objections": "",
}

UNSURE_PHRASES = {"i don't know", "i dont know", "idk", "not sure", "dont know", "don't know", "no idea"}


# ---------------------------------------------------------------
# 2. SESSION STATE
# ---------------------------------------------------------------
def init_state():
    defaults = {
        "stage": "start",      # start -> chat -> review -> active
        "level": 2,
        "messages": [],
        "profile": {},         # key -> text
        "unsure": set(),       # keys the owner didn't know
        "lead": None,          # the current lead (Sarah Johnson)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def active_fields():
    return [f for f in FIELDS if f[4] <= st.session_state.level]


def next_field():
    """First field in the active setup that hasn't been answered yet."""
    for f in active_fields():
        if f[0] not in st.session_state.profile and f[0] not in st.session_state.unsure:
            return f
    return None


def ask(field):
    q = field[3].format(name=st.session_state.profile.get("name", "your business"))
    st.session_state.messages.append({"role": "assistant", "content": q})


# ---------------------------------------------------------------
# 3. ANSWER HANDLING
# TODO (AI teammate): replace this with a real LLM call that extracts
# MULTIPLE fields from one answer and returns a dict like
# {"services": "...", "pricing": "..."}. For now, one answer = one field.
# ---------------------------------------------------------------
def handle_answer(text):
    field = next_field()
    if field is None:
        return
    key = field[0]
    if text.strip().lower() in UNSURE_PHRASES:
        st.session_state.unsure.add(key)
    else:
        st.session_state.profile[key] = text.strip()
        st.session_state.unsure.discard(key)

    nxt = next_field()
    if nxt:
        ask(nxt)
    else:
        st.session_state.messages.append(
            {"role": "assistant", "content": "That's everything I need for now. Let me show you what I've learned."}
        )
        st.session_state.stage = "review"


# ---------------------------------------------------------------
# 4. PROFILE PANEL (right side)
# ---------------------------------------------------------------
def field_state(key):
    if key in st.session_state.profile:
        return "done"
    if key in st.session_state.unsure:
        return "unsure"
    return "learning"


def render_profile(compact=False):
    st.subheader(st.session_state.profile.get("name", "Your business"))
    current = next_field()
    fields = active_fields()
    for section in SECTIONS:
        sec_fields = [f for f in fields if f[1] == section]
        if not sec_fields:
            continue
        st.markdown(f"**{section}**")
        for f in sec_fields:
            state = field_state(f[0])
            if state == "done":
                icon, text = "✅", st.session_state.profile[f[0]]
                if not compact and len(text) > 90:
                    text = text[:90] + "…"
            elif state == "unsure":
                icon, text = "❗", "Needs clarification"
            else:
                is_now = current is not None and current[0] == f[0]
                icon, text = ("🔵", "Learning…") if is_now else ("⚪", "Not asked yet")
            st.markdown(f"{icon} **{f[2]}**: {text}")


def progress_bar():
    fields = [f for f in active_fields() if f[5]]
    done = sum(1 for f in fields if f[0] in st.session_state.profile)
    st.progress(done / len(fields) if fields else 0,
                text=f"Required info: {done}/{len(fields)}")


# ---------------------------------------------------------------
# 5. SCREENS
# ---------------------------------------------------------------
def screen_start():
    st.title("✨ Nova")
    st.write("Teach Nova how your business works. It takes a few minutes and feels like a chat, not a form.")
    mode = st.radio("How detailed do you want to go?", list(MODES.keys()), index=1)
    st.caption("You can always teach Nova more later.")
    c1, c2 = st.columns(2)
    if c1.button("Start", type="primary"):
        st.session_state.level = MODES[mode]
        st.session_state.stage = "chat"
        ask(next_field())
        st.rerun()
    if c2.button("Skip with Nova Tutors demo data"):
        st.session_state.level = MODES[mode]
        st.session_state.profile = {k: v for k, v in DEMO.items() if v}
        st.session_state.stage = "review"
        st.rerun()


def screen_chat():
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.title("✨ Nova")
        progress_bar()
        box = st.container(height=480)
        with box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"], avatar="✨" if m["role"] == "assistant" else None):
                    st.write(m["content"])
        prompt = st.chat_input("Type your answer (or say 'I don't know')")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            handle_answer(prompt)
            st.rerun()

    with right:
        with st.container(border=True):
            render_profile()


def screen_review():
    st.title("I've learned your business")
    st.write("Check what I've learned. Fix anything that's wrong, then activate me.")

    with st.container(border=True):
        render_profile(compact=True)

    st.divider()
    with st.expander("Edit something"):
        labels = {f[2]: f[0] for f in active_fields()}
        choice = st.selectbox("What do you want to change?", list(labels.keys()))
        key = labels[choice]
        new_val = st.text_area("New answer", value=st.session_state.profile.get(key, ""), key=f"edit_{key}")
        if st.button("Save change"):
            if new_val.strip():
                st.session_state.profile[key] = new_val.strip()
                st.session_state.unsure.discard(key)
                st.rerun()

    missing = [f[2] for f in active_fields() if f[5] and f[0] not in st.session_state.profile]
    if missing:
        st.warning("Nova can't activate yet. Still needed: " + ", ".join(missing))

    if st.button("Looks good: Activate Nova", type="primary", disabled=bool(missing)):
        save_profile()
        st.session_state.stage = "active"
        st.rerun()


def save_profile():
    """TODO (backend teammate): save to MongoDB instead of a local file.

    from pymongo import MongoClient
    client = MongoClient("YOUR_MONGO_URI")
    client.nova.business_profiles.replace_one({"name": ...}, doc, upsert=True)
    """
    doc = {
        "profile": st.session_state.profile,
        "onboarding": {"mode": st.session_state.level, "completed": True, "confirmedByOwner": True},
    }
    with open("nova_profile.json", "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------
# 5b. LEADS: dashboard, lead view, outreach, qualification
# TODO (AI teammate): everything marked MOCK below should become LLM calls
# that use the stored business profile (and MongoDB knowledge retrieval).
# ---------------------------------------------------------------
STATUS_ICON = {"NEW": "🆕", "CONTACTED": "📤", "RESPONDED": "💬", "QUALIFIED": "✅", "CONSULTATION OFFERED": "📅"}

SARAH_REPLY = ("Hi, thanks for reaching out. He's currently getting around a 4 and needs a 6 "
               "for sixth form. How much would tutoring be?")


def new_lead():
    return {
        "parent": "Sarah Johnson", "student": "Daniel", "year": 11, "subject": "GCSE Maths",
        "problem": "Daniel needs additional Maths support.",
        "current_grade": None, "target_grade": None, "motivation": None, "pricing_interest": False,
        "status": "NEW", "thread": [], "answer_sent": False,
    }


def assess(lead, profile):
    """MOCK lead analysis. Returns HIGH / MEDIUM / UNKNOWN for each dimension."""
    services = profile.get("services", "").lower()
    subject_ok = "maths" in services and "maths" in lead["subject"].lower()
    return {
        "Service fit": "HIGH" if subject_ok else "UNKNOWN",
        "Need": "HIGH" if lead["current_grade"] and lead["target_grade"] else ("MEDIUM" if lead["problem"] else "UNKNOWN"),
        "Urgency": "HIGH" if lead["motivation"] else "UNKNOWN",
        "Intent": "HIGH" if lead["pricing_interest"] else "UNKNOWN",
    }


def draft_outreach(lead, profile):
    """MOCK outreach. Should use business knowledge + lead + goal + tone + guardrails."""
    biz = profile.get("name", "our team")
    return (
        f"Hi {lead['parent'].split()[0]},\n\n"
        f"I'm getting in touch from {biz}. I understand {lead['student']} is in Year {lead['year']} "
        f"and could use some extra support with {lead['subject']}. We offer personalised one-to-one "
        f"tutoring that focuses on exactly where a student needs the most help.\n\n"
        f"If it would be useful, we can set up a free 15-minute consultation to talk through where "
        f"{lead['student']} is at and what would help. Would you like to hear more?\n\n"
        f"Kind regards,\n{biz}"
    )


def extract_reply_info(lead, text):
    """MOCK information extraction from the customer's reply."""
    t = text.lower()
    cur = re.search(r"getting (?:around )?(?:a |an )?(\d)", t)
    tgt = re.search(r"needs (?:a |an )?(\d)", t)
    if cur:
        lead["current_grade"] = cur.group(1)
    if tgt:
        lead["target_grade"] = tgt.group(1)
    if "sixth form" in t:
        lead["motivation"] = f"Needs Grade {lead['target_grade'] or '?'} for sixth form"
    if "how much" in t or "price" in t or "cost" in t:
        lead["pricing_interest"] = True


def draft_answer(lead, profile):
    """MOCK knowledge retrieval. Must use stored pricing and never guess."""
    pricing = profile.get("pricing")
    if not pricing:
        return None
    return (
        f"Hi {lead['parent'].split()[0]}, thanks for getting back to me, that's really helpful. "
        f"Knowing {lead['student']} is on a {lead['current_grade']} and aiming for a {lead['target_grade']} "
        f"helps us plan the right support.\n\n"
        f"On pricing: {pricing}\n\n"
        f"Would you like to find out more before deciding?"
    )


def draft_consultation(lead):
    return (
        f"Hi {lead['parent'].split()[0]}, the best next step is our free 15-minute consultation. "
        f"We'll look at where {lead['student']} is now, what he needs to reach his target, and "
        f"what availability works for you. We'll confirm exact times based on tutor availability. "
        f"Would you like to book one?"
    )


def screen_active():
    st.title(f"✨ Nova is live for {st.session_state.profile.get('name', 'your business')}")
    lead = st.session_state.lead
    c1, c2, c3 = st.columns(3)
    c1.metric("Leads", 1 if lead else 0)
    c2.metric("Awaiting your approval", 1 if lead and lead["status"] == "NEW" else 0)
    c3.metric("Qualified", 1 if lead and lead["status"] in ("QUALIFIED", "CONSULTATION OFFERED") else 0)

    st.subheader("Leads")
    if lead is None:
        st.info("No leads yet. Add one to see what Nova can do.")
        if st.button("Add demo lead: Sarah Johnson", type="primary"):
            st.session_state.lead = new_lead()
            st.rerun()
    else:
        with st.container(border=True):
            a, b, c, d = st.columns([3, 2, 2, 1])
            a.markdown(f"**{lead['parent']}**  \nParent of {lead['student']}, Year {lead['year']}")
            b.write(lead["subject"])
            c.write(f"{STATUS_ICON[lead['status']]} {lead['status']}")
            if d.button("Open"):
                st.session_state.stage = "lead"
                st.rerun()

    with st.expander("Stored business profile"):
        st.json(st.session_state.profile)
    if st.button("Start over"):
        st.session_state.clear()
        st.rerun()


def screen_lead():
    lead = st.session_state.lead
    profile = st.session_state.profile
    if st.button("← Back to dashboard"):
        st.session_state.stage = "active"
        st.rerun()
    st.title(f"{lead['parent']}  {STATUS_ICON[lead['status']]} {lead['status']}")

    left, right = st.columns([3, 2], gap="large")

    # ---- right: what Nova knows about this lead ----
    with right:
        with st.container(border=True):
            st.markdown("**Lead summary**")
            st.markdown(f"Parent of **{lead['student']}**, Year {lead['year']}, {lead['subject']}")
            st.markdown(f"Known problem: {lead['problem']}")
            st.markdown(f"Current grade: **{lead['current_grade'] or 'Unknown'}**")
            st.markdown(f"Target grade: **{lead['target_grade'] or 'Unknown'}**")
            st.markdown(f"Motivation: {lead['motivation'] or 'Unknown'}")
            st.markdown(f"Asked about pricing: {'Yes' if lead['pricing_interest'] else 'Not yet'}")
        with st.container(border=True):
            st.markdown("**Lead assessment**")
            for k, v in assess(lead, profile).items():
                icon = {"HIGH": "🟢", "MEDIUM": "🟡", "UNKNOWN": "⚪"}[v]
                st.markdown(f"{icon} {k}: **{v}**")

    # ---- left: the journey ----
    with left:
        for who, text in lead["thread"]:
            with st.chat_message("assistant" if who == "Nova" else "user", avatar="✨" if who == "Nova" else None):
                st.write(text)

        status = lead["status"]

        if status == "NEW":
            st.markdown("**Outreach draft (needs your approval)**")
            text = st.text_area("Edit the message if you like", value=draft_outreach(lead, profile), height=260)
            if st.button("Approve and send (simulated)", type="primary"):
                lead["thread"].append(("Nova", text))
                lead["status"] = "CONTACTED"
                st.rerun()

        elif status == "CONTACTED":
            st.caption("Waiting for Sarah to reply.")
            if st.button("Simulate Sarah's reply", type="primary"):
                lead["thread"].append(("Sarah", SARAH_REPLY))
                extract_reply_info(lead, SARAH_REPLY)
                lead["status"] = "RESPONDED"
                st.rerun()

        elif status == "RESPONDED":
            if not lead["answer_sent"]:
                answer = draft_answer(lead, profile)
                if answer is None:
                    st.error("Nova doesn't have pricing information, so it can't answer. Needs human input.")
                else:
                    st.markdown("**Nova's suggested reply**")
                    text = st.text_area("Edit the message if you like", value=answer, height=240)
                    if st.button("Send reply (simulated)", type="primary"):
                        lead["thread"].append(("Nova", text))
                        lead["answer_sent"] = True
                        st.rerun()
            else:
                scores = assess(lead, profile)
                st.caption("Nova checks whether it knows enough to qualify this lead.")
                if st.button("Assess lead", type="primary"):
                    if all(v == "HIGH" for v in scores.values()):
                        lead["status"] = "QUALIFIED"
                    st.rerun()

        elif status == "QUALIFIED":
            st.success("Sarah is qualified. Next step: move her towards the free consultation.")
            text = st.text_area("Suggested message", value=draft_consultation(lead), height=200)
            if st.button("Send consultation invite (simulated)", type="primary"):
                lead["thread"].append(("Nova", text))
                lead["status"] = "CONSULTATION OFFERED"
                st.rerun()

        else:
            st.success("Demo journey complete: onboarded, analysed, contacted, answered, qualified and invited to a consultation.")


# ---------------------------------------------------------------
# 6. ROUTER
# ---------------------------------------------------------------
init_state()
{
    "start": screen_start,
    "chat": screen_chat,
    "review": screen_review,
    "active": screen_active,
    "lead": screen_lead,
}[st.session_state.stage]()