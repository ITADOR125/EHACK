import json
import re
import streamlit as st

try:
    import agent
except Exception:  # groq not installed
    agent = None

st.set_page_config(page_title="Nova", page_icon="✨", layout="wide")

# A calmer, more intentional workspace for Nova. The app remains fully
# Streamlit-native so the chat, forms, and buttons keep their usual behavior.
st.markdown("""
<style>
:root { color-scheme:light; --ink:#18221f; --muted:#52635a; --green:#126448; --mint:#e8f5ef; --line:#dce6df; --paper:#fbfcfa; }
html, body, [class*="css"], .stApp { font-family:Inter, 'Segoe UI', Arial, sans-serif; color:var(--ink) !important; }
.stApp { background:var(--paper); }
[data-testid="stAppViewContainer"] { background:var(--paper); }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
label, .stRadio p, .stCheckbox p, .stSelectbox p { color:var(--ink) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:var(--muted) !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] div { color:#18221f !important; }
[data-testid="stHeader"] { background:#fbfcfa !important; }
[data-testid="stSidebar"] { background:#f1f6f2; border-right:1px solid var(--line); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label { color:#26382f !important; }
.block-container { width:100% !important; max-width:1200px !important; margin-left:auto !important; margin-right:auto !important; box-sizing:border-box; padding:1.7rem clamp(1rem, 2.5vw, 2.25rem) 3rem !important; }
[data-testid="stColumn"], [data-testid="stHorizontalBlock"] { min-width:0 !important; }
h1,h2,h3,h4 { font-family:Inter, 'Segoe UI', Arial, sans-serif !important; letter-spacing:-.035em; color:var(--ink) !important; }
h1 { font-size:2.35rem !important; font-weight:800 !important; }
h2 { font-size:1.6rem !important; font-weight:750 !important; }
p, label { line-height:1.65; }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 18px; box-shadow:0 5px 18px rgba(25,50,38,.035); }
[data-testid="stMetricLabel"] { color:var(--muted); }
[data-testid="stMetricValue"] { font-family:Inter, 'Segoe UI', Arial, sans-serif; font-weight:800; }
[data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] * { color:var(--ink) !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; border-radius:18px !important; background:#fff; box-shadow:0 7px 24px rgba(25,50,38,.035); }
.stButton>button { border-radius:11px; min-height:2.65rem; font-weight:700; border:1px solid #cbd9d0 !important; background:#ffffff !important; color:#18221f !important; transition:all .16s ease; }
.stButton>button[kind="primary"] { background:var(--green) !important; border-color:var(--green) !important; }
.stButton>button[kind="primary"], .stButton>button[kind="primary"] * { color:#fff !important; }
.stButton>button:hover { transform:translateY(-1px); border-color:#9bb9a7; }
[data-testid="stChatMessage"] { border:1px solid var(--line); border-radius:16px; padding:1rem 1.15rem; background:white; }
[data-testid="stChatMessage"] *, [data-testid="stVerticalBlockBorderWrapper"] *, [data-testid="stExpander"] * { color:var(--ink) !important; }
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { background:var(--mint); border-color:#d5e9dd; }
[data-testid="stChatInput"] textarea, [data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input { border-radius:12px; }
[data-testid="stChatInput"] textarea, [data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input,
[data-testid="stSelectbox"] input { color:#18221f !important; background:#fff !important; caret-color:#126448; }
[data-testid="stTextArea"] textarea:disabled, [data-testid="stTextInput"] input:disabled {
    color:#18221f !important; -webkit-text-fill-color:#18221f !important; opacity:1 !important;
    background:#f7faf8 !important; cursor:default;
}
[data-testid="stChatInput"] textarea::placeholder, [data-testid="stTextArea"] textarea::placeholder,
[data-testid="stTextInput"] input::placeholder { color:#697a71 !important; opacity:1; }
[data-testid="stProgressBar"] > div > div { background:var(--green); }
[data-testid="stExpander"] { border-color:var(--line); border-radius:14px; background:#fff; }
.nova-kicker { color:var(--green); text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:800; margin-bottom:.4rem; }
.nova-hero { border:1px solid #dce9df; border-radius:24px; padding:2.6rem 2.8rem 2.6rem 1.3rem; background:radial-gradient(circle at 90% 5%,#dbf1e6 0,transparent 30%),linear-gradient(135deg,#fff 0%,#f2f8f3 100%); box-shadow:0 12px 38px rgba(25,50,38,.055); margin:.5rem 0 1.4rem; }
.nova-hero h1 { font-size:3rem !important; margin:.1rem 0 .6rem; }
.nova-hero p { color:#586a60; font-size:1.05rem; max-width:680px; }
.nova-pill { display:inline-block; background:#e5f2e9; color:#17684f; border-radius:99px; padding:.38rem .75rem; font-size:.78rem; font-weight:700; }
@media (max-width:800px) { .block-container{padding:1rem 1rem 2rem !important}.nova-hero{padding:1.5rem}.nova-hero h1{font-size:2.3rem !important} }
</style>
""", unsafe_allow_html=True)

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
        "leads": [],           # demo pipeline: Sarah, Rachel, and James
        "activity": [],
        "outreach_draft": "",
        "editing_outreach": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def log_activity(message, kind="info"):
    """Append a human-readable event to the demo activity timeline."""
    st.session_state.setdefault("activity", []).append({"message": message, "kind": kind})


def log_lead_activity(lead, message, kind="info"):
    lead.setdefault("activity", []).append({"message": message, "kind": kind})
    log_activity(message, kind)


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
        st.session_state.profile.update(ai_extract(key, text))
        st.session_state.profile.setdefault(key, text.strip())
        st.session_state.unsure.discard(key)
    log_activity(f"Business profile updated: {field[2]}.", "success")

    nxt = next_field()
    if nxt:
        ask(nxt)
    else:
        st.session_state.messages.append(
            {"role": "assistant", "content": "That's everything I need for now. Let me show you what I've learned."}
        )
        st.session_state.stage = "review"
        log_activity("Onboarding questions complete. Profile is ready for owner review.", "success")


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
    st.markdown('<section class="nova-hero"><div class="nova-kicker">Your customer growth copilot</div><h1>Meet Nova ✨</h1><p>Give Nova the context it needs to represent your business with care. Set up your profile, review what it learned, then try a customer conversation.</p><span class="nova-pill">A guided setup · About 5 minutes</span></section>', unsafe_allow_html=True)
    st.subheader("Set up your workspace")
    st.write("Choose how much detail to share. You can add or change anything later.")
    mode = st.radio("How detailed do you want to go?", list(MODES.keys()), index=1)
    st.caption("Your answers shape Nova’s recommendations and customer replies.")
    c1, c2 = st.columns(2)
    if c1.button("Start", type="primary"):
        st.session_state.level = MODES[mode]
        st.session_state.stage = "chat"
        ask(next_field())
        log_activity("Business onboarding started.")
        st.rerun()
    if c2.button("Skip with Nova Tutors demo data"):
        st.session_state.level = MODES[mode]
        st.session_state.profile = {k: v for k, v in DEMO.items() if v}
        st.session_state.stage = "review"
        log_activity("Nova Tutors demo profile loaded.", "success")
        st.rerun()


def screen_chat():
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown('<div class="nova-kicker">Business setup · Step 1 of 2</div>', unsafe_allow_html=True)
        st.title("Let’s get to know your business")
        st.caption("Answer in your own words. Nova will keep track of what it learns as you go.")
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
    st.markdown('<div class="nova-kicker">Business setup · Step 2 of 2</div>', unsafe_allow_html=True)
    st.title("Your business profile")
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
        log_activity(f"{st.session_state.profile.get('name', 'Business')} profile reviewed and Nova activated.", "success")
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
# 5b. LEADS: dashboard, lead view, outreach, live customer conversation
# You type as the customer. Nova extracts what you say, scores the lead,
# drafts replies (you approve them) and qualifies you when it knows enough.
# ---------------------------------------------------------------
STATUS_ICON = {
    "NEW": "🆕", "AWAITING APPROVAL": "🟠", "CONTACTED": "📤", "RESPONDED": "💬", "QUALIFIED": "✅",
    "CONSULTATION OFFERED": "📅", "CONSULTATION REQUESTED": "🎉", "NOT A FIT": "❌",
    "CONSULTATION NEEDED": "🟡", "CLOSED": "🔒", "NEEDS HUMAN": "🙋",
}
# When the lead reaches one of these, Nova sends one final message and the conversation ends.
TERMINAL = ("CONSULTATION REQUESTED", "CLOSED", "NOT A FIT", "NEEDS HUMAN")
MAX_CUSTOMER_MESSAGES = 10  # safety net: hand over to a human after this many customer messages
LEAD_KEYS = ("subject", "year", "student", "problem", "current_grade", "target_grade", "motivation", "pricing_interest")

UNSUPPORTED_WORDS = ("english", "history", "geography", "french", "spanish", "german", "language",
                     "computer science", "a-level", "a level", "alevel", "primary", "sats", "university")
SUPPORTED_WORDS = ("maths", "math", "biology", "chemistry", "physics", "science")


def new_lead(parent="Sarah Johnson", student="Daniel", year=11, subject="GCSE Maths"):
    return {
        "id": "sarah",
        "parent": parent, "student": student, "year": year, "subject": subject,
        "problem": "Needs additional Maths support.",
        "current_grade": None, "target_grade": None, "motivation": None, "pricing_interest": False,
        "other_facts": {}, "status": "AWAITING APPROVAL", "thread": [],
        "activity": [], "recommended_next_action": "Review and approve the personalized first outreach.",
    }


def rachel_lead():
    return {
        "id": "rachel", "parent": "Rachel Thompson", "student": "Oliver Thompson", "year": 10,
        "age": 15, "relationship": "Parent / Guardian", "location": "Islington, London",
        "subject": "GCSE Mathematics", "problem": "Understands most topics in class but struggles with exam-style questions and applying knowledge under timed conditions.",
        "current_grade": "5", "target_grade": "7 or above",
        "motivation": "Wants extra support before Oliver enters Year 11; hopes to start within 2–3 weeks.",
        "pricing_interest": True, "other_facts": {
            "Exam board": "Edexcel", "Main pain points": "Exam technique; confidence with harder questions; time management; algebra; problem solving",
            "Preferred tutoring": "1-to-1 online", "Preferred availability": "Tuesday or Thursday evenings after 6 PM",
            "Desired start": "Within the next 2–3 weeks", "Budget": "£25–£35 per session",
            "Parent priorities": "Experienced GCSE tutor; clear progress tracking; regular feedback; transparent pricing",
            "Main concern": "Price and whether tutoring will improve Oliver's grades",
            "Lead source": "Website enquiry",
            "Consultation approval": "Owner confirmation required before offering a consultation",
        },
        "status": "RESPONDED", "confirm_fit_after_conversation": True, "candidate_engaged": False, "thread": [
            ("Customer", "Hi, I'm looking for some extra Maths support for my son Oliver who's currently in Year 10. He's doing okay but struggles quite a bit with exam questions. Could you let me know how much your sessions cost and how your tutoring works?")
        ],
        "activity": [
            {"message": "Website enquiry received from Rachel Thompson.", "kind": "info"},
            {"message": "Nova is preparing a first reply and will gather more context before deciding fit or recommending a consultation.", "kind": "info"},
        ],
        "recommended_next_action": "Reply to Rachel's enquiry and learn more before deciding the next step.",
        "consultation_draft": "Hi Rachel, thanks for sharing Oliver's situation. Nova Tutors offers one-to-one GCSE Maths support at £30 per 60-minute session. We can't promise a particular grade outcome, but a free 15-minute consultation with a team member is a good way to discuss exam technique, tutor suitability, progress updates, and what sessions include. Would you like us to arrange one? The team can confirm a time and tutor availability.",
    }


def james_lead():
    return {
        "id": "james", "parent": "James Carter", "student": "James Carter", "year": None,
        "age": 19, "relationship": "Self", "education_level": "First-year university student",
        "location": "Camden, London", "subject": "University Mathematics",
        "problem": "Struggling with university calculus, linear algebra, lecture material, and coursework.",
        "current_grade": None, "target_grade": None,
        "motivation": "Wants weekly private tutoring and would like to start immediately.",
        "pricing_interest": True, "other_facts": {
            "Specific topics": "Calculus; Linear Algebra; Probability", "Preferred tutoring": "1-to-1 online",
            "Preferred availability": "Weekday evenings", "Desired start": "Immediately", "Budget": "£30–£40 per session",
            "Main pain points": "University calculus; linear algebra; understanding lecture material; coursework support",
            "Lead source": "Website enquiry",
        },
        "status": "RESPONDED", "confirm_fit_after_conversation": True, "candidate_engaged": False, "thread": [
            ("Customer", "Hi, I'm a first-year university student looking for a Maths tutor. I'm having trouble with calculus and linear algebra and was wondering if you offer weekly online sessions?"),
        ],
        "activity": [
            {"message": "Website enquiry received from James Carter.", "kind": "info"},
            {"message": "Nova will confirm the level of support James needs before assessing service fit.", "kind": "info"},
        ],
        "recommended_next_action": "Ask James to confirm whether he needs university-level or GCSE-level Mathematics support.",
    }


def demo_lead_by_id(lead_id):
    return {"sarah": new_lead, "rachel": rachel_lead, "james": james_lead}.get(lead_id, new_lead)()


def upsert_demo_lead(lead):
    leads = st.session_state.setdefault("leads", [])
    for index, existing in enumerate(leads):
        if existing.get("id") == lead.get("id"):
            leads[index] = lead
            break
    else:
        leads.append(lead)


def lead_line(lead):
    if lead.get("relationship") == "Self":
        return lead.get("education_level") or "Student enquiry"
    year = f"Year {lead['year']}" if lead.get("year") else "year unknown"
    return f"Parent of {lead.get('student') or 'student'}, {year}"


# ---------- MOCK versions (used when no AI key, or if the AI call fails) ----------
def mock_assess(lead, profile):
    subject = (lead.get("subject") or "").lower()
    if any(w in subject for w in UNSUPPORTED_WORDS):
        fit = "LOW"
    elif any(w in subject for w in SUPPORTED_WORDS):
        fit = "HIGH"
    else:
        fit = "UNKNOWN"
    if lead["current_grade"] and lead["target_grade"]:
        need = "HIGH"
    elif lead["problem"] or lead["current_grade"] or lead["target_grade"]:
        need = "MEDIUM"
    else:
        need = "UNKNOWN"
    customer_msgs = [t for who, t in lead["thread"] if who != "Nova"]
    return {
        "Service fit": fit,
        "Need": need,
        "Urgency": "HIGH" if lead["motivation"] else "UNKNOWN",
        "Intent": "HIGH" if lead["pricing_interest"] else ("MEDIUM" if customer_msgs else "UNKNOWN"),
    }


def normalize_agent_assessment(result):
    """Adapt common structured agent response shapes to Nova's UI contract.

    Supported forms include the current flat agent.py result and a nested
    Fatima-style object such as {assessment: {...}, next_action: ...}.
    Unknown fields are preserved in `raw` for later UI integration.
    """
    result = result if isinstance(result, dict) else {}
    result = result.get("data") or result.get("result") or result
    if not isinstance(result, dict):
        result = {}
    nested = (result.get("assessment") or result.get("lead_assessment") or
              result.get("lead_analysis") or result.get("scores") or {})
    if not isinstance(nested, dict):
        nested = {}
    aliases = {
        "Service fit": ("service_fit", "serviceFit", "fit"),
        "Need": ("need", "need_level"),
        "Urgency": ("urgency", "urgency_level"),
        "Intent": ("intent", "intent_level"),
    }
    scores = {}
    for label, keys in aliases.items():
        value = next((result.get(k) for k in keys if result.get(k) is not None), None)
        if value is None:
            value = next((nested.get(k) for k in (label, *keys) if nested.get(k) is not None), None)
        if isinstance(value, dict):
            value = value.get("score") or value.get("level") or value.get("value")
        value = str(value or "UNKNOWN").strip().upper()
        scores[label] = value if value in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"} else "UNKNOWN"

    summary = result.get("summary") or result.get("lead_summary") or nested.get("summary") or ""
    missing = result.get("missing") or result.get("missing_information") or result.get("missing_info") or []
    next_action = (result.get("next_action") or result.get("recommended_next_action") or
                   result.get("recommendation") or "")
    if isinstance(missing, str):
        missing = [missing]
    return {
        "scores": scores,
        "note": {"summary": str(summary), "missing": missing, "next": str(next_action)},
        "raw": result,
    }


def mock_draft_outreach(lead, profile):
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


def normalize_agent_draft(result):
    """Accept plain text or a structured agent response for a draft message."""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        result = result.get("data") or result.get("result") or result
        if isinstance(result, dict):
            for key in ("draft", "outreach", "outreach_draft", "draft_message", "message", "text", "content", "reply"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return ""


def normalize_profile_extraction(result):
    """Unwrap structured extraction payloads while keeping the profile keys flat."""
    if not isinstance(result, dict):
        return {}
    result = result.get("data") or result.get("result") or result
    if not isinstance(result, dict):
        return {}
    for key in ("fields", "profile_fields", "extracted_fields", "business_profile"):
        if isinstance(result.get(key), dict):
            return result[key]
    return result


def mock_extract_reply_info(lead, text):
    t = text.lower()
    if re.search(r"not interested|no thanks|no thank you|not now|don't contact|do not contact|\bstop\b", t):
        lead["outcome"] = "declined"
    elif re.search(r"\b(yes|yeah|sure|ok|okay|please|sounds good|that works|book)\b", t) \
            and lead.get("status") in ("QUALIFIED", "CONSULTATION OFFERED"):
        lead["outcome"] = "accepted"
    supported = next((w for w in SUPPORTED_WORDS if w in t), None)
    if supported and ("gcse" in t or re.search(r"year\s+(9|10|11)\b", t)):
        lead["subject"] = "GCSE " + ("Maths" if supported.startswith("math") else supported.title())
    else:
        for w in UNSUPPORTED_WORDS:
            if w in t:
                lead["subject"] = w.title()
                break
        else:
            if supported:
                lead["subject"] = "GCSE " + ("Maths" if supported.startswith("math") else supported.title())
    year = re.search(r"year (\d{1,2})", t)
    if year:
        lead["year"] = int(year.group(1))
    cur = re.search(r"(?:getting|currently|on) (?:around |about )?(?:a |an |grade )?(\d)", t)
    tgt = re.search(r"(?:needs?|aiming for|target(?: is)?|wants?) (?:a |an |grade )?(\d)", t)
    if cur:
        lead["current_grade"] = cur.group(1)
    if tgt:
        lead["target_grade"] = tgt.group(1)
    for phrase in ("sixth form", "college", "mock", "exam"):
        if phrase in t:
            lead["motivation"] = f"Mentioned {phrase}"
            break
    if any(p in t for p in ("how much", "price", "cost", "£")):
        lead["pricing_interest"] = True


def mock_draft_answer(lead, profile):
    first = lead["parent"].split()[0]
    subject = (lead.get("subject") or "").lower()
    if lead.get("confirm_fit_after_conversation") and not lead.get("candidate_engaged"):
        if lead.get("id") == "james":
            return (f"Hi {first}, thanks for your enquiry. To make sure I point you to the right support, are you "
                    "looking specifically for tutoring in your university Maths course, or are you asking about GCSE Maths? "
                    "Nova Tutors currently focuses on GCSE Maths and Science, so I want to confirm what level you need.")
        return (f"Hi {first}, thanks for getting in touch. GCSE Maths sessions are £30 per 60 minutes and are "
                "one-to-one, with support tailored to the student's learning needs. Before I recommend a next step, "
                "which would Oliver most like help with first: exam technique, harder questions, confidence, or time management?")
    if lead.get("status") == "CONSULTATION REQUESTED":
        return (f"Thanks, {first}. A member of the {profile.get('name', 'team')} team will be in touch to confirm "
                "an exact time based on tutor availability. We haven't booked a time yet.")
    if lead.get("status") == "CLOSED":
        return f"Thanks for letting us know, {first}. We won't contact you further. Please reach out if anything changes."
    if lead.get("status") == "NOT A FIT":
        return (f"Hi {first}, thanks for confirming what support you need. Nova Tutors currently focuses on GCSE Maths "
                "and Science, so we can't provide university-level Mathematics tutoring. I'm sorry we can't help with this request.")
    if lead.get("status") == "NEEDS HUMAN":
        return f"Thanks, {first}. A member of our team will review this and get back to you."
    if any(w in subject for w in UNSUPPORTED_WORDS):
        return (f"Hi {first}, thanks for getting in touch. At the moment we only offer GCSE Maths and Science "
                f"tutoring, so we wouldn't be able to help with {lead['subject']}. I'm sorry we can't help this time.")
    pricing = profile.get("pricing")
    if lead["pricing_interest"] and pricing:
        if lead.get("status") == "QUALIFIED":
            return (f"Hi {first}, thanks for sharing that. Sessions are {pricing}. Based on what you've told me, "
                    "a free 15-minute consultation would be a helpful next step. Would you like us to arrange one? "
                    "A team member can confirm a time based on tutor availability.")
        return (f"Hi {first}, thanks for the details. On pricing: {pricing}\n\n"
                f"Could you also share {lead['student']}'s current grade and target grade?")
    return (f"Hi {first}, thanks for sharing that. To point you in the right direction, could you tell me "
            f"{lead['student']}'s current grade and the grade they are aiming for?")


# ---------- AI LAYER: uses Groq (agent.py) when a key is set, otherwise the mocks above ----------
def use_ai():
    return agent is not None and agent.available()


def safe_ai(fn, fallback):
    try:
        return fn()
    except Exception as e:  # network error, bad JSON, quota, etc.
        st.session_state["ai_error"] = str(e)[:300]
        return fallback()


def cached(key, fn):
    """Streamlit reruns the script on every click, so remember AI results."""
    cache = st.session_state.setdefault("ai_cache", {})
    if key not in cache:
        with st.spinner("Nova is thinking..."):
            cache[key] = fn()
    return cache[key]


def ai_extract(key, text):
    if not use_ai():
        return {}
    labels = {f[0]: f[2] for f in active_fields()}

    def run():
        found = normalize_profile_extraction(
            agent.extract_profile_fields(st.session_state.profile, labels, key, text)
        )
        return {k: str(v).strip() for k, v in found.items()
                if k in labels and str(v).strip() and (k == key or k not in st.session_state.profile)}
    return safe_ai(run, lambda: {})


def assess_full(lead, profile):
    """Returns (scores, note). note has summary / missing / next from the AI."""
    lead.setdefault("other_facts", {})
    if not use_ai():
        return mock_assess(lead, profile), {}

    def run():
        normalized = normalize_agent_assessment(agent.analyse_lead(profile, lead))
        return normalized["scores"], normalized["note"]

    basis = {k: lead.get(k) for k in LEAD_KEYS}
    basis["facts"] = lead["other_facts"]
    basis["n"] = len(lead["thread"])
    key = "assess:" + json.dumps(basis, sort_keys=True, default=str)
    result = cached(key, lambda: safe_ai(run, lambda: (mock_assess(lead, profile), {})))
    if lead.get("last_assessment_key") != key:
        lead["last_assessment_key"] = key
        log_lead_activity(lead, "Nova assessed service fit, need, urgency, and intent.")
    return result


def assess(lead, profile):
    return assess_full(lead, profile)[0]


def draft_outreach(lead, profile):
    if not use_ai():
        draft = mock_draft_outreach(lead, profile)
        if draft and not lead.get("outreach_generated"):
            lead["outreach_generated"] = True
            log_lead_activity(lead, "Nova prepared personalized outreach using demo mode.", "success")
        return draft
    key = "outreach:" + lead["parent"] + str(lead.get("student")) + str(lead.get("year")) + str(lead.get("subject"))
    draft = cached(key, lambda: safe_ai(lambda: normalize_agent_draft(agent.draft_outreach(profile, lead)),
                                        lambda: mock_draft_outreach(lead, profile)))
    if draft and not lead.get("outreach_generated"):
        lead["outreach_generated"] = True
        log_lead_activity(lead, "Nova prepared personalized outreach.", "success")
    return draft


def extract_reply_info(lead, text):
    lead.setdefault("other_facts", {})
    if not use_ai():
        return mock_extract_reply_info(lead, text)

    def run():
        r = agent.extract_reply_info(lead, text)
        if isinstance(r, dict):
            r = r.get("data") or r.get("result") or r
            if isinstance(r, dict) and isinstance(r.get("lead_updates"), dict):
                r = {**r, **r["lead_updates"]}
        if not isinstance(r, dict):
            return
        for src, dst in (("student_name", "student"), ("subject", "subject"), ("current_grade", "current_grade"),
                         ("target_grade", "target_grade"), ("motivation", "motivation")):
            if r.get(src):
                lead[dst] = str(r[src]).strip()
        if r.get("year"):
            try:
                lead["year"] = int(r["year"])
            except (TypeError, ValueError):
                lead["year"] = str(r["year"])
        if r.get("pricing_interest"):
            lead["pricing_interest"] = True
        if r.get("outcome") == "accepted_consultation" and lead.get("status") in ("QUALIFIED", "CONSULTATION OFFERED"):
            lead["outcome"] = "accepted"
        elif r.get("outcome") == "declined":
            lead["outcome"] = "declined"
        for k, v in (r.get("other_facts") or {}).items():
            if v:
                lead["other_facts"][str(k)] = str(v)

    with st.spinner("Nova is reading your message..."):
        safe_ai(run, lambda: mock_extract_reply_info(lead, text))


def draft_answer(lead, profile):
    """Returns the suggested reply text, or None when Nova thinks a human must answer."""
    qualified = lead["status"] == "QUALIFIED"
    customer_msgs = [t for who, t in lead["thread"] if who != "Nova"]
    message = customer_msgs[-1] if customer_msgs else ""
    st.session_state["needs_human_reason"] = ""
    if lead.get("confirm_fit_after_conversation") and not lead.get("candidate_engaged"):
        return mock_draft_answer(lead, profile)
    if not use_ai():
        return mock_draft_answer(lead, profile)

    def run():
        r = agent.draft_reply(profile, lead, message, qualified)
        if isinstance(r, dict):
            r = r.get("data") or r.get("result") or r
        if not isinstance(r, dict):
            return {"text": normalize_agent_draft(r), "reason": ""}
        if r.get("needs_human"):
            return {"text": None, "reason": r.get("reason", "")}
        return {"text": normalize_agent_draft(r), "reason": str(r.get("reason", ""))}
    key = f"answer:{len(lead['thread'])}:{lead['status']}:{message}"
    out = cached(key, lambda: safe_ai(run, lambda: {"text": mock_draft_answer(lead, profile), "reason": ""}))
    st.session_state["needs_human_reason"] = out["reason"]
    return out["text"]


def show_guardrail_check(text, profile):
    if not use_ai() or not text.strip():
        return
    r = cached("guard:" + text, lambda: safe_ai(lambda: agent.check_guardrails(profile, text),
                                                 lambda: {"ok": True, "issues": []}))
    if r.get("ok", True):
        st.caption("✅ Guardrail check passed")
    else:
        st.warning("Guardrail check flagged: " + "; ".join(str(i) for i in r.get("issues", [])))


def is_qualified(scores):
    """Service fit must be HIGH; need, urgency and intent can't be LOW/UNKNOWN, and at least two must be HIGH."""
    if scores.get("Service fit") != "HIGH":
        return False
    others = [scores.get(k) for k in ("Need", "Urgency", "Intent")]
    return all(v in ("HIGH", "MEDIUM") for v in others) and others.count("HIGH") >= 2


def ai_status():
    st.sidebar.markdown("## ✨ Nova")
    st.sidebar.caption("AI customer growth agent · Demo")
    if use_ai():
        st.sidebar.success(f"AI on ({agent.MODEL})")
    elif agent is None:
        st.sidebar.warning("AI off: run pip install groq")
    else:
        st.sidebar.warning("AI off: GROQ_API_KEY not set (using mock answers)")
    if st.session_state.get("ai_error"):
        st.sidebar.error("Last AI error: " + st.session_state["ai_error"])
    st.sidebar.divider()
    if st.sidebar.button("↻ Reset demo", use_container_width=True):
        st.session_state.clear()
        st.rerun()


def render_activity(items, empty_message="No activity yet."):
    if not items:
        st.caption(empty_message)
        return
    for item in reversed(items[-12:]):
        if isinstance(item, dict):
            message, kind = item.get("message", ""), item.get("kind", "info")
        else:  # tolerate earlier/simple agent event formats
            message, kind = str(item), "info"
        icon = {"success": "✓", "warning": "!", "info": "•"}.get(kind, "•")
        st.markdown(f"**{icon}** {message}")


def handle_customer_message(lead, profile, text):
    """The 'customer' (you) wrote something: save it, learn from it, re-score the lead."""
    text = text.strip()
    if not text:
        return
    if lead["thread"] and tuple(lead["thread"][-1]) == ("Customer", text):
        return  # ignore accidental double-submit
    lead["thread"].append(("Customer", text))
    log_lead_activity(lead, f"Customer replied: {text[:100]}{'…' if len(text) > 100 else ''}")
    if lead.get("confirm_fit_after_conversation"):
        lead["candidate_engaged"] = True
    lead.pop("outcome", None)
    extract_reply_info(lead, text)
    log_lead_activity(lead, f"Nova extracted details from {lead['parent'].split()[0]}'s reply and refreshed the lead profile.", "success")
    outcome = lead.pop("outcome", None)

    if outcome == "accepted":
        lead["status"] = "CONSULTATION REQUESTED"
        lead["recommended_next_action"] = "A team member should confirm an exact consultation time based on tutor availability."
        log_lead_activity(lead, "Customer accepted the consultation. Human scheduling is next.", "success")
    elif outcome == "declined":
        lead["status"] = "CLOSED"
        lead["recommended_next_action"] = "No further outreach. Leave the door open if the customer returns."
        log_lead_activity(lead, "Customer declined. Conversation closed respectfully.")
    elif lead["status"] != "CONSULTATION OFFERED":
        scores = assess(lead, profile)
        if scores["Service fit"] == "LOW":
            lead["status"] = "NOT A FIT"
            lead["other_facts"]["Rejection category"] = "Service mismatch"
            lead["other_facts"]["Human approval required"] = "No"
            lead["other_facts"]["CRM note"] = "The customer confirmed they need a service outside Nova Tutors' GCSE Maths and Science offering. Do not continue sales follow-ups."
            lead["recommended_next_action"] = "Close as Not Qualified. Do not continue sales follow-ups."
            first = lead["parent"].split()[0]
            reply = (f"Hi {first}, thanks for confirming what support you need. Nova Tutors currently focuses on GCSE Maths "
                     "and Science, so we can't provide university-level Mathematics tutoring. I'm sorry we can't help with this request.")
            lead["thread"].append(("Nova", reply))
            lead["ended"] = True
            log_lead_activity(lead, "After confirming the customer's needs, Nova identified a service mismatch and closed the lead without human approval.", "warning")
        elif is_qualified(scores):
            if lead.get("id") == "rachel":
                lead["status"] = "CONSULTATION NEEDED"
                lead["qualification_status"] = "QUALIFIED"
                lead["recommended_next_action"] = "Offer Rachel a short consultation with a human member of the Nova Tutors team, after owner confirmation."
                lead.setdefault("consultation_draft", "Hi Rachel, thanks for sharing Oliver's situation. Nova Tutors offers one-to-one GCSE Maths support at £30 per 60-minute session. We can't promise a particular grade outcome, but a free 15-minute consultation with a team member is a good way to discuss exam technique, tutor suitability, progress updates, and what sessions include. Would you like us to arrange one? The team can confirm a time and tutor availability.")
                log_lead_activity(lead, "After Rachel replied, Nova assessed her as a fit and queued a consultation invitation for owner approval.", "success")
            else:
                lead["status"] = "QUALIFIED"
                lead["recommended_next_action"] = "Invite the customer to book a free 15-minute consultation."
                log_lead_activity(lead, "Lead assessed as qualified after the customer conversation.", "success")
        else:
            lead["status"] = "RESPONDED"
            lead["recommended_next_action"] = "Ask for the most important missing qualification detail."
            log_lead_activity(lead, "Nova needs more information before deciding whether the lead is a fit.", "info")

    customer_count = sum(1 for who, _ in lead["thread"] if who != "Nova")
    if customer_count >= MAX_CUSTOMER_MESSAGES and lead["status"] not in TERMINAL:
        lead["status"] = "NEEDS HUMAN"
        lead["recommended_next_action"] = "Hand the conversation to a team member."
        log_lead_activity(lead, "Conversation reached the message limit and needs a human.", "warning")


def handoff_summary(lead):
    parts = [f"{lead['parent']}, {lead_line(lead).lower()}", f"wants {lead.get('subject') or 'unknown'}"]
    if lead["current_grade"] or lead["target_grade"]:
        parts.append(f"grade {lead['current_grade'] or '?'} aiming for {lead['target_grade'] or '?'}")
    if lead["motivation"]:
        parts.append(lead["motivation"])
    for k, v in lead.get("other_facts", {}).items():
        parts.append(f"{k}: {v}")
    return "; ".join(parts) + "."


def show_outcome(lead):
    status = lead["status"]
    if status == "CONSULTATION REQUESTED":
        st.success("🎉 The customer wants a free consultation. Conversation complete.")
        st.markdown("**Handoff for a team member:** confirm a time based on tutor availability. "
                    "Nova can't confirm a booking by itself.")
    elif status == "NOT A FIT":
        st.info("❌ Not qualified: Nova explained the service mismatch and closed the lead. No human approval is needed.")
    elif status == "NEEDS HUMAN":
        st.warning("🙋 This conversation went on a long time, so Nova is handing it to a team member.")
    else:
        st.info("🔒 Conversation closed. Nova will not contact this lead again unless the owner decides to.")
    st.markdown("**Summary:** " + handoff_summary(lead))
    st.caption("Use **Reset this lead** at the top to test a new customer.")


# ---------------------------------------------------------------
# SCREENS
# ---------------------------------------------------------------
def screen_active():
    st.markdown('<div class="nova-kicker">Workspace overview</div>', unsafe_allow_html=True)
    st.title(f"Nova is ready for {st.session_state.profile.get('name', 'your business')} ✨")
    st.caption("Review leads, prepare thoughtful outreach, and keep every customer conversation grounded in your business profile.")
    leads = st.session_state.setdefault("leads", [])
    selected = st.session_state.get("lead")
    if selected and not any(item.get("id") == selected.get("id") for item in leads):
        leads.append(selected)
    c1, c2, c3 = st.columns(3)
    c1.metric("Leads", len(leads))
    c2.metric("Awaiting approval", sum(1 for item in leads if item.get("status") in ("AWAITING APPROVAL", "CONSULTATION NEEDED")))
    c3.metric("Qualified / consultation", sum(1 for item in leads if item.get("status") in ("QUALIFIED", "CONSULTATION NEEDED", "CONSULTATION OFFERED", "CONSULTATION REQUESTED")))

    h, add = st.columns([4, 1])
    h.subheader("Lead pipeline")
    if not leads:
        if add.button("＋ Load demo leads", type="primary", use_container_width=True):
            st.session_state.leads = [new_lead(), rachel_lead(), james_lead()]
            st.session_state.lead = None
            for item in st.session_state.leads:
                log_lead_activity(item, f"{item['parent']} added to the demo pipeline.", "success")
            log_activity("Three sample leads loaded. Rachel and James start as unassessed enquiries and need a conversation before Nova decides fit.", "success")
            st.rerun()
    else:
        if add.button("↻ Reset leads", use_container_width=True):
            st.session_state.leads = [new_lead(), rachel_lead(), james_lead()]
            st.session_state.lead = None
            st.session_state.outreach_draft = ""
            st.session_state.editing_outreach = False
            log_activity("All three sample leads were reset to their starting states.", "success")
            st.rerun()
    if not leads:
        with st.container(border=True):
            st.markdown("### Three demo outcomes")
            st.write("Load Sarah, Rachel, and James. Rachel and James begin as enquiries; Nova must talk with them before it decides fit or recommends a consultation.")
    else:
        for item in leads:
            with st.container(border=True):
                a, b, c, d = st.columns([2.5, 1.5, 1.7, .8])
                a.markdown(f"**{item['parent']}**  \n{lead_line(item)}")
                b.write(item["subject"])
                c.markdown(f"**{STATUS_ICON.get(item['status'], '')} {item['status']}**")
                if d.button("Open", type="primary", key=f"open_{item.get('id', item['parent'])}"):
                    st.session_state.lead = item
                    st.session_state.stage = "lead"
                    st.rerun()

    left, right = st.columns([3, 2], gap="large")
    with left:
        with st.expander("Business profile", expanded=False):
            for section in SECTIONS:
                section_fields = [f for f in FIELDS if f[1] == section and st.session_state.profile.get(f[0])]
                if not section_fields:
                    continue
                st.markdown(f"**{section}**")
                for field in section_fields:
                    st.write(f"**{field[2]}:** {st.session_state.profile[field[0]]}")
    with right:
        with st.container(border=True):
            st.markdown("#### Agent activity log")
            render_activity(st.session_state.get("activity", []), "Nova's onboarding and lead actions will appear here.")


def screen_lead():
    lead = st.session_state.lead
    profile = st.session_state.profile
    lead.setdefault("other_facts", {})

    t1, t2, t3, _ = st.columns([1, 1, 1, 2])
    if t1.button("← Back to dashboard"):
        st.session_state.stage = "active"
        st.rerun()
    if t2.button("Reset this lead"):
        st.session_state.lead = demo_lead_by_id(lead.get("id", "sarah"))
        upsert_demo_lead(st.session_state.lead)
        st.session_state.outreach_draft = ""
        st.session_state.editing_outreach = False
        log_lead_activity(st.session_state.lead, f"{lead['parent']}'s demo lead was reset.")
        st.rerun()
    if lead["thread"] and not lead.get("ended") and t3.button("End conversation"):
        lead["status"] = "CLOSED"
        lead["ended"] = True
        lead["recommended_next_action"] = "No further outreach unless the customer returns."
        log_lead_activity(lead, "Owner ended the conversation.")
        st.rerun()
    st.markdown('<div class="nova-kicker">Lead workspace · Conversation</div>', unsafe_allow_html=True)
    st.title(f"{lead['parent']}  {STATUS_ICON.get(lead['status'], '')} {lead['status']}")

    left, right = st.columns([3, 2], gap="large")

    # ---- right: what Nova knows and thinks about this lead ----
    with right:
        wait_for_talk = lead.get("confirm_fit_after_conversation") and not lead.get("candidate_engaged")
        if wait_for_talk:
            scores = {"Service fit": "UNKNOWN", "Need": "UNKNOWN", "Urgency": "UNKNOWN", "Intent": "UNKNOWN"}
            note = {
                "summary": "Initial enquiry received. Nova will confirm the customer's needs before assessing fit.",
                "missing": [],
                "next": "Reply to the enquiry and wait for the customer's answer before deciding.",
            }
        else:
            scores, note = assess_full(lead, profile)
        with st.container(border=True):
            st.markdown("**What Nova knows**")
            st.markdown(f"{lead_line(lead)}")
            st.markdown(f"Wants: **{lead.get('subject') or 'Unknown'}**")
            if lead.get("relationship"):
                st.markdown(f"Relationship: **{lead['relationship']}**")
            if lead.get("age"):
                st.markdown(f"Age: **{lead['age']}**")
            if lead.get("location"):
                st.markdown(f"Location: **{lead['location']}**")
            if lead.get("education_level"):
                st.markdown(f"Education: **{lead['education_level']}**")
            if lead.get("problem"):
                st.markdown(f"Need: {lead['problem']}")
            st.markdown(f"Current grade: **{lead['current_grade'] or 'Unknown'}**")
            st.markdown(f"Target grade: **{lead['target_grade'] or 'Unknown'}**")
            st.markdown(f"Motivation: {lead['motivation'] or 'Unknown'}")
            st.markdown(f"Asked about pricing: {'Yes' if lead['pricing_interest'] else 'Not yet'}")
            for k, v in lead["other_facts"].items():
                st.markdown(f"{k}: {v}")
        with st.container(border=True):
            st.markdown("**Lead assessment**")
            for k, v in scores.items():
                icon = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(v, "⚪")
                st.markdown(f"{icon} {k}: **{v}**")
            if note.get("summary"):
                st.caption(str(note["summary"]))
            if note.get("missing"):
                st.markdown("**Still needed:** " + ", ".join(str(m) for m in note["missing"]))
            next_action = lead.get("recommended_next_action") or note.get("next")
            if next_action:
                st.markdown("**Recommended next action:** " + str(next_action))
        if lead["status"] in ("QUALIFIED", "CONSULTATION OFFERED", "CONSULTATION REQUESTED"):
            with st.container(border=True):
                st.success("✅ Qualified lead")
                st.markdown("**Recommended next action**")
                st.write(note.get("next") or lead.get("recommended_next_action") or "Invite Sarah to a free 15-minute consultation.")
                if lead.get("status") == "CONSULTATION REQUESTED":
                    st.caption("A team member should confirm the exact time against tutor availability.")
        elif lead["status"] == "CONSULTATION NEEDED":
            st.warning("Consultation needed · waiting for your confirmation")
            st.write(lead.get("recommended_next_action", "Review the consultation recommendation."))
        if lead["status"] == "RESPONDED" and not lead.get("ended") and not wait_for_talk:
            if st.button("Qualify anyway (owner decision)"):
                lead["status"] = "QUALIFIED"
                lead["recommended_next_action"] = "Invite the customer to book a free 15-minute consultation."
                log_lead_activity(lead, "Owner marked this lead as qualified.", "success")
                st.rerun()
        with st.container(border=True):
            st.markdown("**Agent activity log**")
            render_activity(lead.get("activity", []), "Lead activity will appear here.")

    # ---- left: the conversation ----
    with left:
        for who, text in lead["thread"]:
            is_nova = who == "Nova"
            with st.chat_message("assistant" if is_nova else "user", avatar="✨" if is_nova else None):
                st.write(text)

        status = lead["status"]

        if lead.get("ended"):
            show_outcome(lead)

        elif status == "AWAITING APPROVAL":
            st.markdown("### Personalized outreach draft")
            st.warning("Workflow paused · Review this message before Nova can contact Sarah.")
            if not st.session_state.get("outreach_draft"):
                st.session_state.outreach_draft = draft_outreach(lead, profile)
            if st.session_state.get("editing_outreach"):
                text = st.text_area("Edit outreach", value=st.session_state.outreach_draft, height=240, key="outreach_edit")
                show_guardrail_check(text, profile)
                save_col, cancel_col, reject_col = st.columns(3)
                if save_col.button("Save edits", type="primary", use_container_width=True):
                    if text.strip():
                        st.session_state.outreach_draft = text.strip()
                        st.session_state.editing_outreach = False
                        log_lead_activity(lead, "Owner edited and saved the outreach draft.")
                        st.rerun()
                if cancel_col.button("Cancel edit", use_container_width=True):
                    st.session_state.editing_outreach = False
                    st.rerun()
                if reject_col.button("Reject draft", use_container_width=True):
                    lead["status"] = "CLOSED"
                    lead["ended"] = True
                    lead["recommended_next_action"] = "Outreach was rejected; do not contact Sarah."
                    log_lead_activity(lead, "Owner rejected the outreach draft. Workflow stopped.", "warning")
                    st.rerun()
            else:
                st.text_area("Draft message", value=st.session_state.outreach_draft, height=240, disabled=True, key="outreach_readonly")
                show_guardrail_check(st.session_state.outreach_draft, profile)
                approve_col, edit_col, reject_col = st.columns(3)
                if approve_col.button("Approve and send", type="primary", use_container_width=True):
                    lead["thread"].append(("Nova", st.session_state.outreach_draft))
                    lead["status"] = "CONTACTED"
                    lead["recommended_next_action"] = "Wait for Sarah's reply, then update lead details and reassess fit."
                    st.session_state.editing_outreach = False
                    log_lead_activity(lead, "Owner approved first outreach. Message sent in demo.", "success")
                    st.rerun()
                if edit_col.button("Edit draft", use_container_width=True):
                    st.session_state.editing_outreach = True
                    st.rerun()
                if reject_col.button("Reject", use_container_width=True):
                    lead["status"] = "CLOSED"
                    lead["ended"] = True
                    lead["recommended_next_action"] = "Outreach was rejected; do not contact Sarah."
                    log_lead_activity(lead, "Owner rejected the outreach draft. Workflow stopped.", "warning")
                    st.rerun()

        elif status == "CONSULTATION NEEDED":
            st.markdown("### Consultation recommendation")
            st.warning("Approval required · Nova will wait here until you confirm the next step.")
            st.write("Nova recommends a short conversation with a team member so Rachel can ask about tutor suitability, session pricing, and progress tracking.")
            draft = st.text_area(
                "Review or edit the invitation",
                value=lead.get("consultation_draft", ""),
                height=220,
                key=f"consultation_draft_{lead.get('id', 'lead')}",
            )
            show_guardrail_check(draft, profile)
            approve_col, reject_col = st.columns(2)
            if approve_col.button("Confirm and invite Rachel", type="primary", use_container_width=True):
                if draft.strip():
                    lead["consultation_draft"] = draft.strip()
                    lead["thread"].append(("Nova", draft.strip()))
                    lead["status"] = "CONSULTATION OFFERED"
                    lead["recommended_next_action"] = "Wait for Rachel's response; a team member should confirm tutor suitability and exact availability."
                    log_lead_activity(lead, "Owner confirmed Nova's consultation recommendation and approved the invitation.", "success")
                    st.rerun()
            if reject_col.button("Reject recommendation", use_container_width=True):
                lead["status"] = "CLOSED"
                lead["ended"] = True
                lead["recommended_next_action"] = "Owner declined the consultation recommendation. Do not send an invitation."
                log_lead_activity(lead, "Owner rejected the consultation recommendation. No message was sent.", "warning")
                st.rerun()

        else:
            last_who = lead["thread"][-1][0] if lead["thread"] else "Nova"
            if last_who == "Nova":
                if status == "CONSULTATION OFFERED":
                    st.success("Nova has invited the customer to a free consultation. Reply \"yes\" to accept, or decline to end the chat.")
                st.info("Your turn: reply to Nova as the customer. Explain your situation like a real parent would.")
                if status == "CONSULTATION OFFERED":
                    sample = "Yes, we'd like to book a free consultation."
                    sample_label = f"Use {lead['parent'].split()[0]}'s sample acceptance"
                elif lead.get("id") == "rachel":
                    sample = "Exam technique and time management are the biggest issues. Oliver is currently around Grade 5 and we'd like him to reach Grade 7. He is doing Edexcel GCSE Maths."
                    sample_label = "Use Rachel's sample reply"
                elif lead.get("id") == "james":
                    sample = "Yes, I need help with my first-year university Maths course, especially calculus and linear algebra."
                    sample_label = "Use James's sample reply"
                else:
                    sample = ("He's currently getting around a 4 and needs a 6 for sixth form. "
                              "How much would tutoring be?")
                    sample_label = "Use Sarah's sample reply"
                if st.button(sample_label, key=f"sample_reply_{status}"):
                    handle_customer_message(lead, profile, sample)
                    st.rerun()
                msg = st.chat_input("Type as the customer...")
                if msg:
                    handle_customer_message(lead, profile, msg)
                    st.rerun()
            else:
                answer = draft_answer(lead, profile)
                if answer is None:
                    reason = st.session_state.get("needs_human_reason", "")
                    st.error("Nova can't answer this reliably and needs a human. " + reason)
                    answer = ""
                st.markdown("**Nova's suggested reply (you approve it before it's sent)**")
                text = st.text_area("Edit if you like", value=answer, height=240, key=f"reply_{len(lead['thread'])}")
                show_guardrail_check(text, profile)
                if st.button("Send reply (simulated)", type="primary", disabled=not text.strip()):
                    lead["thread"].append(("Nova", text))
                    log_lead_activity(lead, "Owner approved Nova's customer reply. Message sent in demo.", "success")
                    if lead["status"] == "QUALIFIED":
                        lead["status"] = "CONSULTATION OFFERED"
                        lead["recommended_next_action"] = "Await Sarah's answer; if accepted, hand scheduling to a team member."
                    elif lead["status"] in TERMINAL:
                        lead["ended"] = True  # that was Nova's final message
                    st.rerun()


# ---------------------------------------------------------------
# 6. ROUTER
# ---------------------------------------------------------------
init_state()
ai_status()
{
    "start": screen_start,
    "chat": screen_chat,
    "review": screen_review,
    "active": screen_active,
    "lead": screen_lead,
}[st.session_state.stage]()
