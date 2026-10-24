"""Read-only presentation of backend records; no brain or execution imports."""
from backend_client import BackendError


def load_inspection(client, lead_id):
    lead = client.get_lead(lead_id)
    business = client.get_business(lead["businessId"])
    messages = client.get_conversation_history(lead_id)
    actions = client.get_agent_actions(lead_id)
    if (lead["id"] != lead_id or business["id"] != lead["businessId"]
            or any(item["leadId"] != lead_id for item in messages + actions)):
        raise BackendError("Backend returned records for a different lead or business")
    return {"lead": lead, "business": business, "messages": messages, "actions": actions}


def render_inspection(st, client, lead_id):
    """Fetch fresh data on every render; never fall back to a local demo lead."""
    st.caption("Backend lead · Read-only")
    st.button("Refresh backend data", key="refresh_backend_lead")
    try:
        snapshot = load_inspection(client, lead_id)
    except BackendError as error:
        st.error("Could not load this lead from the backend: " + str(error))
        st.info("Start the backend with npm run start:backend and try Refresh backend data.")
        return
    lead, business = snapshot["lead"], snapshot["business"]
    st.title(lead["name"])
    st.write("Status: " + lead["status"])
    st.caption("Lead ID: " + lead["id"] + " · Business: " + business["name"] + " (" + business["id"] + ")")
    left, right = st.columns([3, 2], gap="large")
    with right:
        with st.container(border=True):
            st.markdown("**What Nova knows**")
            fields = [
                ("Student", lead["student"]["name"]), ("Subject", lead["subject"]),
                ("Year", lead["year"]), ("Need", lead["need"]),
                ("Current grade", lead["currentGrade"]), ("Target grade", lead["targetGrade"]),
                ("Exam board", lead["examBoard"]), ("Tier", lead["tier"]),
                ("Location", lead["location"]), ("Preferred format", lead["preferredFormat"]),
            ]
            for label, value in fields:
                st.write(label + ": " + ("Unknown" if value is None or value == "" else str(value)))
            st.write("Recommended next action: " + lead["nextAction"])
            missing = []
            for field in business["qualificationRules"]["requiredFields"]:
                if lead.get(field) is None or lead.get(field) == "":
                    missing.append(field)
            st.caption("Missing configured qualification fields: " + (", ".join(missing) if missing else "None"))
        with st.container(border=True):
            st.markdown("**Agent activity log**")
            if not snapshot["actions"]:
                st.caption("No recorded agent actions.")
            for action in reversed(snapshot["actions"]):
                st.write(action["action"] + " · " + action["status"])
                st.caption(action["id"] + " · " + action["timestamp"])
                st.text(action["reason"])
    with left:
        st.markdown("**Conversation history**")
        if not snapshot["messages"]:
            st.caption("No recorded messages.")
        for message in snapshot["messages"]:
            role = "assistant" if message["sender"] == "nova" else "user"
            with st.chat_message(role):
                st.caption(message["sender"] + " · " + message["timestamp"])
                st.write(message["content"])
