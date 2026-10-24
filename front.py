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
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { color-scheme:light; --ink:#18221f; --muted:#52635a; --green:#126448; --mint:#e8f5ef; --line:#dce6df; --paper:#fbfcfa; }
html, body, [class*="css"], .stApp { font-family:'DM Sans',sans-serif; color:var(--ink) !important; }
.stApp { background:var(--paper); }
[data-testid="stAppViewContainer"] { background:var(--paper); }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
label, .stRadio p, .stCheckbox p, .stSelectbox p { color:var(--ink) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:var(--muted) !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] div { color:#18221f !important; }
[data-testid="stHeader"] { background:rgba(251,252,250,.92); }
[data-testid="stSidebar"] { background:#f1f6f2; border-right:1px solid var(--line); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label { color:#26382f !important; }
.block-container { max-width:1440px; padding-top:2.1rem; padding-bottom:3rem; }
h1,h2,h3,h4 { font-family:'Manrope',sans-serif !important; letter-spacing:-.035em; color:var(--ink) !important; }
h1 { font-size:2.35rem !important; font-weight:800 !important; }
h2 { font-size:1.6rem !important; font-weight:750 !important; }
p, label { line-height:1.65; }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:16px; padding:16px 18px; box-shadow:0 5px 18px rgba(25,50,38,.035); }
[data-testid="stMetricLabel"] { color:var(--muted); }
[data-testid="stMetricValue"] { font-family:'Manrope',sans-serif; font-weight:800; }
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
[data-testid="stChatInput"] textarea::placeholder, [data-testid="stTextArea"] textarea::placeholder,
[data-testid="stTextInput"] input::placeholder { color:#697a71 !important; opacity:1; }
[data-testid="stProgressBar"] > div > div { background:var(--green); }
[data-testid="stExpander"] { border-color:var(--line); border-radius:14px; background:#fff; }
.nova-kicker { color:var(--green); text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:800; margin-bottom:.4rem; }
.nova-hero { border:1px solid #dce9df; border-radius:24px; padding:2.6rem 2.8rem; background:radial-gradient(circle at 90% 5%,#dbf1e6 0,transparent 30%),linear-gradient(135deg,#fff 0%,#f2f8f3 100%); box-shadow:0 12px 38px rgba(25,50,38,.055); margin:.5rem 0 1.4rem; }
.nova-hero h1 { font-size:3rem !important; margin:.1rem 0 .6rem; }
.nova-hero p { color:#586a60; font-size:1.05rem; max-width:680px; }
.nova-pill { display:inline-block; background:#e5f2e9; color:#17684f; border-radius:99px; padding:.38rem .75rem; font-size:.78rem; font-weight:700; }
@media (max-width:800px) { .block-container{padding:1rem 1rem 2rem}.nova-hero{padding:1.5rem}.nova-hero h1{font-size:2.3rem !important} }
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
        st.session_state.profile.update(ai_extract(key, text))
        st.session_state.profile.setdefault(key, text.strip())
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
        st.rerun()
    if c2.button("Skip with Nova Tutors demo data"):
        st.session_state.level = MODES[mode]
        st.session_state.profile = {k: v for k, v in DEMO.items() if v}
        st.session_state.stage = "review"
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
    "NEW": "🆕", "CONTACTED": "📤", "RESPONDED": "💬", "QUALIFIED": "✅",
    "CONSULTATION OFFERED": "📅", "CONSULTATION REQUESTED": "🎉", "NOT A FIT": "❌",
    "CLOSED": "🔒", "NEEDS HUMAN": "🙋",
}
# When the lead reaches one of these, Nova sends one final message and the conversation ends.
TERMINAL = ("CONSULTATION REQUESTED", "CLOSED", "NOT A FIT", "NEEDS HUMAN")
MAX_CUSTOMER_MESSAGES = 10  # safety net: hand over to a human after this many customer messages
LEAD_KEYS = ("subject", "year", "student", "problem", "current_grade", "target_grade", "motivation", "pricing_interest")

UNSUPPORTED_WORDS = ("english", "history", "geography", "french", "spanish", "german", "language",
                     "computer science", "a-level", "a level", "alevel", "primary", "sats", "university")
SUPPORTED_WORDS = ("maths", "math", "biology", "chemistry", "physics", "science")


def new_lead():
    return {
        "parent": "Sarah Johnson", "student": "Daniel", "year": 11, "subject": "GCSE Maths",
        "problem": "Needs additional Maths support.",
        "current_grade": None, "target_grade": None, "motivation": None, "pricing_interest": False,
        "other_facts": {}, "status": "NEW", "thread": [],
    }


def lead_line(lead):
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


def mock_extract_reply_info(lead, text):
    t = text.lower()
    if re.search(r"not interested|no thanks|no thank you|not now|don't contact|do not contact|\bstop\b", t):
        lead["outcome"] = "declined"
    elif re.search(r"\b(yes|yeah|sure|ok|okay|please|sounds good|that works|book)\b", t) \
            and lead.get("status") in ("QUALIFIED", "CONSULTATION OFFERED"):
        lead["outcome"] = "accepted"
    for w in UNSUPPORTED_WORDS:
        if w in t:
            lead["subject"] = w.title()
            break
    else:
        for w in SUPPORTED_WORDS:
            if w in t:
                lead["subject"] = "GCSE " + ("Maths" if w.startswith("math") else w.title())
                break
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
    if any(w in subject for w in UNSUPPORTED_WORDS):
        return (f"Hi {first}, thanks for getting in touch. At the moment we only offer GCSE Maths and Science "
                f"tutoring, so we wouldn't be able to help with {lead['subject']}. I'm sorry we can't help this time.")
    pricing = profile.get("pricing")
    if lead["pricing_interest"] and pricing:
        return (f"Hi {first}, thanks for the details. On pricing: {pricing}\n\n"
                f"Would you like to find out more before deciding?")
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
        found = agent.extract_profile_fields(st.session_state.profile, labels, key, text)
        return {k: str(v).strip() for k, v in found.items()
                if k in labels and str(v).strip() and (k == key or k not in st.session_state.profile)}
    return safe_ai(run, lambda: {})


def assess_full(lead, profile):
    """Returns (scores, note). note has summary / missing / next from the AI."""
    lead.setdefault("other_facts", {})
    if not use_ai():
        return mock_assess(lead, profile), {}

    def run():
        r = agent.analyse_lead(profile, lead)
        scores = {
            "Service fit": str(r.get("service_fit") or "UNKNOWN").upper(),
            "Need": str(r.get("need") or "UNKNOWN").upper(),
            "Urgency": str(r.get("urgency") or "UNKNOWN").upper(),
            "Intent": str(r.get("intent") or "UNKNOWN").upper(),
        }
        note = {"summary": r.get("summary", ""), "missing": r.get("missing", []), "next": r.get("next_action", "")}
        return scores, note

    basis = {k: lead.get(k) for k in LEAD_KEYS}
    basis["facts"] = lead["other_facts"]
    basis["n"] = len(lead["thread"])
    key = "assess:" + json.dumps(basis, sort_keys=True, default=str)
    return cached(key, lambda: safe_ai(run, lambda: (mock_assess(lead, profile), {})))


def assess(lead, profile):
    return assess_full(lead, profile)[0]


def draft_outreach(lead, profile):
    if not use_ai():
        return mock_draft_outreach(lead, profile)
    key = "outreach:" + lead["parent"] + str(lead.get("student")) + str(lead.get("year")) + str(lead.get("subject"))
    return cached(key, lambda: safe_ai(lambda: agent.draft_outreach(profile, lead),
                                       lambda: mock_draft_outreach(lead, profile)))


def extract_reply_info(lead, text):
    lead.setdefault("other_facts", {})
    if not use_ai():
        return mock_extract_reply_info(lead, text)

    def run():
        r = agent.extract_reply_info(lead, text)
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
    if not use_ai():
        return mock_draft_answer(lead, profile)

    def run():
        r = agent.draft_reply(profile, lead, message, qualified)
        if r.get("needs_human"):
            return {"text": None, "reason": r.get("reason", "")}
        return {"text": r.get("reply"), "reason": ""}
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
    if use_ai():
        st.sidebar.success(f"AI on ({agent.MODEL})")
    elif agent is None:
        st.sidebar.warning("AI off: run pip install groq")
    else:
        st.sidebar.warning("AI off: GROQ_API_KEY not set (using mock answers)")
    if st.session_state.get("ai_error"):
        st.sidebar.error("Last AI error: " + st.session_state["ai_error"])


def handle_customer_message(lead, profile, text):
    """The 'customer' (you) wrote something: save it, learn from it, re-score the lead."""
    text = text.strip()
    if not text:
        return
    if lead["thread"] and tuple(lead["thread"][-1]) == ("Customer", text):
        return  # ignore accidental double-submit
    lead["thread"].append(("Customer", text))
    lead.pop("outcome", None)
    extract_reply_info(lead, text)
    outcome = lead.pop("outcome", None)

    if outcome == "accepted":
        lead["status"] = "CONSULTATION REQUESTED"
    elif outcome == "declined":
        lead["status"] = "CLOSED"
    elif lead["status"] != "CONSULTATION OFFERED":
        scores = assess(lead, profile)
        if scores["Service fit"] == "LOW":
            lead["status"] = "NOT A FIT"
        elif is_qualified(scores):
            lead["status"] = "QUALIFIED"
        else:
            lead["status"] = "RESPONDED"

    customer_count = sum(1 for who, _ in lead["thread"] if who != "Nova")
    if customer_count >= MAX_CUSTOMER_MESSAGES and lead["status"] not in TERMINAL:
        lead["status"] = "NEEDS HUMAN"


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
        st.info("❌ Nova politely explained it can't help with this request. Conversation closed.")
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
    lead = st.session_state.lead
    c1, c2, c3 = st.columns(3)
    c1.metric("Leads", 1 if lead else 0)
    c2.metric("Awaiting your approval", 1 if lead and lead["status"] == "NEW" else 0)
    c3.metric("Qualified", 1 if lead and lead["status"] in ("QUALIFIED", "CONSULTATION OFFERED", "CONSULTATION REQUESTED") else 0)

    st.subheader("Leads")
    if lead is None:
        st.info("No leads yet. Add one to see what Nova can do.")
        if st.button("Add demo lead: Sarah Johnson", type="primary"):
            st.session_state.lead = new_lead()
            st.rerun()
    else:
        with st.container(border=True):
            a, b, c, d = st.columns([3, 2, 2, 1])
            a.markdown(f"**{lead['parent']}**  \n{lead_line(lead)}")
            b.write(lead["subject"])
            c.write(f"{STATUS_ICON.get(lead['status'], '')} {lead['status']}")
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
    lead.setdefault("other_facts", {})

    t1, t2, t3, _ = st.columns([1, 1, 1, 2])
    if t1.button("← Back to dashboard"):
        st.session_state.stage = "active"
        st.rerun()
    if t2.button("Reset this lead"):
        st.session_state.lead = new_lead()
        st.rerun()
    if lead["thread"] and not lead.get("ended") and t3.button("End conversation"):
        lead["status"] = "CLOSED"
        lead["ended"] = True
        st.rerun()
    st.markdown('<div class="nova-kicker">Lead workspace · Conversation</div>', unsafe_allow_html=True)
    st.title(f"{lead['parent']}  {STATUS_ICON.get(lead['status'], '')} {lead['status']}")

    left, right = st.columns([3, 2], gap="large")

    # ---- right: what Nova knows and thinks about this lead ----
    with right:
        scores, note = assess_full(lead, profile)
        with st.container(border=True):
            st.markdown("**What Nova knows**")
            st.markdown(f"{lead_line(lead)}")
            st.markdown(f"Wants: **{lead.get('subject') or 'Unknown'}**")
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
            if note.get("next"):
                st.markdown("**Next step:** " + str(note["next"]))
        if lead["status"] == "RESPONDED" and not lead.get("ended"):
            if st.button("Qualify anyway (owner decision)"):
                lead["status"] = "QUALIFIED"
                st.rerun()

    # ---- left: the conversation ----
    with left:
        for who, text in lead["thread"]:
            is_nova = who == "Nova"
            with st.chat_message("assistant" if is_nova else "user", avatar="✨" if is_nova else None):
                st.write(text)

        status = lead["status"]

        if lead.get("ended"):
            show_outcome(lead)

        elif status == "NEW":
            st.markdown("**Outreach draft (needs your approval)**")
            text = st.text_area("Edit the message if you like", value=draft_outreach(lead, profile), height=260)
            show_guardrail_check(text, profile)
            if st.button("Approve and send (simulated)", type="primary"):
                lead["thread"].append(("Nova", text))
                lead["status"] = "CONTACTED"
                st.rerun()

        else:
            last_who = lead["thread"][-1][0] if lead["thread"] else "Nova"
            if last_who == "Nova":
                if status == "CONSULTATION OFFERED":
                    st.success("Nova has invited the customer to a free consultation. Reply \"yes\" to accept, or decline to end the chat.")
                st.info("Your turn: reply to Nova as the customer. Explain your situation like a real parent would.")
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
                    if lead["status"] == "QUALIFIED":
                        lead["status"] = "CONSULTATION OFFERED"
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
