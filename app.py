"""
Gram Panchayat Grievance Redressal — Streamlit Prototype (PS-24)

Two views:
  - Citizen Portal: bilingual (English/Hindi) chatbot to file / track a
    grievance, with optional photo attachment
  - Panchayat Admin: register of all grievances, editable inline, with
    overdue (escalation) flags and photo preview

Data is stored in a local SQLite file (grievances.db) so the Admin
view sees whatever the Citizen Portal submits, and it survives
reruns/page reloads within the same deployment.
"""

import sqlite3
import datetime
import base64
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
DEFAULT_ESCALATION_DAYS = 5

# ------------------------------------------------------------------
# TRANSLATIONS (citizen-facing UI only — admin stays English, staff-facing)
# ------------------------------------------------------------------
STRINGS = {
    "English": {
        "welcome1": "Namaste 🙏 I'm the Panchayat Sahayak. I can help you "
                     "file a grievance or check the status of an existing one.",
        "welcome2": "Which language would you like to continue in?",
        "info_title": "How this works",
        "info_body": "Describe your problem in your own words. The assistant "
                      "detects the right department automatically, gives you "
                      "a tracking ID, and staff can update the status as work "
                      "progresses.",
        "info_bullets": [
            "No login needed — track by ID or phone",
            "Works in text; voice/IVR is a later phase",
            "You can attach a photo of the problem",
            "SMS/WhatsApp alerts on status change (simulated)",
        ],
        "track_button": "🔍 Track an existing complaint",
        "restart_button": "↺ Start a new conversation",
        "describe_prompt": "Please describe your problem in your own words — "
                            "e.g. *'water pipeline near ward 4 is broken'*.",
        "describe_placeholder": "Describe your problem...",
        "confirm_q": "Based on your description, this looks like a "
                      "**{cat}** issue. Is that correct?",
        "yes_correct": "Yes, {cat} is correct",
        "no_choose": "No, let me choose",
        "pick_category_prompt": "Please pick the correct department:",
        "location_prompt": "Which village / ward is this in?",
        "location_placeholder": "Village / ward name...",
        "phone_prompt": "Please share a phone number for status updates via "
                         "SMS/WhatsApp.",
        "phone_placeholder": "10-digit phone number...",
        "photo_choice_prompt": "Would you like to attach a photo of the "
                                "problem? This helps staff assess it faster.",
        "attach_photo": "📎 Attach a photo",
        "skip_photo": "Skip",
        "photo_upload_prompt": "Please upload a photo.",
        "photo_uploader_label": "Choose a photo",
        "submit_photo": "Submit with photo",
        "skip_after_all": "Submit without photo",
        "photo_attached": "Photo attached.",
        "registered_msg": "Thank you. Your grievance has been registered and "
                           "routed to the correct department:",
        "slip_title": "🎫 Complaint Slip",
        "ticket_label": "Ticket ID",
        "dept_label": "Department",
        "loc_label": "Location",
        "status_label": "Status",
        "filed_label": "Filed",
        "followup_msg": "You'll get an SMS/WhatsApp update when the status "
                         "changes (simulated). You can also track it anytime "
                         "using this ID or your phone number.",
        "sms_toast": '📩 SMS sent (simulated): "Your complaint {tid} has '
                     'been received."',
        "track_prompt": "Sure — please enter your Ticket ID (e.g. "
                         "GP/2026/0001) or registered phone number.",
        "track_placeholder": "Ticket ID or phone number...",
        "not_found": "I couldn't find a grievance with that ID or phone "
                      "number. Please check and try again, or file a new "
                      "complaint.",
        "found_msg": "Found it! Here's the latest status for **{tid}**:",
        "timeline_title": "Status Timeline",
        "current_label": "(current)",
    },
    "हिन्दी": {
        "welcome1": "नमस्ते 🙏 मैं पंचायत सहायक हूं। मैं आपकी शिकायत दर्ज "
                     "करने या मौजूदा शिकायत की स्थिति जांचने में मदद कर सकता हूं।",
        "welcome2": "आप किस भाषा में आगे बढ़ना चाहेंगे?",
        "info_title": "यह कैसे काम करता है",
        "info_body": "अपनी समस्या अपने शब्दों में बताएं। सहायक सही विभाग "
                      "को स्वतः पहचान लेता है, आपको एक ट्रैकिंग आईडी देता है, "
                      "और कर्मचारी काम के अनुसार स्थिति अपडेट कर सकते हैं।",
        "info_bullets": [
            "लॉगिन की जरूरत नहीं — आईडी या फ़ोन नंबर से ट्रैक करें",
            "अभी टेक्स्ट में उपलब्ध; वॉइस/IVR बाद के चरण में",
            "आप समस्या की फोटो भी जोड़ सकते हैं",
            "स्थिति बदलने पर SMS/WhatsApp सूचना (सिम्युलेटेड)",
        ],
        "track_button": "🔍 मौजूदा शिकायत ट्रैक करें",
        "restart_button": "↺ नई बातचीत शुरू करें",
        "describe_prompt": "कृपया अपनी समस्या अपने शब्दों में बताएं — जैसे "
                            "*'वार्ड 4 के पास पानी की पाइपलाइन टूटी है'*।",
        "describe_placeholder": "अपनी समस्या लिखें...",
        "confirm_q": "आपके विवरण के अनुसार, यह **{cat}** से जुड़ी समस्या "
                      "लगती है। क्या यह सही है?",
        "yes_correct": "हां, {cat} सही है",
        "no_choose": "नहीं, मैं खुद चुनूंगा",
        "pick_category_prompt": "कृपया सही विभाग चुनें:",
        "location_prompt": "यह किस गांव / वार्ड में है?",
        "location_placeholder": "गांव / वार्ड का नाम...",
        "phone_prompt": "स्थिति अपडेट के लिए कृपया अपना फ़ोन नंबर साझा करें।",
        "phone_placeholder": "10 अंकों का फ़ोन नंबर...",
        "photo_choice_prompt": "क्या आप समस्या की एक फोटो जोड़ना चाहेंगे? "
                                "इससे कर्मचारियों को जल्दी समझने में मदद मिलती है।",
        "attach_photo": "📎 फोटो जोड़ें",
        "skip_photo": "छोड़ें",
        "photo_upload_prompt": "कृपया एक फोटो अपलोड करें।",
        "photo_uploader_label": "फोटो चुनें",
        "submit_photo": "फोटो के साथ जमा करें",
        "skip_after_all": "बिना फोटो जमा करें",
        "photo_attached": "फोटो जोड़ी गई।",
        "registered_msg": "धन्यवाद। आपकी शिकायत दर्ज कर ली गई है और सही "
                           "विभाग को भेज दी गई है:",
        "slip_title": "🎫 शिकायत पर्ची",
        "ticket_label": "टिकट आईडी",
        "dept_label": "विभाग",
        "loc_label": "स्थान",
        "status_label": "स्थिति",
        "filed_label": "दर्ज तिथि",
        "followup_msg": "स्थिति बदलने पर आपको SMS/WhatsApp सूचना मिलेगी "
                         "(सिम्युलेटेड)। आप इस आईडी या फ़ोन नंबर से कभी भी "
                         "स्थिति देख सकते हैं।",
        "sms_toast": '📩 SMS भेजा गया (सिम्युलेटेड): "आपकी शिकायत {tid} '
                     'प्राप्त हो गई है।"',
        "track_prompt": "कृपया अपनी टिकट आईडी (जैसे GP/2026/0001) या "
                         "पंजीकृत फ़ोन नंबर दर्ज करें।",
        "track_placeholder": "टिकट आईडी या फ़ोन नंबर...",
        "not_found": "उस आईडी या फ़ोन नंबर से कोई शिकायत नहीं मिली। कृपया "
                      "दोबारा जांचें या नई शिकायत दर्ज करें।",
        "found_msg": "मिल गया! **{tid}** की नवीनतम स्थिति यहां है:",
        "timeline_title": "स्थिति समयरेखा",
        "current_label": "(वर्तमान)",
    },
}


def t(key, **kwargs):
    lang = st.session_state.get("data", {}).get("language", "English")
    text = STRINGS.get(lang, STRINGS["English"]).get(key, STRINGS["English"][key])
    return text.format(**kwargs) if kwargs else text


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
    # lightweight migration for dbs created before photo/resolved_at existed
    for col, coltype in (("photo", "BLOB"), ("resolved_at", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE grievances ADD COLUMN {col} {coltype}")
        except sqlite3.OperationalError:
            pass
    return conn


def classify(text: str) -> str:
    t_ = text.lower()
    for cat, keywords in CATEGORIES.items():
        if cat == "Other":
            continue
        if any(k in t_ for k in keywords):
            return cat
    return "Other"


def next_ticket_id(conn) -> str:
    count = conn.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]
    year = datetime.datetime.now().year
    return f"GP/{year}/{count + 1:04d}"


def add_grievance(category, description, location, phone, language, photo_bytes=None):
    conn = get_conn()
    ticket_id = next_ticket_id(conn)
    created_at = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO grievances (ticket_id, category, description, location, "
        "phone, language, status, created_at, photo) VALUES (?,?,?,?,?,?,?,?,?)",
        (ticket_id, category, description, location, phone, language,
         "Received", created_at, photo_bytes),
    )
    conn.commit()
    conn.close()
    return ticket_id, created_at


def get_all_df() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM grievances ORDER BY id DESC", conn)
    conn.close()
    if df.empty:
        return df

    def to_uri(b):
        if b is None:
            return None
        try:
            return "data:image/png;base64," + base64.b64encode(b).decode()
        except Exception:
            return None

    df["photo_uri"] = df["photo"].apply(to_uri)

    now = datetime.datetime.now()

    def age(row):
        created = datetime.datetime.fromisoformat(row["created_at"])
        end = (datetime.datetime.fromisoformat(row["resolved_at"])
               if row["resolved_at"] else now)
        return (end - created).days

    df["age_days"] = df.apply(age, axis=1)
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
            "phone", "language", "status", "created_at", "photo", "resolved_at"]
    return dict(zip(cols, row))


def update_row(row_id: int, category: str, status: str):
    conn = get_conn()
    prev_status = conn.execute(
        "SELECT status FROM grievances WHERE id = ?", (row_id,)
    ).fetchone()[0]

    if status == "Resolved" and prev_status != "Resolved":
        conn.execute(
            "UPDATE grievances SET category=?, status=?, resolved_at=? WHERE id=?",
            (category, status, datetime.datetime.now().isoformat(), row_id),
        )
    elif status != "Resolved" and prev_status == "Resolved":
        conn.execute(
            "UPDATE grievances SET category=?, status=?, resolved_at=NULL WHERE id=?",
            (category, status, row_id),
        )
    else:
        conn.execute(
            "UPDATE grievances SET category=?, status=? WHERE id=?",
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
    bot(STRINGS["English"]["welcome1"])
    bot(STRINGS["English"]["welcome2"])


def finalize_grievance(photo_bytes=None):
    d = st.session_state.data
    ticket_id, created_at = add_grievance(
        d["category"], d["description"], d["location"], d["phone"],
        d["language"], photo_bytes,
    )
    bot(t("registered_msg"))
    slip = (
        f"**{t('slip_title')}**\n\n"
        f"**{t('ticket_label')}:** `{ticket_id}`\n\n"
        f"**{t('dept_label')}:** {d['category']}\n\n"
        f"**{t('loc_label')}:** {d['location']}\n\n"
        f"**{t('status_label')}:** Received\n\n"
        f"**{t('filed_label')}:** {created_at[:10]}"
    )
    if photo_bytes:
        slip += f"\n\n📷 {t('photo_attached')}"
    bot(slip)
    bot(t("followup_msg"))
    st.toast(t("sms_toast", tid=ticket_id))
    st.session_state.step = "done"


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
        st.subheader(t("info_title"))
        st.markdown(t("info_body"))
        st.markdown("\n".join(f"- {b}" for b in t("info_bullets")))
        if st.button(t("track_button"), use_container_width=True):
            st.session_state.step = "track_input"
            bot(t("track_prompt"))
            st.rerun()
        if st.button(t("restart_button"), use_container_width=True):
            init_chat()
            st.rerun()

    with col_chat:
        chat_box = st.container(height=480)
        with chat_box:
            for m in st.session_state.messages:
                avatar = "🏛️" if m["role"] == "assistant" else "🧑‍🌾"
                with st.chat_message(m["role"], avatar=avatar):
                    st.markdown(m["content"])

        step = st.session_state.step

        # --- quick-reply buttons for each step ---
        if step == "choose_language":
            c1, c2 = st.columns(2)
            if c1.button("English", use_container_width=True):
                user("English")
                st.session_state.data["language"] = "English"
                st.session_state.step = "describe"
                bot(t("describe_prompt"))
                st.rerun()
            if c2.button("हिन्दी", use_container_width=True):
                user("हिन्दी")
                st.session_state.data["language"] = "हिन्दी"
                st.session_state.step = "describe"
                bot(t("describe_prompt"))
                st.rerun()

        elif step == "confirm_category":
            detected = st.session_state.data["category"]
            c1, c2 = st.columns(2)
            if c1.button(t("yes_correct", cat=detected), use_container_width=True):
                user(t("yes_correct", cat=detected))
                st.session_state.step = "location"
                bot(t("location_prompt"))
                st.rerun()
            if c2.button(t("no_choose"), use_container_width=True):
                user(t("no_choose"))
                st.session_state.step = "pick_category"
                bot(t("pick_category_prompt"))
                st.rerun()

        elif step == "pick_category":
            cats = list(CATEGORIES.keys())
            cols = st.columns(len(cats))
            for i, cat in enumerate(cats):
                if cols[i].button(cat, use_container_width=True, key=f"pick_{cat}"):
                    user(cat)
                    st.session_state.data["category"] = cat
                    st.session_state.step = "location"
                    bot(t("location_prompt"))
                    st.rerun()

        elif step == "photo_choice":
            c1, c2 = st.columns(2)
            if c1.button(t("attach_photo"), use_container_width=True):
                user(t("attach_photo"))
                st.session_state.step = "photo_upload"
                bot(t("photo_upload_prompt"))
                st.rerun()
            if c2.button(t("skip_photo"), use_container_width=True):
                user(t("skip_photo"))
                finalize_grievance()
                st.rerun()

        elif step == "photo_upload":
            uploaded = st.file_uploader(
                t("photo_uploader_label"), type=["jpg", "jpeg", "png"],
                key="photo_uploader",
            )
            c1, c2 = st.columns(2)
            if uploaded is not None:
                if c1.button(t("submit_photo"), use_container_width=True):
                    finalize_grievance(photo_bytes=uploaded.getvalue())
                    st.rerun()
            if c2.button(t("skip_after_all"), use_container_width=True):
                finalize_grievance()
                st.rerun()

        # --- free-text input drives: describe / location / phone / track ---
        if step in ("describe", "location", "phone", "track_input"):
            placeholder_key = {
                "describe": "describe_placeholder",
                "location": "location_placeholder",
                "phone": "phone_placeholder",
                "track_input": "track_placeholder",
            }[step]
            text = st.chat_input(t(placeholder_key))
            if text:
                user(text)

                if step == "describe":
                    st.session_state.data["description"] = text
                    detected = classify(text)
                    st.session_state.data["category"] = detected
                    bot(t("confirm_q", cat=detected))
                    st.session_state.step = "confirm_category"

                elif step == "location":
                    st.session_state.data["location"] = text
                    bot(t("phone_prompt"))
                    st.session_state.step = "phone"

                elif step == "phone":
                    st.session_state.data["phone"] = text
                    bot(t("photo_choice_prompt"))
                    st.session_state.step = "photo_choice"

                elif step == "track_input":
                    match = find_grievance(text)
                    if match is None:
                        bot(t("not_found"))
                    else:
                        idx = STATUSES.index(match["status"])
                        timeline = "\n\n".join(
                            f"{'●' if i <= idx else '○'} {s}"
                            + (f"  *{t('current_label')}*" if i == idx else "")
                            for i, s in enumerate(STATUSES)
                        )
                        bot(t("found_msg", tid=match["ticket_id"]))
                        bot(
                            f"**{t('timeline_title')}** — {match['category']}\n\n"
                            f"{timeline}\n\n"
                            f"**{t('loc_label')}:** {match['location']}"
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

    with st.expander("⚙️ Escalation settings"):
        threshold = st.number_input(
            "Flag as overdue after this many days without resolution",
            min_value=1, max_value=60, value=DEFAULT_ESCALATION_DAYS,
        )

    overdue_count = 0
    if total:
        overdue_count = int(
            ((df["status"] != "Resolved") & (df["age_days"] >= threshold)).sum()
        )
    if overdue_count:
        st.warning(f"⚠️ {overdue_count} grievance(s) are overdue "
                    f"(open {threshold}+ days).")

    st.divider()

    left, right = st.columns([3, 1])

    with left:
        st.subheader("Grievance Register")

        if total == 0:
            st.info("No grievances yet — file one from the Citizen Portal "
                     "to see it appear here.")
        else:
            fc1, fc2, fc3, fc4 = st.columns(4)
            dept_filter = fc1.selectbox("Department", ["All"] + list(CATEGORIES.keys()))
            status_filter = fc2.selectbox("Status", ["All"] + STATUSES)
            overdue_only = fc3.checkbox("Overdue only")
            search = fc4.text_input("Search description / location")

            view = df.copy()
            if dept_filter != "All":
                view = view[view["category"] == dept_filter]
            if status_filter != "All":
                view = view[view["status"] == status_filter]
            if overdue_only:
                view = view[(view["status"] != "Resolved") & (view["age_days"] >= threshold)]
            if search:
                mask = (
                    view["description"].str.contains(search, case=False, na=False)
                    | view["location"].str.contains(search, case=False, na=False)
                )
                view = view[mask]

            view = view.copy()
            view["flag"] = view.apply(
                lambda r: "⚠️ Overdue" if r["status"] != "Resolved"
                and r["age_days"] >= threshold else "", axis=1,
            )

            edited = st.data_editor(
                view[["id", "ticket_id", "photo_uri", "description", "category",
                      "location", "created_at", "age_days", "flag", "status"]],
                column_config={
                    "id": None,  # hide raw id
                    "ticket_id": st.column_config.TextColumn("Ticket ID", disabled=True),
                    "photo_uri": st.column_config.ImageColumn("Photo"),
                    "description": st.column_config.TextColumn("Description", disabled=True),
                    "category": st.column_config.SelectboxColumn(
                        "Department", options=list(CATEGORIES.keys())),
                    "location": st.column_config.TextColumn("Location", disabled=True),
                    "created_at": st.column_config.TextColumn("Filed", disabled=True),
                    "age_days": st.column_config.NumberColumn("Age (days)", disabled=True),
                    "flag": st.column_config.TextColumn("Flag", disabled=True),
                    "status": st.column_config.SelectboxColumn(
                        "Status", options=STATUSES),
                },
                hide_index=True,
                use_container_width=True,
                key="register_editor",
            )

            # detect and persist changes (only editable columns matter)
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
