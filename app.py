"""
Gram Panchayat Grievance Redressal — Streamlit Prototype (PS-24)

Two views:
  - Citizen Portal: guided chatbot to file / track a grievance
  - Panchayat Admin: register of all grievances, editable inline

Data is stored in a local SQLite file (grievances.db) so the Admin
view sees whatever the Citizen Portal submits, and it survives
reruns/page reloads within the same deployment.
"""

import sqlite3
import datetime
import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Gram Panchayat Grievance Redressal",
    page_icon="🏛️",
    layout="wide",
)

DB_PATH = "grievances.db"

CATEGORIES = {
    "Water Supply": ["water", "pipe", "pipeline", "tap", "borewell", "supply",
                      "tanker", "leak", "hand pump", "handpump", "paani", "jal"],
    "Roads": ["road", "pothole", "street", "footpath", "bridge", "culvert",
              "sadak", "gadda"],
    "Electricity": ["light", "electricity", "power", "transformer", "wire",
                     "streetlight", "current", "bijli", "meter"],
    "Sanitation": ["garbage", "drain", "sewage", "toilet", "cleanliness",
                    "trash", "waste", "gutter", "safai", "naali"],
    "Other": [],
}
STATUSES = ["Received", "In Progress", "Resolved"]

# ------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT NOT NULL,
            language TEXT,
            status TEXT NOT NULL DEFAULT 'Received',
            created_at TEXT NOT NULL
        )
    """)
    return conn


def classify(text: str) -> str:
    t = text.lower()
    for cat, keywords in CATEGORIES.items():
        if cat == "Other":
            continue
        if any(k in t for k in keywords):
            return cat
    return "Other"


def next_ticket_id(conn) -> str:
    count = conn.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]
    year = datetime.datetime.now().year
    return f"GP/{year}/{count + 1:04d}"


def add_grievance(category, description, location, phone, language):
    conn = get_conn()
    ticket_id = next_ticket_id(conn)
    created_at = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO grievances (ticket_id, category, description, location, "
        "phone, language, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (ticket_id, category, description, location, phone, language,
         "Received", created_at),
    )
    conn.commit()
    conn.close()
    return ticket_id, created_at


def get_all_df() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM grievances ORDER BY id DESC", conn)
    conn.close()
    return df


def find_grievance(query: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM grievances WHERE ticket_id = ? OR phone = ?",
        (query.strip(), query.strip()),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    cols = ["id", "ticket_id", "category", "description", "location",
            "phone", "language", "status", "created_at"]
    return dict(zip(cols, row))


def update_row(row_id: int, category: str, status: str):
    conn = get_conn()
    conn.execute(
        "UPDATE grievances SET category = ?, status = ? WHERE id = ?",
        (category, status, row_id),
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------
# CHAT STATE HELPERS
# ------------------------------------------------------------------
def bot(text):
    st.session_state.messages.append({"role": "assistant", "content": text})


def user(text):
    st.session_state.messages.append({"role": "user", "content": text})


def init_chat():
    st.session_state.messages = []
    st.session_state.step = "choose_language"
    st.session_state.data = {}
    bot("Namaste 🙏 I'm the Panchayat Sahayak. I can help you file a "
        "grievance or check the status of an existing one.")
    bot("Which language would you like to continue in?")


if "initialized" not in st.session_state:
    st.session_state.initialized = True
    init_chat()

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("🏛️ Gram Panchayat Grievance Redressal")
st.caption("Prototype · Citizen Chatbot & Admin Register — शिकायत दर्ज करें · निवारण पाएँ")

tab_citizen, tab_admin = st.tabs(["🧑‍🌾 Citizen Portal", "🗂️ Panchayat Admin"])

# ==================== CITIZEN PORTAL ====================
with tab_citizen:
    col_chat, col_info = st.columns([2, 1])

    with col_info:
        st.subheader("How this works")
        st.markdown(
            "Describe your problem in your own words. The assistant detects "
            "the right department automatically, gives you a tracking ID, "
            "and staff can update the status as work progresses.\n\n"
            "- No login needed — track by ID or phone\n"
            "- Works in text; voice/IVR is a later phase\n"
            "- SMS/WhatsApp alerts on status change (simulated)"
        )
        if st.button("🔍 Track an existing complaint", use_container_width=True):
            st.session_state.step = "track_input"
            bot("Sure — please enter your Ticket ID (e.g. GP/2026/0001) or "
                "registered phone number.")
            st.rerun()
        if st.button("↺ Start a new conversation", use_container_width=True):
            init_chat()
            st.rerun()

    with col_chat:
        chat_box = st.container(height=480)
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        step = st.session_state.step

        # --- quick-reply buttons for each step ---
        if step == "choose_language":
            c1, c2 = st.columns(2)
            if c1.button("English", use_container_width=True):
                user("English")
                st.session_state.data["language"] = "English"
                st.session_state.step = "describe"
                bot("Please describe your problem in your own words — e.g. "
                    "*'water pipeline near ward 4 is broken'*.")
                st.rerun()
            if c2.button("हिन्दी", use_container_width=True):
                user("हिन्दी")
                st.session_state.data["language"] = "हिन्दी"
                st.session_state.step = "describe"
                bot("Please describe your problem in your own words — e.g. "
                    "*'water pipeline near ward 4 is broken'*.")
                st.rerun()

        elif step == "confirm_category":
            detected = st.session_state.data["category"]
            c1, c2 = st.columns(2)
            if c1.button(f"Yes, {detected} is correct", use_container_width=True):
                user("Yes, correct")
                st.session_state.step = "location"
                bot("Which village / ward is this in?")
                st.rerun()
            if c2.button("No, let me choose", use_container_width=True):
                user("No, let me choose")
                st.session_state.step = "pick_category"
                bot("Please pick the correct department:")
                st.rerun()

        elif step == "pick_category":
            cats = list(CATEGORIES.keys())
            cols = st.columns(len(cats))
            for i, cat in enumerate(cats):
                if cols[i].button(cat, use_container_width=True, key=f"pick_{cat}"):
                    user(cat)
                    st.session_state.data["category"] = cat
                    st.session_state.step = "location"
                    bot("Which village / ward is this in?")
                    st.rerun()

        # --- free-text input drives: describe / location / phone / track ---
        if step in ("describe", "location", "phone", "track_input"):
            prompt_placeholder = {
                "describe": "Describe your problem...",
                "location": "Village / ward name...",
                "phone": "10-digit phone number...",
                "track_input": "Ticket ID or phone number...",
            }[step]
            text = st.chat_input(prompt_placeholder)
            if text:
                user(text)

                if step == "describe":
                    st.session_state.data["description"] = text
                    detected = classify(text)
                    st.session_state.data["category"] = detected
                    bot(f"Based on your description, this looks like a "
                        f"**{detected}** issue. Is that correct?")
                    st.session_state.step = "confirm_category"

                elif step == "location":
                    st.session_state.data["location"] = text
                    bot("Please share a phone number for status updates via "
                        "SMS/WhatsApp.")
                    st.session_state.step = "phone"

                elif step == "phone":
                    st.session_state.data["phone"] = text
                    d = st.session_state.data
                    ticket_id, created_at = add_grievance(
                        d["category"], d["description"], d["location"],
                        text, d["language"],
                    )
                    bot("Thank you. Your grievance has been registered and "
                        "routed to the correct department:")
                    bot(
                        f"**🎫 Complaint Slip**\n\n"
                        f"**Ticket ID:** `{ticket_id}`\n\n"
                        f"**Department:** {d['category']}\n\n"
                        f"**Location:** {d['location']}\n\n"
                        f"**Status:** Received\n\n"
                        f"**Filed:** {created_at[:10]}"
                    )
                    bot("You'll get an SMS/WhatsApp update when the status "
                        "changes (simulated). You can also track it anytime "
                        "using this ID or your phone number.")
                    st.toast(f'📩 SMS sent (simulated): "Your complaint '
                              f'{ticket_id} has been received."')
                    st.session_state.step = "done"

                elif step == "track_input":
                    match = find_grievance(text)
                    if match is None:
                        bot("I couldn't find a grievance with that ID or "
                            "phone number. Please check and try again, or "
                            "file a new complaint.")
                    else:
                        idx = STATUSES.index(match["status"])
                        timeline = "\n\n".join(
                            f"{'●' if i <= idx else '○'} {s}"
                            + ("  *(current)*" if i == idx else "")
                            for i, s in enumerate(STATUSES)
                        )
                        bot(f"Found it! Here's the latest status for "
                            f"**{match['ticket_id']}**:")
                        bot(
                            f"**Status Timeline** — {match['category']}\n\n"
                            f"{timeline}\n\n"
                            f"**Location:** {match['location']}"
                        )
                        st.session_state.step = "done"

                st.rerun()

# ==================== ADMIN DASHBOARD ====================
with tab_admin:
    df = get_all_df()

    total = len(df)
    received = int((df["status"] == "Received").sum()) if total else 0
    in_progress = int((df["status"] == "In Progress").sum()) if total else 0
    resolved = int((df["status"] == "Resolved").sum()) if total else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Filed", total)
    m2.metric("Received", received)
    m3.metric("In Progress", in_progress)
    m4.metric("Resolved", resolved)

    st.divider()

    left, right = st.columns([3, 1])

    with left:
        st.subheader("Grievance Register")

        if total == 0:
            st.info("No grievances yet — file one from the Citizen Portal "
                     "to see it appear here.")
        else:
            fc1, fc2, fc3 = st.columns(3)
            dept_filter = fc1.selectbox("Department", ["All"] + list(CATEGORIES.keys()))
            status_filter = fc2.selectbox("Status", ["All"] + STATUSES)
            search = fc3.text_input("Search description / location")

            view = df.copy()
            if dept_filter != "All":
                view = view[view["category"] == dept_filter]
            if status_filter != "All":
                view = view[view["status"] == status_filter]
            if search:
                mask = (
                    view["description"].str.contains(search, case=False, na=False)
                    | view["location"].str.contains(search, case=False, na=False)
                )
                view = view[mask]

            edited = st.data_editor(
                view[["id", "ticket_id", "description", "category", "location",
                      "created_at", "status"]],
                column_config={
                    "id": None,  # hide raw id
                    "ticket_id": st.column_config.TextColumn("Ticket ID", disabled=True),
                    "description": st.column_config.TextColumn("Description", disabled=True),
                    "category": st.column_config.SelectboxColumn(
                        "Department", options=list(CATEGORIES.keys())),
                    "location": st.column_config.TextColumn("Location", disabled=True),
                    "created_at": st.column_config.TextColumn("Filed", disabled=True),
                    "status": st.column_config.SelectboxColumn(
                        "Status", options=STATUSES),
                },
                hide_index=True,
                use_container_width=True,
                key="register_editor",
            )

            # detect and persist changes
            merged = edited.set_index("id")
            original = view.set_index("id")
            changed_ids = merged.index[
                (merged["category"] != original["category"])
                | (merged["status"] != original["status"])
            ]
            for rid in changed_ids:
                update_row(int(rid), merged.loc[rid, "category"], merged.loc[rid, "status"])
            if len(changed_ids):
                st.toast(f"✅ Updated {len(changed_ids)} grievance(s). "
                          "Citizens notified (simulated).")
                st.rerun()

    with right:
        st.subheader("Category Breakdown")
        if total:
            counts = df["category"].value_counts().reindex(
                list(CATEGORIES.keys()), fill_value=0)
            st.bar_chart(counts)
        else:
            st.caption("No data yet.")

st.divider()
st.caption("Working prototype for PS-24 · Rule-based classification (MVP) · "
           "SQLite storage for this demo only")
