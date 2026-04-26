"""
Victory Road — Admin App v0.7
Features: Road types (Cohort/Personalize), Sprint types (foundation/practice), Score Entry, Performance Analytics
DB: Separate sprints table (v0.4 schema)
"""

import streamlit as st
import uuid
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta, time as dt_time
from dotenv import load_dotenv

load_dotenv()

from utils.db_client import (
    get_all_victory_roads, create_victory_road, update_victory_road,
    delete_victory_road, publish_victory_road,
    get_all_students, create_student, update_student, delete_student,
    get_all_teachers, create_teacher, update_teacher, delete_teacher,
    get_calendar_events, SUBJECT_COLORS, hash_password,
    upsert_student_performance,
    get_sim_open, set_sim_open,
    get_student_payments, upsert_student_payment,
    get_teacher_expenses, upsert_teacher_expense, delete_teacher_expense,
    update_sprint, get_sprint_attendance_batch, upsert_sprint_attendance,
    get_sprint_cover_url, upload_sprint_cover, DEFAULT_COVER_BY_SUBJECT,
)
from utils.analytics import (
    load_scores_df, build_subject_bar_chart, summarize_by_subject,
)
# streamlit_option_menu removed — using custom nav

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
st.set_page_config(page_title="Victory Academy", layout="wide")

st.markdown("""
<style>
/* ════════════════════════════════════════
   SIDEBAR — Light default
════════════════════════════════════════ */
section[data-testid="stSidebar"] > div:first-child {
    padding: 24px 10px 12px !important;
}

/* Nav buttons — flat text, hover only */
section[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: transparent !important;
    border: none !important;
    border-radius: 6px !important;
    color: #31333F !important;
    font-size: 1.05rem !important;
    font-weight: 400 !important;
    text-align: left !important;
    padding: 10px 14px !important;
    box-shadow: none !important;
    justify-content: flex-start !important;
    transition: background 0.12s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(0,0,0,0.06) !important;
    color: #0F0F0F !important;
}
section[data-testid="stSidebar"] .stButton > button:focus:not(:active) {
    box-shadow: none !important;
}

/* Active nav item */
section[data-testid="stSidebar"] .nav-active button {
    background: rgba(0,0,0,0.08) !important;
    font-weight: 600 !important;
    color: #0F0F0F !important;
}

/* Sidebar footer caption */
section[data-testid="stSidebar"] .stCaption p {
    color: #999 !important;
    font-size: 0.68rem !important;
    text-align: center !important;
    margin-top: 8px !important;
}

/* ════════════════════════════════════════
   MAIN CONTENT
════════════════════════════════════════ */
.main .block-container {
    padding-top: 2.2rem !important;
    padding-left: 2.8rem !important;
    padding-right: 2.8rem !important;
    max-width: 1080px !important;
}

/* Page titles */
.main h1 {
    font-size: 1.75rem !important;
    font-weight: 800 !important;
    color: #14142A !important;
    letter-spacing: -0.025em !important;
    line-height: 1.2 !important;
    margin-bottom: 0 !important;
}

/* Section headings */
.main h2 {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    color: #1E1E3A !important;
    letter-spacing: -0.01em !important;
}
.main h3 {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: #2A2A44 !important;
}

/* Cards / bordered containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border: 1px solid #EAEAF4 !important;
    box-shadow: 0 2px 8px rgba(0,0,20,0.06) !important;
    transition: box-shadow 0.15s ease !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 16px rgba(0,0,20,0.10) !important;
}

/* Primary buttons */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #E05252 0%, #C84040 100%) !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 10px rgba(224,82,82,0.30) !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 16px rgba(224,82,82,0.40) !important;
    transform: translateY(-1px) !important;
}

/* Secondary buttons */
.stButton > button[kind="secondary"] {
    border-radius: 9px !important;
    border: 1.5px solid #DCDCEE !important;
    color: #4A4A6A !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #E05252 !important;
    color: #E05252 !important;
    background: rgba(224,82,82,0.04) !important;
}

/* Dividers */
hr {
    border-color: #EDEDF8 !important;
    margin: 1rem 0 !important;
}

/* Streamlit info/warning/error boxes */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

SUBJECTS = ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ", "ภาษาไทย"]
LEVELS = [
    "ประถมศึกษาปีที่ 1", "ประถมศึกษาปีที่ 2", "ประถมศึกษาปีที่ 3",
    "ประถมศึกษาปีที่ 4", "ประถมศึกษาปีที่ 5", "ประถมศึกษาปีที่ 6",
    "มัธยมศึกษาปีที่ 1", "มัธยมศึกษาปีที่ 2", "มัธยมศึกษาปีที่ 3",
    "มัธยมศึกษาปีที่ 4", "มัธยมศึกษาปีที่ 5", "มัธยมศึกษาปีที่ 6",
]
# ── Sidebar navigation ──────────────────────────────────────
SIDEBAR_NAV_ITEMS = [
    ("Victory road",    "Victory Road"),
    ("Student",         "Student"),
    ("Teacher",         "Teacher"),
    ("Calendar",        "Calendar"),
    ("Financial",       "Financial"),
    ("Victory Partner", "Victory Partner"),
]

ALL_PAGES = [
    "Victory Road", "Student", "Teacher", "Calendar", "Financial",
    "ผลลัพธ์การสอน Victory Road", "Victory Partner",
]

SPRINT_TYPES  = ["สร้างพื้นฐาน", "เพิ่มความชำนาญ", "ทดสอบ"]
SPRINT_TO_KEY = {
    "สร้างพื้นฐาน":    "foundation",
    "เพิ่มความชำนาญ": "practice",
    "ทดสอบ":           "test",
    "Regular":         "regular",
}
SPRINT_TO_LABEL = {v: k for k, v in SPRINT_TO_KEY.items()}

COHORT_SPRINT_TYPES = ["Regular", "ทดสอบ"]

SUBJECT_CHART_COLOR = {
    "คณิตศาสตร์": "#FF6B6B",
    "วิทยาศาสตร์": "#4ECDC4",
    "ภาษาอังกฤษ":  "#45B7D1",
    "ภาษาไทย":     "#96CEB4",
}
SPRINT_DOT_COLOR = {
    "foundation": "#2ECC71",
    "practice":   "#3498DB",
    "test":       "#E67E22",
}


# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
def init_state():
    defaults = {
        "page":                "Victory Road",
        "vr_view":             "list",
        "editing_vr":          None,
        "viewing_vr":          None,
        "vr_detail_id":        None,
        "_open_create":        False,
        "form_sprints":        [],   # personal sprints (Personalize VR)
        "form_cohort_sprints": [],   # cohort parent sprints (Cohort VR)
        "form_vr_name":        "",
        "form_vr_description": "",
        "form_vr_level":       LEVELS[5],
        "form_road_type":      "cohort",
        "form_students":       [],
        "victory_roads":       [],
        "students":            [],
        "teachers":            [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # Migrate old page values that no longer exist
    if st.session_state.page not in ALL_PAGES:
        st.session_state.page = "Victory Road"

init_state()


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def new_sprint() -> dict:
    return {
        "id":             str(uuid.uuid4()),
        "name":           "",
        "date":           date.today(),
        "subject":        SUBJECTS[0],
        "sprint_type":    "foundation",
        "teacher":        "—",
        "start_time":     "16:30",
        "end_time":       "17:30",
        "lecture_link":   "",
        "ws_link":        "",
        "done":           False,
        "student_scores": {},
        "order_index":    0,
        "cover_photo":    "",
    }


def new_cohort_sprint() -> dict:
    """Cohort parent sprint — มีแค่ ชื่อ + ระดับ + sub_sprints"""
    return {
        "id":          str(uuid.uuid4()),
        "name":        "",
        "sprint_type": "regular",
        "order_index": 0,
        "sub_sprints": [],
    }


def _all_sprints(vr: dict) -> list:
    """คืน sprints ทั้งหมดของ VR (personal sprints + sub-sprints ของ cohort)
    ใช้สำหรับ calendar, analytics, score matrix
    """
    result = list(vr.get("sprints", []))
    for cs in vr.get("cohort_sprints", []):
        result.extend(cs.get("sub_sprints", []))
    return result


def calc_status(sprint) -> str:
    if sprint is None:
        return "not_start"
    if isinstance(sprint, dict):
        if sprint.get("done"):
            return "finished"
        sprint_date = sprint.get("date")
    else:
        sprint_date = sprint
    if not sprint_date:
        return "not_start"
    if isinstance(sprint_date, str):
        sprint_date = date.fromisoformat(sprint_date[:10])
    today = date.today()
    if sprint_date < today:
        return "finished"
    if sprint_date <= today + timedelta(days=3):
        return "incoming"
    return "not_start"


STATUS_BADGE = {
    "finished":  ("สำเร็จแล้ว",    "green"),
    "incoming":  ("กำลังจะมาถึง", "blue"),
    "not_start": ("ยังไม่เริ่ม",   "gray"),
}


def _nickname(student_entry) -> str:
    """
    'โอ๊ต: สมชาย ใจดี'                            → 'โอ๊ต'  (legacy string)
    {'id':..., 'nickname':'โอ๊ต', 'name':'...'}  → 'โอ๊ต'  (new object format)
    """
    if isinstance(student_entry, dict):
        return student_entry.get("nickname", "")
    s = str(student_entry)
    return s.split(":")[0].strip() if ":" in s else s.strip()


def _student_id(student_entry) -> str | None:
    """ดึง students.id จาก entry ใหม่ — legacy string คืน None"""
    if isinstance(student_entry, dict):
        return student_entry.get("id")
    return None


def sprint_duration_mins(sp: dict) -> int:
    """คำนวณเวลาสอน (นาที) จาก start_time/end_time หรือ minutes เดิม (backward compat)"""
    st_str = sp.get("start_time", "")
    et_str = sp.get("end_time", "")
    if st_str and et_str:
        try:
            sh, sm = map(int, st_str.split(":"))
            eh, em = map(int, et_str.split(":"))
            return max(0, (eh * 60 + em) - (sh * 60 + sm))
        except Exception:
            pass
    return int(sp.get("minutes") or 0)


def fmt_mins(m: int) -> str:
    """60 → '60 น.' | 90 → '1 ชม. 30 น.' | 120 → '2 ชม.'"""
    m = int(m or 0)
    if not m:
        return ""
    h, mins = divmod(m, 60)
    if h and mins:
        return f"{h} ชม. {mins} น."
    if h:
        return f"{h} ชม."
    return f"{mins} น."


def _to_date(d) -> date | None:
    if d is None:
        return None
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return date.fromisoformat(d[:10])
        except ValueError:
            return None
    return None


# ─────────────────────────────────────────
# ANALYTICS: Performance Chart (Personalize)
# ─────────────────────────────────────────
def render_performance_chart(sprints: list, student_nick: str):
    # Collect data per subject
    subject_data: dict[str, list] = {}

    for sp in sprints:
        scores = sp.get("student_scores", {}).get(student_nick, {})
        earned = scores.get("earned")
        max_s  = scores.get("max")
        if earned is None or not max_s:
            continue
        pct        = round(earned / max_s * 100, 1)
        sprint_key = sp.get("sprint_type", "worksheet")
        subj       = sp.get("subject", "")
        d          = _to_date(sp.get("date"))
        if d is None:
            continue
        subject_data.setdefault(subj, []).append((d, pct, sprint_key))

    if not subject_data:
        st.info("ยังไม่มีคะแนน — กรอกคะแนนด้านบนก่อนนะครับ")
        return

    fig = go.Figure()

    for subj, pts in subject_data.items():
        pts.sort(key=lambda x: x[0])
        dates      = [p[0] for p in pts]
        scores_pct = [p[1] for p in pts]
        types      = [p[2] for p in pts]
        subj_color = SUBJECT_CHART_COLOR.get(subj, "#888")

        # Connecting line per subject
        fig.add_trace(go.Scatter(
            x=dates, y=scores_pct,
            mode="lines",
            line=dict(color=subj_color, width=2, dash="dot"),
            showlegend=False,
            legendgroup=subj,
            hoverinfo="skip",
        ))

        # Points colored by sprint type
        for i, (d, s, t) in enumerate(pts):
            symbol = "circle"
            fig.add_trace(go.Scatter(
                x=[d], y=[s],
                mode="markers",
                marker=dict(
                    size=14 if t == "test" else 10,
                    color=SPRINT_DOT_COLOR.get(t, "#888"),
                    symbol=symbol,
                    line=dict(width=1.5, color="white"),
                ),
                name=subj if i == 0 else subj,
                showlegend=(i == 0),
                legendgroup=subj,
                hovertemplate=(
                    f"<b>{subj}</b><br>"
                    f"วันที่: %{{x}}<br>"
                    f"คะแนน: %{{y:.1f}}%<br>"
                    f"ประเภท: {SPRINT_TO_LABEL.get(t, t)}<extra></extra>"
                ),
            ))

        # Regression line (≥5 data points)
        if len(pts) >= 5:
            origin     = dates[0]
            date_nums  = [(d - origin).days for d in dates]
            coeffs     = np.polyfit(date_nums, scores_pct, 1)
            trend_fn   = np.poly1d(coeffs)
            future     = max(dates) + timedelta(days=30)
            future_num = (future - origin).days
            x_reg = [origin, future]
            y_reg = [float(trend_fn(0)), float(trend_fn(future_num))]
            fig.add_trace(go.Scatter(
                x=x_reg, y=y_reg,
                mode="lines",
                line=dict(color=subj_color, width=2.5, dash="dash"),
                name=f"แนวโน้ม {subj}",
                legendgroup=subj,
                hovertemplate=(
                    f"<b>แนวโน้ม {subj}</b><br>"
                    f"วันที่: %{{x}}<br>"
                    f"คาดการณ์: %{{y:.1f}}%<extra></extra>"
                ),
            ))

    fig.add_hline(y=80, line_dash="dash", line_color="green",
                  annotation_text="เป้าหมาย 80%", opacity=0.5)
    fig.add_hline(y=50, line_dash="dash", line_color="red",
                  annotation_text="เส้นผ่าน 50%", opacity=0.5)

    fig.update_layout(
        title=f"Performance Tracking: {student_nick}",
        xaxis_title="วันที่",
        yaxis_title="คะแนน (%)",
        yaxis=dict(range=[0, 110]),
        height=500,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Legend
    c1, c2 = st.columns(2)
    c1.markdown(
        "<span style='background:#2ECC71;color:white;padding:3px 10px;border-radius:4px'>สร้างพื้นฐาน</span>",
        unsafe_allow_html=True)
    c2.markdown(
        "<span style='background:#3498DB;color:white;padding:3px 10px;border-radius:4px'>เพิ่มความชำนาญ</span>",
        unsafe_allow_html=True)


# ─────────────────────────────────────────
# ANALYTICS: Radar Chart (Cohort)
# ─────────────────────────────────────────
def render_cohort_radar(score_row: dict, subjects: list, max_scores: dict):
    scores = [score_row.get(subj, 0) for subj in subjects]
    max_s  = [max_scores.get(subj, 1) for subj in subjects]
    pcts   = [s / m * 100 for s, m in zip(scores, max_s)]
    theta  = subjects + [subjects[0]]
    r      = pcts + [pcts[0]]
    fig = go.Figure(go.Scatterpolar(
        r=r, theta=theta, fill="toself",
        marker=dict(color="#45B7D1"),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=300, margin=dict(t=20, b=20, l=20, r=20),
    )
    return fig


# ─────────────────────────────────────────
# ANALYTICS VIEW: Unified Score Matrix
# ─────────────────────────────────────────
def render_score_matrix(vr: dict):
    """ตารางกรอกคะแนนแบบ matrix: แถว=นักเรียน, คอลัมน์=Sprint
    ใช้ได้ทั้ง Cohort และ Personalize
    """
    sprints  = _all_sprints(vr)
    students = vr.get("students", [])
    nicks    = [_nickname(s) for s in students]

    if not nicks:
        st.warning("ยังไม่มีนักเรียนใน Road นี้ครับ — กลับไปเพิ่มนักเรียนก่อนนะครับ")
        return
    if not sprints:
        st.info("ยังไม่มี Sprint ใน Road นี้ครับ")
        return

    # ── 1. วิเคราะห์แนวโน้มการเรียน (กราฟ) ─────────────────────
    st.markdown("### วิเคราะห์แนวโน้มการเรียน")
    chart_mode = st.radio(
        "มุมมอง",
        options=["ภาพรวม class", "รายบุคคล"],
        horizontal=True,
        key="chart_mode_radio",
    )

    if chart_mode == "ภาพรวม class":
        st.caption("เฉลี่ยจากนักเรียนทุกคนที่มีคะแนนใน Sprint นั้น")
        df          = load_scores_df(sprints, nickname=None)
        chart_title = f"คะแนนเฉลี่ยรายวิชา (ทั้ง class): {vr.get('name', '')}"
        chart_key   = "chart_cohort_bar"
    else:
        sel_nick    = st.selectbox("เลือกนักเรียน", nicks, key="chart_sel_nick")
        st.caption(f"คะแนนเฉลี่ยของ {sel_nick} แยกตามวิชา")
        df          = load_scores_df(sprints, nickname=sel_nick)
        chart_title = f"คะแนนรายวิชา: {sel_nick}"
        chart_key   = f"chart_student_bar_{sel_nick}"

    if df.empty:
        st.info("กรอกคะแนนนักเรียนแล้วกดบันทึก เพื่อดู chart ครับ")
    else:
        st.plotly_chart(
            build_subject_bar_chart(df, title=chart_title),
            use_container_width=True,
            key=chart_key,
        )
        st.dataframe(summarize_by_subject(df), hide_index=True, use_container_width=True)

    st.divider()

    # ── 2. ตารางสรุปคะแนน + การเข้าเรียน (รวมตาราง) ─────────────
    st.markdown("### ตารางสรุปคะแนน + การเข้าเรียน")
    st.caption("✅ = เข้าเรียน  ❌ = ขาด  — = n/a หรือยังไม่บันทึก")
    _att_batch_matrix = get_sprint_attendance_batch([str(sp["id"]) for sp in sprints])
    combined: dict = {"นักเรียน": nicks}
    for i, sp in enumerate(sprints):
        name_short = (sp.get("name") or "")[:10]
        col_key    = f"S{i+1}: {name_short}"
        sp_att     = _att_batch_matrix.get(str(sp["id"]), [])
        att_by_stu = {r["student_id"]: r["status"] for r in sp_att}
        col_vals   = []
        for s, nick in zip(vr.get("students", []), nicks):
            stu_id     = s.get("id") if isinstance(s, dict) else ""
            att_status = att_by_stu.get(stu_id, "")
            sc         = sp.get("student_scores", {}).get(nick, {})
            if sc and sc.get("max"):
                pct       = round(sc["earned"] / sc["max"] * 100)
                score_str = f"{sc['earned']:.0f}/{sc['max']:.0f} ({pct}%)"
            else:
                score_str = "—"
            if att_status == "n/a":
                col_vals.append("—")
            elif att_status == "present":
                col_vals.append(f"✅ {score_str}")
            elif att_status == "absent":
                col_vals.append(f"❌ {score_str}")
            else:
                col_vals.append(score_str)
        combined[col_key] = col_vals
    st.dataframe(pd.DataFrame(combined), hide_index=True, use_container_width=True)


# ─────────────────────────────────────────
# ANALYTICS VIEW: Personalize (legacy alias)
# ─────────────────────────────────────────
def render_personalize_analytics(vr: dict):
    render_score_matrix(vr)


# ─────────────────────────────────────────
# ANALYTICS VIEW: Cohort
# ─────────────────────────────────────────
def render_cohort_analytics(vr: dict):
    sprints  = _all_sprints(vr)
    students = vr.get("students", [])
    nicks    = [_nickname(s) for s in students]

    if not nicks:
        st.warning("ยังไม่มีนักเรียนใน Road นี้ครับ")
        return

    test_sprints = [s for s in sprints if s.get("sprint_type") == "test"]
    if not test_sprints:
        st.info("ยังไม่มี Sprint ทดสอบ — กลับไปเพิ่ม Sprint ประเภท ทดสอบ ก่อน")
        return

    test_sp = test_sprints[0]
    d_str   = _to_date(test_sp.get("date"))
    d_str   = d_str.strftime("%d/%m/%Y") if d_str else "—"
    st.markdown(f"### Sprint ทดสอบ: **{test_sp.get('name','—')}**  |  {d_str}")
    st.divider()

    # ── Config: subjects, topics, max scores ──
    with st.container(border=True):
        st.markdown("**ตั้งค่าการทดสอบ**")
        saved_subjects  = test_sp.get("cohort_subjects", [])
        saved_topics    = test_sp.get("cohort_topics",   {})
        saved_max       = test_sp.get("cohort_max_scores", {})

        selected_subjects = st.multiselect(
            "วิชาที่ทดสอบ", SUBJECTS,
            default=saved_subjects,
            key="cohort_subjects_sel",
        )

        topics     = {}
        max_scores = {}
        if selected_subjects:
            cols = st.columns(len(selected_subjects))
            for i, subj in enumerate(selected_subjects):
                with cols[i]:
                    st.markdown(f"**{subj}**")
                    topics[subj] = st.text_input(
                        "หัวข้อที่ทดสอบ", value=saved_topics.get(subj, ""),
                        key=f"c_topic_{subj}", placeholder="เช่น เศษส่วน")
                    max_scores[subj] = st.number_input(
                        "คะแนนเต็ม", value=float(saved_max.get(subj, 20.0)),
                        min_value=1.0, max_value=500.0, step=1.0,
                        key=f"c_max_{subj}")

    if not selected_subjects:
        st.info("เลือกวิชาที่ทดสอบก่อนนะครับ")
        return

    st.markdown("### กรอกคะแนนนักเรียน")

    # Build DataFrame: rows=students, cols=subjects
    saved_score_map = {row["alias"]: row for row in test_sp.get("cohort_scores", [])}
    rows = []
    for nick in nicks:
        r = {"นักเรียน": nick}
        for subj in selected_subjects:
            r[subj] = float(saved_score_map.get(nick, {}).get(subj, 0.0))
        rows.append(r)

    score_df = pd.DataFrame(rows)
    col_cfg  = {"นักเรียน": st.column_config.TextColumn("นักเรียน", disabled=True)}
    for subj in selected_subjects:
        m = max_scores.get(subj, 20)
        col_cfg[subj] = st.column_config.NumberColumn(
            f"{subj} (/{m:.0f})", min_value=0.0, max_value=m, step=0.5)

    edited_scores = st.data_editor(
        score_df, column_config=col_cfg,
        hide_index=True, use_container_width=True,
        key="cohort_score_editor",
    )

    if st.button("บันทึกคะแนน", type="primary", key="save_cohort"):
        new_scores = []
        for _, row in edited_scores.iterrows():
            entry = {"alias": row["นักเรียน"]}
            for subj in selected_subjects:
                entry[subj] = float(row[subj])
            new_scores.append(entry)

        updated_sprints = []
        for sp in sprints:
            if sp["id"] == test_sp["id"]:
                sp = {**sp,
                      "cohort_subjects":   selected_subjects,
                      "cohort_topics":     topics,
                      "cohort_max_scores": max_scores,
                      "cohort_scores":     new_scores}
            updated_sprints.append(sp)

        update_victory_road(vr["id"], {"sprints": updated_sprints})
        st.session_state.viewing_vr = {**vr, "sprints": updated_sprints}
        st.success("บันทึกคะแนนแล้ว")
        st.rerun()

    # ── Radar charts ──
    cohort_scores = test_sp.get("cohort_scores", [])
    if cohort_scores and selected_subjects:
        st.divider()
        st.markdown("### Radar Chart — ผลคะแนนรายนักเรียน")

        # Normalize scores to % per subject
        cols_per_row = 3
        score_rows_list = [r for r in cohort_scores if r.get("alias") in nicks]
        n = len(score_rows_list)
        for chunk_start in range(0, n, cols_per_row):
            cols = st.columns(cols_per_row)
            for j, score_row in enumerate(score_rows_list[chunk_start:chunk_start+cols_per_row]):
                nick = score_row.get("alias", "—")
                pcts = [round(score_row.get(subj, 0) / max(max_scores.get(subj, 1), 1) * 100, 1)
                        for subj in selected_subjects]
                avg  = round(sum(pcts) / len(pcts), 1) if pcts else 0
                with cols[j]:
                    st.markdown(f"**{nick}** — เฉลี่ย {avg:.1f}%")
                    fig = render_cohort_radar(score_row, selected_subjects, max_scores)
                    st.plotly_chart(fig, use_container_width=True, key=f"radar_{nick}")

        # Summary table
        st.markdown("### ตารางสรุปคะแนน")
        summary_rows = []
        for score_row in cohort_scores:
            nick = score_row.get("alias", "—")
            r    = {"นักเรียน": nick}
            total_earned = 0
            total_max    = 0
            for subj in selected_subjects:
                earned = score_row.get(subj, 0)
                mx     = max_scores.get(subj, 1)
                r[f"{subj} (%)"] = f"{earned:.1f} / {mx:.0f} ({earned/mx*100:.1f}%)"
                total_earned += earned
                total_max    += mx
            r["รวม (%)"] = f"{total_earned:.1f} / {total_max:.0f} ({total_earned/total_max*100:.1f}%)" if total_max else "—"
            summary_rows.append(r)
        st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)


# ─────────────────────────────────────────
# ANALYTICS VIEW: Main router
# ─────────────────────────────────────────
def render_analytics_view():
    vr = st.session_state.viewing_vr
    if not vr:
        st.session_state.viewing_vr = None
        st.rerun()

    col_back, _gap, col_title = st.columns([1.2, 0.3, 6.5])
    with col_back:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("กลับ", width="stretch"):
            st.session_state.viewing_vr = None
            st.rerun()
    with col_title:
        road_type = vr.get("road_type", "cohort")
        badge = "Cohort" if road_type == "cohort" else "Personalize"
        st.subheader(f"ผลลัพธ์การสอน: {vr['name']}  |  {badge}  |  {vr.get('level','')}")

    st.divider()

    # Refresh VR from DB to get latest scores
    all_vrs    = get_all_victory_roads()
    fresh_vr   = next((v for v in all_vrs if v["id"] == vr["id"]), vr)
    st.session_state.viewing_vr = fresh_vr

    render_score_matrix(fresh_vr)


@st.dialog("สร้าง Victory Road", width="large")
def dialog_create_vr():
    render_vr_form(mode="create")


@st.dialog("แก้ไข Victory Road", width="large")
def dialog_edit_vr():
    render_vr_form(mode="edit")


@st.dialog("รายละเอียด Sprint")
def dialog_sprint_detail():
    ev = st.session_state.get("_cal_clicked_ev", {})
    ep = st.session_state.get("_cal_clicked_ep", {})

    # ── ชื่อ VR (และ sub-sprint ถ้า cohort) ──
    st.markdown(f"## {ev.get('title', '')}")
    _rt_label = "Cohort" if ep.get("road_type") == "cohort" else "Personalize"
    st.markdown(
        f"<span style='color:#888;font-size:0.88rem'>"
        f"{ep.get('level','')}  ·  {_rt_label}"
        f"</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    _t_start = ep.get("start_time", "")
    _t_end   = ep.get("end_time", "")
    if _t_start and _t_end:
        st.markdown(f"🕐 **{_t_start} – {_t_end} น.**")

    if ep.get("sprint_type"):
        st.markdown(f"**ประเภท Sprint:** {ep['sprint_type']}")

    _teacher = ep.get("teacher", "")
    if _teacher and _teacher != "—":
        st.markdown(f"**ครูผู้สอน:** {_teacher}")

    if ep.get("subject"):
        st.markdown(f"**วิชา:** {ep['subject']}")

    if ep.get("road_type") == "personalize" and ep.get("students"):
        st.markdown(f"**นักเรียน:** {', '.join(ep['students'])}")

    if ep.get("lecture_link"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"[📖 เปิด Lecture]({ep['lecture_link']})")


# ─────────────────────────────────────────
# COMPONENT: Sprint Card
# ─────────────────────────────────────────
def render_sprint_card(sprint: dict, i: int, sprints: list,
                       key_prefix: str = "new", vr_level: str = LEVELS[5],
                       road_type: str = "cohort", teachers: list = None,
                       label_prefix: str = "Sprint",
                       rerun_scope: str = "app",
                       extra_state: dict = None,
                       allowed_sprint_types: list = None):
    """extra_state: session_state keys to set before every rerun (e.g. keep parent expander open)"""
    sid      = sprint["id"]
    p        = f"{key_prefix}_{sid}"
    d        = sprint.get("date")
    date_str = d.strftime("%d/%m/%Y") if isinstance(d, date) else (d[:10] if d else "-")
    label    = f"{label_prefix} {i+1}  |  {sprint['name'] or 'ยังไม่มีชื่อ'}  |  {date_str}"

    _exp_key  = f"sprint_exp_{p}"
    _expanded = st.session_state.get(_exp_key, False)

    def _keep_open():
        st.session_state[_exp_key] = True

    def _rerun():
        st.session_state[_exp_key] = True   # keep expander open across reruns
        if extra_state:
            st.session_state.update(extra_state)
        st.rerun(scope=rerun_scope)

    with st.expander(label, expanded=_expanded):
        ct, c1, c2, c3, c4a, c4b, c5 = st.columns([1.5, 2, 1.5, 1.2, 0.9, 0.9, 1.2])

        with ct:
            _avail_types = allowed_sprint_types if allowed_sprint_types else SPRINT_TYPES
            cur_label    = SPRINT_TO_LABEL.get(sprint.get("sprint_type", "foundation"), _avail_types[0])
            if cur_label not in _avail_types:          # auto-correct when parent type changed
                cur_label = _avail_types[0]
                sprint["sprint_type"] = SPRINT_TO_KEY[cur_label]
            idx_type = _avail_types.index(cur_label)
            chosen   = st.selectbox("ประเภท Sprint", _avail_types, index=idx_type,
                                    key=f"stype_{p}", on_change=_keep_open)
            sprint["sprint_type"] = SPRINT_TO_KEY[chosen]
        with c1:
            sprint["name"] = st.text_input(
                f"ชื่อ {label_prefix}", value=sprint["name"],
                key=f"sn_{p}", placeholder="เช่น เศษส่วน", on_change=_keep_open)
        with c2:
            if teachers is None:
                teachers = get_all_teachers()
            t_names  = ["—"] + [f"{t.get('nickname','')} ({t.get('name','')})" for t in teachers]
            cur_t    = sprint.get("teacher", "—")
            idx_t    = t_names.index(cur_t) if cur_t in t_names else 0
            sprint["teacher"] = st.selectbox("ครูผู้สอน", t_names, index=idx_t,
                                              key=f"st_{p}", on_change=_keep_open)
        with c3:
            if isinstance(d, str) and d:
                try:
                    d = date.fromisoformat(d[:10])
                except ValueError:
                    d = date.today()
            sprint["date"] = st.date_input(
                "วันที่", value=d if isinstance(d, date) else date.today(),
                key=f"sd_{p}", format="DD/MM/YYYY", on_change=_keep_open)
        with c4a:
            _st_str = sprint.get("start_time") or "16:30"
            try:
                _st_val = datetime.strptime(_st_str, "%H:%M").time()
            except Exception:
                _st_val = dt_time(16, 30)
            _t_start = st.time_input("เวลาเริ่ม", value=_st_val,
                                      key=f"tstart_{p}", step=900, on_change=_keep_open)
            sprint["start_time"] = _t_start.strftime("%H:%M")
        with c4b:
            _et_str = sprint.get("end_time") or "17:30"
            try:
                _et_val = datetime.strptime(_et_str, "%H:%M").time()
            except Exception:
                _et_val = dt_time(17, 30)
            _t_end = st.time_input("เวลาจบ", value=_et_val,
                                    key=f"tend_{p}", step=900, on_change=_keep_open)
            sprint["end_time"] = _t_end.strftime("%H:%M")
        with c5:
            cur_sub = sprint.get("subject", SUBJECTS[0])
            sprint["subject"] = st.selectbox(
                "วิชา", SUBJECTS,
                index=SUBJECTS.index(cur_sub) if cur_sub in SUBJECTS else 0,
                key=f"ss_{p}", on_change=_keep_open)

        # Links
        cl, cw = st.columns(2)
        with cl:
            st.markdown("**Lecture**")
            sprint["lecture_link"] = st.text_input(
                "lec", value=sprint.get("lecture_link", ""),
                key=f"lec_{p}", label_visibility="collapsed",
                placeholder="วาง Google Slides link", on_change=_keep_open)
            if sprint["lecture_link"]:
                st.markdown(f"[เปิด Lecture]({sprint['lecture_link']})")
        with cw:
            st.markdown("**Worksheet**")
            sprint["ws_link"] = st.text_input(
                "ws", value=sprint.get("ws_link", ""),
                key=f"ws_{p}", label_visibility="collapsed",
                placeholder="วาง Worksheet link", on_change=_keep_open)
            if sprint["ws_link"]:
                st.markdown(f"[เปิด Worksheet]({sprint['ws_link']})")

        # ── Cover Photo ──────────────────────────────────
        st.markdown("**Cover Photo**")
        _cv_url = get_sprint_cover_url(sprint)
        _cv_col_img, _cv_col_up = st.columns([1, 3])
        with _cv_col_img:
            if _cv_url:
                st.image(_cv_url, use_container_width=True)
            else:
                st.caption("(ไม่มีรูป)")
        with _cv_col_up:
            _cv_uploader = st.file_uploader(
                "อัปโหลด cover photo ใหม่",
                type=["png", "jpg", "jpeg"],
                key=f"cover_up_{p}",
                on_change=_keep_open,
            )
            if _cv_uploader is not None:
                if st.button("📤 บันทึก cover", key=f"cover_save_{p}"):
                    _ext   = _cv_uploader.name.rsplit(".", 1)[-1].lower()
                    _fname = f"custom_{sprint['id']}.{_ext}"
                    _url   = upload_sprint_cover(
                        _cv_uploader.read(), _fname, f"image/{_ext}"
                    )
                    if _url:
                        sprint["cover_photo"] = _url
                        st.success("✅ อัปโหลดแล้ว!")
                        _keep_open()
                    else:
                        st.error("อัปโหลดไม่สำเร็จ — ตรวจสอบ bucket permissions")
            else:
                _sub_name = sprint.get("subject", "")
                _def_file = DEFAULT_COVER_BY_SUBJECT.get(_sub_name, "")
                if _def_file and not sprint.get("cover_photo"):
                    st.caption(f"📌 ใช้ default: `{_def_file}`")

        st.markdown("---")
        cu, cd, _, cx = st.columns([1, 1, 5, 2])
        with cu:
            if i > 0 and st.button("↑", key=f"up_{p}"):
                sprints[i], sprints[i-1] = sprints[i-1], sprints[i]
                _rerun()
        with cd:
            if i < len(sprints)-1 and st.button("↓", key=f"dn_{p}"):
                sprints[i], sprints[i+1] = sprints[i+1], sprints[i]
                _rerun()
        with cx:
            _del_label   = "ลบ sub-sprint" if label_prefix == "Sub-sprint" else "ลบ sprint"
            _del_confirm = f"confirm_del_{p}"
            if not st.session_state.get(_del_confirm, False):
                if st.button(_del_label, key=f"del_{p}"):
                    st.session_state[_del_confirm] = True
                    st.session_state[_exp_key] = True   # keep expander open
            else:
                st.warning(f"{_del_label} นี้จริงๆ หรือ?")
                _cy, _cn = st.columns(2)
                with _cy:
                    if st.button("ยืนยัน ลบ", key=f"del_yes_{p}", type="primary"):
                        # ── ลบตรงจาก session_state — natural rerun handles display ──
                        _sid = sprint["id"]
                        _ss_sprints = st.session_state.get("form_sprints", [])
                        if any(s["id"] == _sid for s in _ss_sprints):
                            st.session_state["form_sprints"] = [
                                s for s in _ss_sprints if s["id"] != _sid
                            ]
                        else:
                            for _cs in st.session_state.get("form_cohort_sprints", []):
                                _subs = _cs.get("sub_sprints", [])
                                if any(s["id"] == _sid for s in _subs):
                                    _cs["sub_sprints"] = [s for s in _subs if s["id"] != _sid]
                                    break
                        st.session_state.pop(_del_confirm, None)
                with _cn:
                    if st.button("ยกเลิก", key=f"del_no_{p}"):
                        st.session_state.pop(_del_confirm, None)
                        st.session_state[_exp_key] = True   # keep expander open


# ─────────────────────────────────────────
# COMPONENT: Cohort Sprint Card (parent)
# ─────────────────────────────────────────
@st.fragment
def render_cohort_sprint_card(cs: dict, i: int, cohort_sprints: list,
                               key_prefix: str = "form", teachers: list = None,
                               vr_level: str = LEVELS[5]):
    """Card สำหรับ Cohort parent sprint — แสดงแค่ ชื่อ + ระดับ + sub-sprints"""
    cid   = cs["id"]
    p     = f"{key_prefix}_{cid}"
    n_sub = len(cs.get("sub_sprints", []))
    cur_type_label = SPRINT_TO_LABEL.get(cs.get("sprint_type", "regular"), COHORT_SPRINT_TYPES[0])
    label = f"Sprint {i+1}  [{cur_type_label}]  |  {cs['name'] or 'ยังไม่มีชื่อ'}  |  {n_sub} sub-sprint"

    _exp_key = f"cohort_exp_{cid}"
    _expanded = st.session_state.get(_exp_key, False)

    def _keep_open(k=_exp_key):
        st.session_state[k] = True

    def _frag_rerun(k=_exp_key):
        st.session_state[k] = True
        st.rerun(scope="fragment")

    with st.expander(label, expanded=_expanded):
        c1, c2 = st.columns([1.5, 3])
        with c1:
            idx_type = COHORT_SPRINT_TYPES.index(cur_type_label) if cur_type_label in COHORT_SPRINT_TYPES else 0
            chosen   = st.selectbox("ระดับ Sprint", COHORT_SPRINT_TYPES, index=idx_type,
                                    key=f"cstype_{p}", on_change=_keep_open)
            cs["sprint_type"] = SPRINT_TO_KEY[chosen]
        with c2:
            cs["name"] = st.text_input(
                "ชื่อ Sprint", value=cs.get("name", ""),
                key=f"csn_{p}", placeholder="เช่น ปูพื้นฐานเศษส่วน",
                on_change=_keep_open)

        st.markdown("---")
        sub_sprints = cs.setdefault("sub_sprints", [])
        st.markdown(f"**Sub-sprints ({len(sub_sprints)} sub-sprint)**")
        _cs_type = cs.get("sprint_type", "regular")
        if _cs_type == "test":
            _allowed_sub = ["ทดสอบ"]
        else:   # regular / foundation / etc.
            _allowed_sub = ["สร้างพื้นฐาน", "เพิ่มความชำนาญ"]
        for k, sub in enumerate(sub_sprints):
            render_sprint_card(sub, k, sub_sprints,
                               key_prefix=f"sub_{cid}",
                               vr_level=vr_level,
                               road_type="cohort",
                               teachers=teachers,
                               label_prefix="Sub-sprint",
                               rerun_scope="fragment",
                               extra_state={_exp_key: True},
                               allowed_sprint_types=_allowed_sub)
        if st.button("+ เพิ่ม Sub-sprint", key=f"add_sub_{p}"):
            sub_sprints.append(new_sprint())
            _frag_rerun()

        st.markdown("---")
        cu, cd, _, cx = st.columns([1, 1, 5, 2])
        with cu:
            if i > 0 and st.button("↑", key=f"cup_{p}"):
                cohort_sprints[i], cohort_sprints[i-1] = cohort_sprints[i-1], cohort_sprints[i]
                _frag_rerun()
        with cd:
            if i < len(cohort_sprints) - 1 and st.button("↓", key=f"cdn_{p}"):
                cohort_sprints[i], cohort_sprints[i+1] = cohort_sprints[i+1], cohort_sprints[i]
                _frag_rerun()
        with cx:
            _cdel_confirm = f"confirm_cdel_{p}"
            if not st.session_state.get(_cdel_confirm, False):
                if st.button("ลบ sprint", key=f"cdel_{p}"):
                    st.session_state[_cdel_confirm] = True
                    _frag_rerun()
            else:
                st.warning("ลบ sprint นี้จริงๆ หรือ?")
                _cy, _cn = st.columns(2)
                with _cy:
                    if st.button("ยืนยัน ลบ", key=f"cdel_yes_{p}", type="primary"):
                        # ── ลบตรงจาก session_state เพราะ fragment args เป็น copy ──
                        st.session_state["form_cohort_sprints"] = [
                            c for c in st.session_state.get("form_cohort_sprints", [])
                            if c["id"] != cid
                        ]
                        del st.session_state[_cdel_confirm]
                        st.rerun(scope="fragment")
                with _cn:
                    if st.button("ยกเลิก", key=f"cdel_no_{p}"):
                        del st.session_state[_cdel_confirm]
                        _frag_rerun()


# ─────────────────────────────────────────
# COMPONENT: VR Form
# ─────────────────────────────────────────
def render_vr_form(mode: str = "create"):
    is_edit = mode == "edit"
    st.subheader("แก้ไข Victory Road" if is_edit else "สร้าง Victory Road ใหม่")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.session_state.form_vr_name = st.text_input(
            "ชื่อ Victory Road *", value=st.session_state.form_vr_name,
            placeholder="เช่น Primary 6 (Mon–Thu) มีนาคม 2025")
    with c2:
        idx = LEVELS.index(st.session_state.form_vr_level) if st.session_state.form_vr_level in LEVELS else 5
        st.session_state.form_vr_level = st.selectbox("ระดับชั้น", LEVELS, index=idx)
    with c3:
        cur_rt  = st.session_state.get("form_road_type", "cohort")
        rt_lbl  = st.radio("ประเภท Road", ["Cohort", "Personalize"],
                           index=0 if cur_rt == "cohort" else 1, horizontal=True)
        st.session_state.form_road_type = "cohort" if rt_lbl == "Cohort" else "personalize"

    st.session_state.form_vr_description = st.text_area(
        "คำอธิบาย Victory Road",
        value=st.session_state.get("form_vr_description", ""),
        placeholder="เช่น กลุ่มเรียนคณิตศาสตร์ ม.3 เน้นเตรียมสอบ O-NET ปี 2568",
        height=80,
    )

    road_type = st.session_state.form_road_type

    st.markdown("---")
    _form_teachers = get_all_teachers()

    if road_type == "cohort":
        n = len(st.session_state.form_cohort_sprints)
        st.markdown(f"**Sprint ({n} sprint)**")
        for i, cs in enumerate(st.session_state.form_cohort_sprints):
            render_cohort_sprint_card(cs, i, st.session_state.form_cohort_sprints,
                                      key_prefix="form", teachers=_form_teachers,
                                      vr_level=st.session_state.form_vr_level)
        if st.button("เพิ่ม Sprint", width="stretch"):
            st.session_state.form_cohort_sprints.append(new_cohort_sprint())
    else:
        n = len(st.session_state.form_sprints)
        st.markdown(f"**Sprint ({n} sprint)**")
        for i, sp in enumerate(st.session_state.form_sprints):
            render_sprint_card(sp, i, st.session_state.form_sprints,
                               key_prefix="form", vr_level=st.session_state.form_vr_level,
                               road_type=road_type, teachers=_form_teachers)
        if st.button("เพิ่ม Sprint", width="stretch"):
            st.session_state.form_sprints.append(new_sprint())

    # Student selection
    if True:
        st.markdown("---")
        st.markdown("**เลือกนักเรียน**")
        all_students_db = get_all_students()
        # pool = display strings "nickname: name surname"
        pool        = [f"{s.get('nickname','')}: {s.get('name','')} {s.get('surname','')}".strip() for s in all_students_db]
        student_map = {
            f"{s.get('nickname','')}: {s.get('name','')} {s.get('surname','')}".strip(): s
            for s in all_students_db
        }
        if pool:
            prev = st.session_state.get("form_students", [])
            # normalize prev: ถ้าเป็น dict (new format) แปลงเป็น display string
            prev_display = []
            for p in prev:
                if isinstance(p, dict):
                    prev_display.append(f"{p.get('nickname','')}: {p.get('name','')}".strip())
                else:
                    prev_display.append(str(p))
            st.session_state.form_students = st.multiselect(
                "เลือกนักเรียนที่จะเห็น Victory Road นี้", pool,
                default=[x for x in prev_display if x in pool], key="form_student_sel")
            st.session_state._student_map = student_map  # ใช้ตอน save
        else:
            st.caption("ยังไม่มีนักเรียน — ไปเพิ่มที่เมนู Student ก่อนนะครับ")
            st.session_state.form_students = []
            st.session_state._student_map  = {}

    st.divider()
    cs, cc = st.columns([4, 1])
    with cs:
        btn_label = "บันทึกการแก้ไข" if is_edit else "สร้าง Victory Road"
        if st.button(btn_label, type="primary", width="stretch"):
            if not st.session_state.form_vr_name:
                st.error("กรุณาใส่ชื่อ Victory Road ก่อนนะครับ")
            else:
                sprints_to_save = [
                    {**sp, "order_index": i}
                    for i, sp in enumerate(st.session_state.form_sprints)
                ]
                # แปลง display strings → object format [{id, nickname, name}]
                _smap = st.session_state.get("_student_map", {})
                students_out = []
                for display in st.session_state.get("form_students", []):
                    s = _smap.get(display)
                    if s:
                        students_out.append({
                            "id":       s["id"],
                            "nickname": s.get("nickname", ""),
                            "name":     f"{s.get('name','')} {s.get('surname','')}".strip(),
                        })
                    else:
                        # fallback: legacy string (ไม่ควรเกิด แต่ safe)
                        students_out.append(display)

                if road_type == "cohort":
                    cohort_sprints_to_save = [
                        {**cs, "order_index": i}
                        for i, cs in enumerate(st.session_state.form_cohort_sprints)
                    ]
                    sprints_to_save = []
                else:
                    cohort_sprints_to_save = []

                payload = {
                    "name":        st.session_state.form_vr_name,
                    "description": st.session_state.get("form_vr_description", ""),
                    "level":          st.session_state.form_vr_level,
                    "road_type":      road_type,
                    "sprints":        sprints_to_save,
                    "cohort_sprints": cohort_sprints_to_save,
                    "students":       students_out,
                    "status":         st.session_state.editing_vr.get("status", "draft") if is_edit else "draft",
                }
                if is_edit:
                    update_victory_road(st.session_state.editing_vr["id"], payload)
                    st.success("บันทึกการแก้ไขสำเร็จ")
                else:
                    create_victory_road(payload)
                    st.success(f"สร้าง '{payload['name']}' สำเร็จ")
                st.session_state.update({
                    "vr_view": "list", "editing_vr": None,
                    "form_sprints": [], "form_cohort_sprints": [],
                    "form_vr_name": "", "form_vr_description": "", "form_students": [],
                    "page": "Victory Road",
                })
                st.rerun()
    with cc:
        if st.button("ยกเลิก", width="stretch"):
            st.session_state.update({
                "vr_view": "list", "editing_vr": None,
                "form_sprints": [], "form_cohort_sprints": [],
                "form_vr_name": "", "form_vr_description": "", "page": "Victory Road",
            })
            st.rerun()

    # ── Delete (edit mode only) ────────────────────────
    if is_edit and st.session_state.editing_vr:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#bbb;font-size:0.78rem;margin-bottom:4px'>"
            "Danger Zone</p>",
            unsafe_allow_html=True,
        )
        if st.button(
            "ลบ Victory Road นี้",
            key="delete_vr_btn",
            type="secondary",
            use_container_width=True,
            help="กดเพื่อลบ — ไม่สามารถกู้คืนได้",
        ):
            delete_victory_road(st.session_state.editing_vr["id"])
            st.session_state.update({
                "vr_view": "list", "editing_vr": None,
                "form_sprints": [], "form_cohort_sprints": [],
                "form_vr_name": "", "form_vr_description": "", "page": "Victory Road",
            })
            st.rerun()


# ─────────────────────────────────────────
# FRAGMENT HELPER
# ─────────────────────────────────────────
# st.fragment ใช้ได้ตั้งแต่ Streamlit 1.33+ — fallback เป็น no-op decorator
_fragment = st.fragment if hasattr(st, "fragment") else (lambda f: f)


@_fragment
def render_sprint_attendance_fragment(sp: dict, vr_students: list, att_records: list):
    """Isolated fragment: data_editor interactions ไม่ rerun ทั้งหน้า
    เฉพาะ save button เท่านั้นที่ rerun ทั้ง app เพื่อ refresh ข้อมูล
    """
    sprint_id = str(sp["id"])
    is_done   = sp.get("done", False)
    scores_data = sp.get("student_scores", {})

    att_map = {r["student_id"]: r for r in att_records}

    # ── ตั้งคะแนนเต็มทุกคนพร้อมกัน ───────────────
    col_mx, col_mx_hint = st.columns([1, 4])
    with col_mx:
        set_max = st.number_input(
            "คะแนนเต็ม (ทุกคน)",
            min_value=0.0, max_value=500.0, step=1.0, value=0.0,
            key=f"set_max_{sprint_id}",
        )
    with col_mx_hint:
        st.markdown("<br>", unsafe_allow_html=True)
        if set_max > 0:
            st.caption(f"จะตั้งคะแนนเต็ม {set_max:.0f} ให้ทุกคนเมื่อบันทึก")
        else:
            st.caption("ใส่ค่า > 0 เพื่อตั้งคะแนนเต็มให้ทุกคนพร้อมกัน")

    # ── Merged data_editor ────────────────────────
    merged_rows = []
    for stu in vr_students:
        rec  = att_map.get(stu["id"], {})
        nick = stu.get("nickname", stu.get("name", ""))
        sc   = scores_data.get(nick, {})
        default_max = set_max if set_max > 0 else float(sc.get("max", 10))
        merged_rows.append({
            "นักเรียน":        nick,
            "สถานะ":           rec.get("status", "absent"),
            "ได้คะแนน":        float(sc.get("earned", 0)),
            "คะแนนเต็ม":       default_max,
            "Feedback จากครู": rec.get("teacher_feedback", ""),
            "Worksheet นักเรียน": rec.get("student_ws_link", ""),
            "_student_id":     stu["id"],
        })

    edited = st.data_editor(
        pd.DataFrame(merged_rows)[
            ["นักเรียน", "สถานะ", "ได้คะแนน", "คะแนนเต็ม", "Worksheet นักเรียน"]
        ],
        hide_index=True,
        use_container_width=True,
        column_config={
            "นักเรียน":        st.column_config.TextColumn(
                "นักเรียน", disabled=True, width="small"
            ),
            "สถานะ":           st.column_config.SelectboxColumn(
                "สถานะ", options=["present", "absent", "n/a"], width="small"
            ),
            "ได้คะแนน":        st.column_config.NumberColumn(
                "ได้คะแนน", min_value=0.0, step=0.5, width="small"
            ),
            "คะแนนเต็ม":       st.column_config.NumberColumn(
                "คะแนนเต็ม", min_value=0.0, step=1.0, width="small"
            ),
            "Worksheet นักเรียน": st.column_config.LinkColumn(
                "Worksheet นักเรียน",
                help="วาง link worksheet ที่นักเรียนส่ง",
                display_text="เปิด",
                width="small",
            ),
        },
        key=f"att_editor_{sprint_id}",
    )

    # สรุปการเข้าเรียน
    present_n = sum(1 for _, r in edited.iterrows() if r["สถานะ"] == "present")
    countable = sum(1 for _, r in edited.iterrows() if r["สถานะ"] != "n/a")
    pct_att   = round(present_n / countable * 100) if countable else 0
    st.caption(
        f"เข้าเรียน **{present_n}/{countable}** คน ({pct_att}%)"
        + ("  |  มี n/a (ไม่นับ)" if countable < len(merged_rows) else "")
    )

    # ── บันทึกทั้งคู่ในปุ่มเดียว ─────────────────
    if st.button(
        "บันทึกการเข้าเรียน + คะแนน",
        key=f"save_att_{sprint_id}",
        type="primary",
        use_container_width=True,
    ):
        new_scores = {}
        for i_row, row in edited.iterrows():
            stu_id = merged_rows[i_row]["_student_id"]
            upsert_sprint_attendance(
                sprint_id, stu_id,
                row["สถานะ"],
                merged_rows[i_row].get("Feedback จากครู", ""),  # คงค่า feedback เดิมจากครู
                row.get("Worksheet นักเรียน", ""),
            )
            nick = merged_rows[i_row]["นักเรียน"]
            new_scores[nick] = {
                "earned": float(row["ได้คะแนน"]),
                "max":    float(row["คะแนนเต็ม"]),
            }
        update_sprint(sprint_id, {"student_scores": new_scores})
        st.success("บันทึกแล้ว")
        st.rerun()

    # ── Confirm จบ Sprint ─────────────────────────
    st.markdown("---")
    if not is_done:
        if st.button(
            "Confirm จบ Sprint",
            key=f"confirm_done_{sprint_id}",
            type="primary",
            use_container_width=True,
        ):
            update_sprint(sprint_id, {"done": True})
            st.success("Sprint จบแล้ว")
            st.rerun()
    else:
        if st.button(
            "Reopen Sprint",
            key=f"reopen_{sprint_id}",
            use_container_width=True,
        ):
            update_sprint(sprint_id, {"done": False})
            st.rerun()


# ─────────────────────────────────────────
# LOGIN GATE
# ─────────────────────────────────────────
def _check_login():
    if st.session_state.get("authenticated"):
        return
    # ซ่อน sidebar ในหน้า login
    st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stAppViewContainer"] { background: #F1F5F9; }
        </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([2, 3, 2])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        import os as _los
        _logo_login = _los.path.join(_los.path.dirname(__file__), "assets", "logos", "BDxVA.png")
        if _los.path.exists(_logo_login):
            st.image(_logo_login, use_container_width=True)
        st.markdown(
            "<p style='text-align:center;color:#64748B;margin:0.5rem 0 1.5rem;font-size:0.95rem'>Admin System</p>",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.markdown("#### เข้าสู่ระบบ")
            _uname = st.text_input("Username", placeholder="กรอก username", key="_login_user")
            _pw    = st.text_input("Password", type="password", placeholder="กรอก password", key="_login_pw")
            if st.button("เข้าสู่ระบบ", type="primary", use_container_width=True):
                _ok_u = st.secrets.get("APP_USERNAME", "")
                _ok_p = st.secrets.get("APP_PASSWORD", "")
                if _uname == _ok_u and _pw == _ok_p:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Username หรือ Password ไม่ถูกต้อง")
    st.stop()

_check_login()


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
import os as _os

with st.sidebar:
    _cur_page = st.session_state.page

    # ── Logo ──────────────────────────────────────────
    _logo_path = _os.path.join(_os.path.dirname(__file__), "assets", "logos", "BDxVA.png")
    if _os.path.exists(_logo_path):
        st.markdown("""
            <style>
            [data-testid="stSidebar"] [data-testid="stImage"] img {
                margin-left: -1.5rem;
                width: calc(100% + 3rem) !important;
                max-width: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        st.image(_logo_path, use_container_width=True)
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    # ── Nav items ─────────────────────────────────────
    # Only ONE item can be active → key="nav-active" is unique per render
    _vp_open = get_sim_open()
    for _label, _target in SIDEBAR_NAV_ITEMS:
        _is_active = _cur_page == _target
        _ckey = "nav-active" if _is_active else f"nav-{_target.lower().replace(' ', '-')}"

        if _target == "Victory Partner":
            # Show nav button + pill indicator side by side
            _pill_bg    = "#16a34a" if _vp_open else "#D1D5DB"
            _knob_side  = "right:2px" if _vp_open else "left:2px"
            _pill_title = "เปิดใช้งาน" if _vp_open else "ปิดใช้งาน"
            _nav_col, _pill_col = st.columns([5, 1.4])
            with _nav_col:
                with st.container(key=_ckey):
                    if st.button(_label, key=f"navbtn-{_target}", use_container_width=True):
                        st.session_state.page         = _target
                        st.session_state.vr_view      = "list"
                        st.session_state.vr_detail_id = None
                        st.session_state.viewing_vr   = None
                        st.rerun()
            with _pill_col:
                st.markdown(
                    f"""<div title="{_pill_title}" style="
                        display:flex;align-items:center;
                        justify-content:center;height:42px;">
                        <div style="
                            width:34px;height:20px;border-radius:10px;
                            background:{_pill_bg};position:relative;
                            box-shadow:inset 0 1px 2px rgba(0,0,0,0.15);flex-shrink:0;">
                            <div style="
                                width:15px;height:15px;border-radius:50%;
                                background:#fff;position:absolute;top:2.5px;{_knob_side};
                                box-shadow:0 1px 3px rgba(0,0,0,0.25);">
                            </div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            with st.container(key=_ckey):
                if st.button(_label, key=f"navbtn-{_target}", use_container_width=True):
                    st.session_state.page         = _target
                    st.session_state.vr_view      = "list"
                    st.session_state.vr_detail_id = None
                    st.session_state.viewing_vr   = None
                    st.rerun()

    # ── Logout ───────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔓 ออกจากระบบ", use_container_width=True, key="sidebar_logout"):
        st.session_state.authenticated = False
        st.rerun()

    # ── Footer ────────────────────────────────────────
    _mode = "Supabase" if _os.getenv("SUPABASE_URL") else "Local"
    st.caption(f"v0.7  ·  {_mode}")


# ═══════════════════════════════════════════════════════
# PAGE: Victory Road
# ═══════════════════════════════════════════════════════
if st.session_state.page == "Victory Road":

    # ── Trigger create dialog from sidebar ─────────────
    if st.session_state.pop("_open_create", False):
        dialog_create_vr()

    if st.session_state.vr_view == "edit":
        dialog_edit_vr()
        st.session_state.vr_view = "list"

    elif st.session_state.get("vr_detail_id"):
        # ── Detail view ──────────────────────────────────
        all_vrs = get_all_victory_roads()
        detail_vr = next((v for v in all_vrs if str(v["id"]) == str(st.session_state.vr_detail_id)), None)
        if not detail_vr:
            st.session_state.vr_detail_id = None
            st.rerun()

        # ── Page header ──────────────────────────────────
        if st.button("← กลับ"):
            st.session_state.vr_detail_id = None
            st.rerun()
        road_type = detail_vr.get("road_type", "cohort")
        badge     = "Cohort" if road_type == "cohort" else "Personalize"
        st.subheader(f"{detail_vr['name']}  ·  {badge}  ·  {detail_vr.get('level','')}")

        # ── Common data ──────────────────────────────────
        road_type_detail = detail_vr.get("road_type", "cohort")
        cohort_sprints   = detail_vr.get("cohort_sprints", [])
        personal_sprints = detail_vr.get("sprints", [])
        vr_students      = [s for s in detail_vr.get("students", [])
                            if isinstance(s, dict) and s.get("id")]

        _all_sprint_ids = [str(sp["id"]) for sp in personal_sprints]
        for cs in cohort_sprints:
            for sub in cs.get("sub_sprints", []):
                _all_sprint_ids.append(str(sub["id"]))
        _att_batch = get_sprint_attendance_batch(_all_sprint_ids)

        # ── Sprint card helper ────────────────────────────
        def _render_sprint_card(sp: dict, label: str, vr_id: str):
            d_raw = sp.get("date", "")
            try:
                d_str  = (d_raw[:10] if isinstance(d_raw, str)
                          else d_raw.strftime("%Y-%m-%d") if d_raw else "")
                d_disp = (datetime.strptime(d_str, "%Y-%m-%d").strftime("%d/%m/%Y")
                          if d_str else "—")
            except Exception:
                d_disp = str(d_raw)[:10] if d_raw else "—"

            st_key                  = calc_status(sp)
            badge_text, badge_color = STATUS_BADGE.get(st_key, ("?", "gray"))
            is_done                 = sp.get("done", False)
            sprint_type_label       = SPRINT_TO_LABEL.get(sp.get("sprint_type", "foundation"), "")
            teacher                 = sp.get("teacher", "—") or "—"
            subject                 = sp.get("subject", "") or "—"
            start_t                 = sp.get("start_time", "")
            end_t                   = sp.get("end_time", "")
            time_str                = (f"{start_t} – {end_t}" if start_t and end_t
                                       else fmt_mins(sprint_duration_mins(sp)))
            lec_link                = sp.get("lecture_link", "")
            ws_link                 = sp.get("ws_link", "")
            status_icon             = "✅" if is_done else ("🔵" if st_key == "incoming" else "⬜")

            with st.container(border=True):
                # ── Row 1: label + name + status badge + done toggle ──
                col_name, col_toggle = st.columns([6, 2])
                with col_name:
                    st.markdown(
                        f"{status_icon} &nbsp;**{label}** &nbsp;·&nbsp; {sp.get('name','?')}"
                        f"&nbsp;&nbsp;:{badge_color}[{badge_text}]&nbsp;&nbsp;`{sprint_type_label}`",
                        unsafe_allow_html=True,
                    )
                with col_toggle:
                    _done_lbl = "✅ จบแล้ว" if is_done else "⬜ ยังไม่จบ"
                    if st.button(_done_lbl, key=f"qdone_{vr_id}_{sp['id']}",
                                 use_container_width=True,
                                 type="primary" if is_done else "secondary"):
                        update_sprint(str(sp["id"]), {"done": not is_done})
                        st.rerun()

                # ── Row 2: date / time / teacher / subject ──
                st.caption(f"📅 {d_disp}   🕐 {time_str}   👨‍🏫 {teacher}   📚 {subject}")

                # ── Row 3: links (only if present) ──
                link_parts = []
                if lec_link:
                    link_parts.append(f"[📹 Lecture]({lec_link})")
                if ws_link:
                    link_parts.append(f"[📝 Worksheet]({ws_link})")
                if link_parts:
                    st.markdown("  ·  ".join(link_parts))

                # ── Attendance / score expander ──
                if vr_students:
                    with st.expander("📝 เช็คชื่อ / บันทึกคะแนน", expanded=False):
                        render_sprint_attendance_fragment(
                            sp, vr_students, _att_batch.get(str(sp["id"]), [])
                        )

        # ── Tabs ─────────────────────────────────────────
        tab_analytics, tab_teaching = st.tabs(["📊 ผลการเรียน", "📋 บันทึกการสอน"])

        # ── Tab 2: บันทึกการสอน ──────────────────────────
        with tab_teaching:
            vr_id = detail_vr["id"]
            if road_type_detail == "cohort":
                if not cohort_sprints:
                    st.info("ยังไม่มี Sprint ใน Victory Road นี้")
                else:
                    for j, cs in enumerate(cohort_sprints):
                        cs_type_label = SPRINT_TO_LABEL.get(cs.get("sprint_type", "foundation"), "")
                        cs_name       = cs.get("name", "?")
                        # Parent sprint — styled section header
                        st.markdown(
                            f"<div style='background:#EFF6FF;border-left:4px solid #3B82F6;"
                            f"padding:10px 16px;border-radius:6px;margin:14px 0 6px 0'>"
                            f"<span style='font-size:1rem;font-weight:700;color:#1E3A8A'>"
                            f"Sprint {j+1}: {cs_name}</span>"
                            f"&nbsp;&nbsp;<span style='font-size:0.8rem;color:#64748B;"
                            f"background:#DBEAFE;padding:2px 8px;border-radius:10px'>"
                            f"{cs_type_label}</span></div>",
                            unsafe_allow_html=True,
                        )
                        subs = cs.get("sub_sprints", [])
                        if subs:
                            for k, sub in enumerate(subs):
                                _render_sprint_card(sub, f"Sub-sprint {k+1}", vr_id)
                        else:
                            st.caption("ยังไม่มี Sub-sprint ใน Sprint นี้")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                if not personal_sprints:
                    st.info("ยังไม่มี Sprint ใน Victory Road นี้")
                else:
                    for j, sp in enumerate(personal_sprints):
                        _render_sprint_card(sp, f"Sprint {j+1}", vr_id)

        # ── Tab 1: ผลการเรียน ────────────────────────────
        with tab_analytics:
            render_score_matrix(detail_vr)

    else:
        # ── List view ──
        col_title, col_btn = st.columns([4, 1])
        with col_title:
            st.title("Victory Road")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("+ สร้าง Victory Road", type="primary", width="stretch"):
                st.session_state.update({
                    "form_sprints": [], "form_cohort_sprints": [],
                    "form_vr_name": "", "form_vr_level": LEVELS[5],
                    "form_road_type": "cohort",
                })
                dialog_create_vr()

        st.divider()
        vrs = get_all_victory_roads()

        if not vrs:
            st.info("ยังไม่มี Victory Road — กดปุ่ม '+ สร้าง Victory Road' ด้านบนได้เลย")
        else:
            for vr in vrs:
                all_sp     = _all_sprints(vr)
                n_cohort   = len(vr.get("cohort_sprints", []))
                finished   = sum(1 for s in all_sp if calc_status(s) == "finished")
                incoming   = sum(1 for s in all_sp if calc_status(s) == "incoming")
                total_mins = sum(sprint_duration_mins(s) for s in all_sp)
                road_type  = vr.get("road_type", "cohort")
                rt_badge   = "Cohort" if road_type == "cohort" else "Personalize"
                hrs_label  = fmt_mins(total_mins) if total_mins else ""
                sprint_summary = (f"{n_cohort} sprint ({len(all_sp)} sub-sprint)"
                                  if road_type == "cohort"
                                  else f"{len(all_sp)} sprint")

                with st.container(border=True):
                    col_info, col_btns = st.columns([5, 1])
                    with col_info:
                        not_started = len(all_sp) - finished - incoming
                        _desc = vr.get("description", "")
                        st.markdown(
                            f"<div style='line-height:1.7'>"
                            f"<div style='font-size:1.05rem;font-weight:700;color:#14142A'>{vr['name']}</div>"
                            f"<div style='font-size:0.82rem;color:#888;margin-top:1px'>{rt_badge}  ·  {vr.get('level','')}</div>"
                            + (f"<div style='font-size:0.83rem;color:#475569;margin-top:3px'>{_desc}</div>" if _desc else "")
                            + f"<div style='font-size:0.82rem;color:#555;margin-top:2px'>"
                            f"{sprint_summary}"
                            f"{'  ·  ' + hrs_label if hrs_label else ''}"
                            f"</div>"
                            f"<div style='font-size:0.82rem;margin-top:3px'>"
                            f"<span style='color:#16a34a'>✅ สำเร็จ {finished}</span>&nbsp;&nbsp;"
                            f"<span style='color:#3B82F6'>🔵 กำลังมา {incoming}</span>&nbsp;&nbsp;"
                            f"<span style='color:#9CA3AF'>⬜ ยังไม่เริ่ม {not_started}</span>"
                            f"</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col_btns:
                        # ── เปิด (primary) ──────────────────────────────
                        if st.button("เปิด Victory Road", key=f"open_{vr['id']}", use_container_width=True, type="primary"):
                            st.session_state.vr_detail_id = str(vr["id"])
                            st.rerun()
                        # ── แก้ไข (secondary, stacked below) ───────────
                        def _parse_sprint_for_edit(s: dict) -> dict:
                            sc = s.copy()
                            _d = sc.get("date")
                            if isinstance(_d, str) and _d:
                                try:
                                    sc["date"] = date.fromisoformat(_d[:10])
                                except ValueError:
                                    sc["date"] = date.today()
                            _wkey = f"sd_form_{sc['id']}"
                            if _wkey in st.session_state:
                                del st.session_state[_wkey]
                            return sc
                        if st.button("แก้ไข Victory road", key=f"edit_{vr['id']}", use_container_width=True):
                            st.session_state.editing_vr          = vr
                            st.session_state.form_vr_name        = vr["name"]
                            st.session_state.form_vr_description = vr.get("description", "")
                            st.session_state.form_vr_level       = vr.get("level", LEVELS[5])
                            st.session_state.form_road_type      = vr.get("road_type", "cohort")
                            st.session_state.form_sprints = [
                                _parse_sprint_for_edit(_s)
                                for _s in vr.get("sprints", [])
                            ]
                            st.session_state.form_cohort_sprints = [
                                {
                                    **cs,
                                    "sub_sprints": [
                                        _parse_sprint_for_edit(sub)
                                        for sub in cs.get("sub_sprints", [])
                                    ],
                                }
                                for cs in vr.get("cohort_sprints", [])
                            ]
                            raw_stu = vr.get("students", [])
                            st.session_state.form_students = [
                                f"{s.get('nickname','')}: {s.get('name','')}".strip()
                                if isinstance(s, dict) else str(s)
                                for s in raw_stu
                            ]
                            st.session_state.vr_view = "edit"
                            dialog_edit_vr()

# ═══════════════════════════════════════════════════════
# PAGE 3: Student
# ═══════════════════════════════════════════════════════
elif st.session_state.page == "Student":

    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.title("Student")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add Student", type="primary", width="stretch"):
            st.session_state.add_student_open = True

    st.divider()

    if st.session_state.get("add_student_open"):
        with st.container(border=True):
            st.markdown("**เพิ่มนักเรียนใหม่**")
            c1, c2 = st.columns(2)
            with c1:
                nn  = st.text_input("Nickname *", key="new_nn", placeholder="เช่น โอ๊ต")
                nm  = st.text_input("ชื่อ *",    key="new_nm", placeholder="สมชาย")
                sur = st.text_input("นามสกุล *", key="new_sur", placeholder="ใจดี")
            with c2:
                lv  = st.selectbox("ระดับชั้น", LEVELS, index=5, key="new_lv")
                ph  = st.text_input("เบอร์โทรศัพท์", key="new_ph", placeholder="08x-xxx-xxxx")
                li  = st.text_input("Line ID",       key="new_li", placeholder="@lineId")
            st.markdown("**บัญชีเข้าใช้งาน**")
            ca, cb = st.columns(2)
            with ca:
                s_user = st.text_input("Username", key="new_s_user", placeholder="เช่น oak2025")
            with cb:
                s_pw   = st.text_input("Password", key="new_s_pw", type="password", placeholder="ตั้งรหัสผ่าน")
            cs, cc = st.columns([2, 1])
            with cs:
                if st.button("บันทึก", type="primary", width="stretch", key="save_student"):
                    if not nn or not nm:
                        st.error("กรุณาใส่ Nickname และชื่อก่อน")
                    else:
                        student_data = {"nickname": nn, "name": nm, "surname": sur,
                                        "level": lv, "phone": ph, "line_id": li}
                        if s_user: student_data["username"] = s_user
                        if s_pw:   student_data["password_hash"] = hash_password(s_pw)
                        create_student(student_data)
                        st.session_state.add_student_open = False
                        st.success(f"เพิ่ม '{nn}' แล้ว")
                        st.rerun()
            with cc:
                if st.button("ยกเลิก", width="stretch", key="cancel_student"):
                    st.session_state.add_student_open = False; st.rerun()
        st.divider()

    students = get_all_students()
    if not students:
        st.info("ยังไม่มีนักเรียนในระบบ — กด 'Add Student' ด้านบนขวาได้เลย")
    else:
        df = pd.DataFrame([{
            "Nickname":     s.get("nickname", ""),
            "Name-Surname": f"{s.get('name','')} {s.get('surname','')}".strip(),
            "Username":     s.get("username", ""),
            "Level":        s.get("level", ""),
            "Phone":        s.get("phone", ""),
            "Line":         s.get("line_id", ""),
            "_id":          s.get("id", ""),
        } for s in students])

        edited = st.data_editor(
            df.drop(columns=["_id"]),
            width="stretch", num_rows="fixed", hide_index=True,
            column_config={
                "Nickname":     st.column_config.TextColumn("Nickname", width="small"),
                "Name-Surname": st.column_config.TextColumn("ชื่อ-นามสกุล", width="medium"),
                "Username":     st.column_config.TextColumn("Username", width="small"),
                "Level":        st.column_config.SelectboxColumn("ระดับชั้น", options=LEVELS, width="medium"),
                "Phone":        st.column_config.TextColumn("เบอร์โทร", width="small"),
                "Line":         st.column_config.TextColumn("Line ID", width="small"),
            },
            key="student_table",
        )

        col_save, _ = st.columns([1, 5])
        with col_save:
            if st.button("บันทึกการแก้ไข", width="stretch", key="save_s_tbl"):
                for i, row in edited.iterrows():
                    sid   = df.iloc[i]["_id"]
                    parts = row["Name-Surname"].split(" ", 1)
                    update_student(sid, {
                        "nickname": row["Nickname"], "name": parts[0],
                        "surname":  parts[1] if len(parts) > 1 else "",
                        "username": row["Username"],
                        "level":    row["Level"], "phone": row["Phone"], "line_id": row["Line"],
                    })
                st.success("บันทึกแล้ว"); st.rerun()

        st.markdown("---")
        with st.expander("แก้ไขข้อมูลนักเรียน"):
            ed_s_pick = st.selectbox("เลือกนักเรียน", ["—"] + list(df["Nickname"]), key="ed_s_pick")
            if ed_s_pick != "—":
                _s_row = next((s for s in students if s.get("nickname") == ed_s_pick), None)
                if _s_row:
                    ed_c1, ed_c2 = st.columns(2)
                    with ed_c1:
                        ed_s_nn  = st.text_input("Nickname *", value=_s_row.get("nickname", ""), key="ed_s_nn")
                        ed_s_nm  = st.text_input("ชื่อ *",    value=_s_row.get("name", ""),     key="ed_s_nm")
                        ed_s_sur = st.text_input("นามสกุล",   value=_s_row.get("surname", ""),  key="ed_s_sur")
                    with ed_c2:
                        _cur_lv = _s_row.get("level", LEVELS[5])
                        ed_s_lv  = st.selectbox("ระดับชั้น", LEVELS,
                                                index=LEVELS.index(_cur_lv) if _cur_lv in LEVELS else 5,
                                                key="ed_s_lv")
                        ed_s_ph  = st.text_input("เบอร์โทรศัพท์", value=_s_row.get("phone", ""),   key="ed_s_ph")
                        ed_s_li  = st.text_input("Line ID",        value=_s_row.get("line_id", ""), key="ed_s_li")
                    st.markdown("**บัญชีเข้าใช้งาน**")
                    ed_ca, ed_cb = st.columns(2)
                    with ed_ca:
                        ed_s_user = st.text_input("Username", value=_s_row.get("username", ""), key="ed_s_user")
                    with ed_cb:
                        ed_s_pw1 = st.text_input("รหัสผ่านใหม่ (เว้นว่างถ้าไม่เปลี่ยน)",
                                                  type="password", key="ed_s_pw1")
                    ed_sb, ed_sc = st.columns([2, 1])
                    with ed_sb:
                        if st.button("บันทึกข้อมูล", type="primary", width="stretch", key="ed_s_save"):
                            if not ed_s_nn or not ed_s_nm:
                                st.error("กรุณาใส่ Nickname และชื่อก่อน")
                            else:
                                _upd = {
                                    "nickname": ed_s_nn, "name": ed_s_nm,
                                    "surname":  ed_s_sur, "level": ed_s_lv,
                                    "phone":    ed_s_ph, "line_id": ed_s_li,
                                    "username": ed_s_user,
                                }
                                if ed_s_pw1:
                                    _upd["password_hash"] = hash_password(ed_s_pw1)
                                update_student(_s_row["id"], _upd)
                                st.success(f"อัปเดตข้อมูล '{ed_s_nn}' แล้ว")
                                st.rerun()
                    with ed_sc:
                        if st.button("ยกเลิก", width="stretch", key="ed_s_cancel"):
                            st.rerun()

                    st.markdown("---")
                    _sdel_key = f"sdel_confirm_{_s_row['id']}"
                    if not st.session_state.get(_sdel_key):
                        if st.button(f"🗑 ลบ '{ed_s_pick}' ออกจากระบบ", key="del_s_btn"):
                            st.session_state[_sdel_key] = True
                            st.rerun()
                    else:
                        st.warning(f"ยืนยันการลบ '{ed_s_pick}' จริงๆ หรือ? ข้อมูลจะหายถาวร")
                        _sdy, _sdn = st.columns(2)
                        with _sdy:
                            if st.button("ยืนยัน ลบ", key="del_s_yes", type="primary"):
                                delete_student(_s_row["id"])
                                st.session_state.pop(_sdel_key, None)
                                st.rerun()
                        with _sdn:
                            if st.button("ยกเลิก", key="del_s_no"):
                                st.session_state.pop(_sdel_key, None)
                                st.rerun()

    st.caption("กรอกรายรับ/รายจ่ายได้ที่หน้า Financial")


# ═══════════════════════════════════════════════════════
# PAGE 4: Teacher
# ═══════════════════════════════════════════════════════
elif st.session_state.page == "Teacher":

    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.title("Teacher")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add Teacher", type="primary", width="stretch"):
            st.session_state.add_teacher_open = True

    st.divider()

    if st.session_state.get("add_teacher_open"):
        with st.container(border=True):
            st.markdown("**เพิ่มครูใหม่**")
            c1, c2 = st.columns(2)
            with c1:
                t_nn  = st.text_input("Nickname *", key="new_t_nn", placeholder="เช่น ครูป้อม")
                t_nm  = st.text_input("ชื่อ *",    key="new_t_nm", placeholder="สมชาย")
                t_sur = st.text_input("นามสกุล",   key="new_t_sur", placeholder="ใจดี")
            with c2:
                t_subj = st.multiselect("วิชาที่สอน", SUBJECTS, key="new_t_subj")
                t_ph   = st.text_input("เบอร์โทรศัพท์", key="new_t_ph", placeholder="08x-xxx-xxxx")
                t_li   = st.text_input("Line ID",        key="new_t_li", placeholder="@lineId")
            st.markdown("**บัญชีเข้าใช้งาน**")
            ta, tb = st.columns(2)
            with ta:
                t_user = st.text_input("Username", key="new_t_user", placeholder="เช่น teacher_pom")
            with tb:
                t_pw   = st.text_input("Password", key="new_t_pw", type="password", placeholder="ตั้งรหัสผ่าน")
            cs, cc = st.columns([2, 1])
            with cs:
                if st.button("บันทึก", type="primary", width="stretch", key="save_teacher"):
                    if not t_nn or not t_nm:
                        st.error("กรุณาใส่ Nickname และชื่อก่อน")
                    else:
                        teacher_data = {
                            "nickname": t_nn, "name": t_nm, "surname": t_sur,
                            "subjects": ", ".join(t_subj), "phone": t_ph, "line_id": t_li,
                        }
                        if t_user: teacher_data["username"] = t_user
                        if t_pw:   teacher_data["password_hash"] = hash_password(t_pw)
                        create_teacher(teacher_data)
                        st.session_state.add_teacher_open = False
                        st.success(f"เพิ่ม '{t_nn}' แล้ว")
                        st.rerun()
            with cc:
                if st.button("ยกเลิก", width="stretch", key="cancel_teacher"):
                    st.session_state.add_teacher_open = False; st.rerun()
        st.divider()

    teachers = get_all_teachers()
    if not teachers:
        st.info("ยังไม่มีครูในระบบ — กด 'Add Teacher' ด้านบนขวาได้เลย")
    else:
        df_t = pd.DataFrame([{
            "Nickname":     t.get("nickname", ""),
            "ชื่อ-นามสกุล": f"{t.get('name','')} {t.get('surname','')}".strip(),
            "Username":     t.get("username", ""),
            "วิชาที่สอน":  t.get("subjects", ""),
            "เบอร์โทร":    t.get("phone", ""),
            "Line ID":      t.get("line_id", ""),
            "_id":          t.get("id", ""),
        } for t in teachers])

        edited_t = st.data_editor(
            df_t.drop(columns=["_id"]),
            width="stretch", num_rows="fixed", hide_index=True,
            column_config={
                "Nickname":      st.column_config.TextColumn("Nickname", width="small"),
                "ชื่อ-นามสกุล": st.column_config.TextColumn("ชื่อ-นามสกุล", width="medium"),
                "Username":      st.column_config.TextColumn("Username", width="small"),
                "วิชาที่สอน":   st.column_config.TextColumn("วิชาที่สอน", width="medium"),
                "เบอร์โทร":     st.column_config.TextColumn("เบอร์โทร", width="small"),
                "Line ID":       st.column_config.TextColumn("Line ID", width="small"),
            },
            key="teacher_table",
        )

        col_save, _ = st.columns([1, 5])
        with col_save:
            if st.button("บันทึกการแก้ไข", width="stretch", key="save_t_tbl"):
                for i, row in edited_t.iterrows():
                    tid   = df_t.iloc[i]["_id"]
                    parts = row["ชื่อ-นามสกุล"].split(" ", 1)
                    update_teacher(tid, {
                        "nickname": row["Nickname"], "name": parts[0],
                        "surname":  parts[1] if len(parts) > 1 else "",
                        "username": row["Username"],
                        "subjects": row["วิชาที่สอน"],
                        "phone":    row["เบอร์โทร"], "line_id": row["Line ID"],
                    })
                st.success("บันทึกแล้ว"); st.rerun()

        st.markdown("---")
        with st.expander("แก้ไขข้อมูลครู"):
            ed_t_pick = st.selectbox("เลือกครู", ["—"] + list(df_t["Nickname"]), key="ed_t_pick")
            if ed_t_pick != "—":
                _t_row = next((t for t in teachers if t.get("nickname") == ed_t_pick), None)
                if _t_row:
                    ed_tc1, ed_tc2 = st.columns(2)
                    with ed_tc1:
                        ed_t_nn  = st.text_input("Nickname *", value=_t_row.get("nickname", ""), key="ed_t_nn")
                        ed_t_nm  = st.text_input("ชื่อ *",    value=_t_row.get("name", ""),     key="ed_t_nm")
                        ed_t_sur = st.text_input("นามสกุล",   value=_t_row.get("surname", ""),  key="ed_t_sur")
                    with ed_tc2:
                        _cur_subj_str = _t_row.get("subjects", "")
                        _cur_subj_list = [s.strip() for s in _cur_subj_str.split(",") if s.strip() in SUBJECTS]
                        ed_t_subj = st.multiselect("วิชาที่สอน", SUBJECTS,
                                                    default=_cur_subj_list, key="ed_t_subj")
                        ed_t_ph  = st.text_input("เบอร์โทรศัพท์", value=_t_row.get("phone", ""),   key="ed_t_ph")
                        ed_t_li  = st.text_input("Line ID",        value=_t_row.get("line_id", ""), key="ed_t_li")
                    st.markdown("**บัญชีเข้าใช้งาน**")
                    ed_ta, ed_tb = st.columns(2)
                    with ed_ta:
                        ed_t_user = st.text_input("Username", value=_t_row.get("username", ""), key="ed_t_user")
                    with ed_tb:
                        ed_t_pw1 = st.text_input("รหัสผ่านใหม่ (เว้นว่างถ้าไม่เปลี่ยน)",
                                                  type="password", key="ed_t_pw1")
                    ed_tsb, ed_tsc = st.columns([2, 1])
                    with ed_tsb:
                        if st.button("บันทึกข้อมูล", type="primary", width="stretch", key="ed_t_save"):
                            if not ed_t_nn or not ed_t_nm:
                                st.error("กรุณาใส่ Nickname และชื่อก่อน")
                            else:
                                _upd_t = {
                                    "nickname": ed_t_nn, "name": ed_t_nm,
                                    "surname":  ed_t_sur,
                                    "subjects": ", ".join(ed_t_subj),
                                    "phone":    ed_t_ph, "line_id": ed_t_li,
                                    "username": ed_t_user,
                                }
                                if ed_t_pw1:
                                    _upd_t["password_hash"] = hash_password(ed_t_pw1)
                                update_teacher(_t_row["id"], _upd_t)
                                st.success(f"อัปเดตข้อมูล '{ed_t_nn}' แล้ว")
                                st.rerun()
                    with ed_tsc:
                        if st.button("ยกเลิก", width="stretch", key="ed_t_cancel"):
                            st.rerun()

                    st.markdown("---")
                    _tdel_key = f"tdel_confirm_{_t_row['id']}"
                    if not st.session_state.get(_tdel_key):
                        if st.button(f"🗑 ลบ '{ed_t_pick}' ออกจากระบบ", key="del_t_btn"):
                            st.session_state[_tdel_key] = True
                            st.rerun()
                    else:
                        st.warning(f"ยืนยันการลบ '{ed_t_pick}' จริงๆ หรือ? ข้อมูลจะหายถาวร")
                        _tdy, _tdn = st.columns(2)
                        with _tdy:
                            if st.button("ยืนยัน ลบ", key="del_t_yes", type="primary"):
                                delete_teacher(_t_row["id"])
                                st.session_state.pop(_tdel_key, None)
                                st.rerun()
                        with _tdn:
                            if st.button("ยกเลิก", key="del_t_no"):
                                st.session_state.pop(_tdel_key, None)
                                st.rerun()

    st.caption("กรอกรายจ่ายค่าสอนได้ที่หน้า Financial")


# ═══════════════════════════════════════════════════════
# PAGE 5: Calendar
# ═══════════════════════════════════════════════════════
elif st.session_state.page == "Calendar":

    st.title("Calendar")
    st.caption("ตารางเรียนจาก Sprint ทั้งหมดใน Victory Road")
    st.divider()

    events = get_calendar_events()

    try:
        from streamlit_calendar import calendar as st_calendar
        cal_options = {
            "initialView":   "dayGridMonth",
            "locale":        "th",
            "height":        620,
            "headerToolbar": {
                "left":   "prev,next today",
                "center": "title",
                "right":  "dayGridMonth,timeGridWeek,listWeek",
            },
        }
        result = st_calendar(events=events, options=cal_options, key="main_calendar")

        # ── เก็บ click ล่าสุดใน session_state ──
        if result and result.get("eventClick"):
            st.session_state["_cal_ev"] = result["eventClick"].get("event", {})

        # ── แสดงรายละเอียดด้านล่าง calendar ──
        _cal_ev = st.session_state.get("_cal_ev")
        if _cal_ev:
            ep = _cal_ev.get("extendedProps", {})
            st.markdown("---")
            with st.container(border=True):
                _close_col, _title_col = st.columns([1, 8])
                with _close_col:
                    if st.button("✕", key="cal_close"):
                        del st.session_state["_cal_ev"]
                        st.rerun()
                with _title_col:
                    _rt_label = "Cohort" if ep.get("road_type") == "cohort" else "Personalize"
                    st.markdown(f"### {_cal_ev.get('title', '')}")
                    st.caption(f"{ep.get('level', '')}  ·  {_rt_label}")

                st.divider()

                _t_start = ep.get("start_time", "")
                _t_end   = ep.get("end_time", "")
                if _t_start and _t_end:
                    st.markdown(f"🕐 **{_t_start} – {_t_end} น.**")
                if ep.get("sprint_type"):
                    st.markdown(f"**ประเภท Sprint:** {ep['sprint_type']}")
                _teacher = ep.get("teacher", "")
                if _teacher and _teacher != "—":
                    st.markdown(f"**ครูผู้สอน:** {_teacher}")
                if ep.get("subject"):
                    st.markdown(f"**วิชา:** {ep['subject']}")
                if ep.get("road_type") == "personalize" and ep.get("students"):
                    st.markdown(f"**นักเรียน:** {', '.join(ep['students'])}")
                if ep.get("lecture_link"):
                    st.markdown(f"[📖 เปิด Lecture]({ep['lecture_link']})")

    except ImportError:
        st.warning("ยังไม่ได้ติดตั้ง streamlit-calendar — แสดงเป็นตารางแทน")
        if not events:
            st.info("ยังไม่มีตารางเรียน — ไปสร้าง Victory Road และใส่วันที่ Sprint ก่อนนะครับ")
        else:
            df_cal = pd.DataFrame([{
                "วันที่":          e["start"],
                "Victory Road":   e["title"],
                "ประเภท Sprint":  e["extendedProps"].get("sprint_type", ""),
                "วิชา":           e["extendedProps"].get("subject", ""),
                "ครูผู้สอน":     e["extendedProps"].get("teacher", ""),
                "ระดับชั้น":     e["extendedProps"].get("level", ""),
            } for e in sorted(events, key=lambda x: x["start"])])
            st.dataframe(df_cal, hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════
# PAGE 6: Financial
# ═══════════════════════════════════════════════════════
elif st.session_state.page == "Financial":
    import io

    # ── Password Gate ─────────────────────────────────
    import hashlib as _hl
    _admin_pin = _os.getenv("ADMIN_PIN", "")

    if "fin_auth" not in st.session_state:
        st.session_state["fin_auth"] = False

    if not st.session_state["fin_auth"]:
        st.markdown("## Financial — ยืนยันตัวตน")
        fin_pw_input = st.text_input("รหัสผ่าน", type="password", key="fin_pw_input",
                                     placeholder="กรอกรหัสผ่าน")
        if st.button("เข้าสู่ระบบ", type="primary", key="fin_pw_btn"):
            if fin_pw_input == _admin_pin:
                st.session_state["fin_auth"] = True
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
        st.stop()

    st.title("Financial")

    if st.button("ออกจากระบบ", key="fin_logout"):
        st.session_state["fin_auth"] = False
        st.rerun()

    tab_inc, tab_exp, tab_sum = st.tabs(["รายรับ", "รายจ่าย", "สรุป"])

    # ══════════════════════════════════════════════════════════
    # TAB 1 — รายรับ (Student Payments)
    # ══════════════════════════════════════════════════════════
    with tab_inc:
        st.subheader("รายรับ / สถานะการชำระเงิน")
        st.caption("💡 คอลัมน์ **ค้างจ่าย** คำนวณอัตโนมัติจาก ค่าเรียน − รับแล้ว หลังจากกดบันทึกรายรับ")

        pay_vrs      = get_all_victory_roads()
        payments_all = get_student_payments()
        pay_map = {
            (p["student_id"], p["victory_road_id"]): p
            for p in payments_all
        }

        students_pay = get_all_students()
        if not students_pay:
            st.info("ยังไม่มีนักเรียนในระบบ")
        else:
            vr_names_pay = ["ทั้งหมด"] + [v["name"] for v in pay_vrs]
            sel_pay_vr   = st.selectbox("กรองตาม Victory Road", vr_names_pay, key="fin_sel_pay_vr")

            pay_rows = []
            for stu in students_pay:
                stu_id = stu.get("id", "")
                for vr in pay_vrs:
                    if sel_pay_vr != "ทั้งหมด" and vr["name"] != sel_pay_vr:
                        continue
                    in_vr = any(
                        isinstance(s, dict) and s.get("id") == stu_id
                        for s in vr.get("students", [])
                    )
                    if not in_vr:
                        continue
                    rec = pay_map.get((stu_id, vr["id"]), {})
                    _fee    = float(rec.get("fee", 0))
                    _amount = float(rec.get("amount", 0))
                    pay_rows.append({
                        "นักเรียน":          stu.get("nickname", ""),
                        "Victory Road":      vr["name"],
                        "ระดับชั้น":         vr.get("level", ""),
                        "ค่าเรียน (฿)":      _fee,
                        "รับแล้ว (฿)":       _amount,
                        "ค้างจ่าย (฿)":      round(_fee - _amount, 2),
                        "สถานะ":             rec.get("payment_status", "pending"),
                        "หมายเหตุ":          rec.get("note", ""),
                        "_stu_id":           stu_id,
                        "_vr_id":            vr["id"],
                    })

            if not pay_rows:
                st.info("ไม่มีนักเรียนที่ลงทะเบียน VR ใดเลย — ไปเพิ่มนักเรียนใน Victory Road ก่อนนะครับ")
            else:
                edited_pay = st.data_editor(
                    pd.DataFrame(pay_rows)[[
                        "นักเรียน", "Victory Road", "ระดับชั้น",
                        "ค่าเรียน (฿)", "รับแล้ว (฿)", "ค้างจ่าย (฿)",
                        "สถานะ", "หมายเหตุ",
                    ]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "นักเรียน":     st.column_config.TextColumn("นักเรียน",      disabled=True, width="small"),
                        "Victory Road": st.column_config.TextColumn("Victory Road",   disabled=True),
                        "ระดับชั้น":    st.column_config.TextColumn("ระดับชั้น",     disabled=True, width="small"),
                        "ค่าเรียน (฿)": st.column_config.NumberColumn("ค่าเรียน (฿)", min_value=0, step=100,
                                            help="ค่าเรียนทั้งหมดที่ต้องชำระ"),
                        "รับแล้ว (฿)":  st.column_config.NumberColumn("รับแล้ว (฿)",  min_value=0, step=100,
                                            help="ยอดที่รับมาแล้ว"),
                        "ค้างจ่าย (฿)": st.column_config.NumberColumn("ค้างจ่าย (฿)", disabled=True, width="small"),
                        "สถานะ":        st.column_config.SelectboxColumn(
                            "สถานะ", options=["pending", "success"], width="small"
                        ),
                        "หมายเหตุ":     st.column_config.TextColumn("หมายเหตุ"),
                    },
                    key="fin_pay_editor",
                )

                col_save_pay, col_sum_pay = st.columns([2, 3])
                with col_save_pay:
                    if st.button("บันทึกรายรับ", type="primary", key="fin_save_pay_btn", width="stretch"):
                        errors = []
                        for i, row in edited_pay.iterrows():
                            meta = pay_rows[i]
                            ok = upsert_student_payment(
                                meta["_stu_id"], meta["_vr_id"],
                                row["สถานะ"],
                                float(row["รับแล้ว (฿)"]),
                                str(row.get("หมายเหตุ") or ""),
                                float(row["ค่าเรียน (฿)"]),
                            )
                            if not ok:
                                errors.append(f"{meta.get('นักเรียน', i)}")
                        if errors:
                            st.error(f"บันทึกไม่สำเร็จ: {', '.join(errors)} — ตรวจสอบว่ารัน SQL migration แล้วหรือยัง")
                        else:
                            st.success("บันทึกรายรับแล้ว")
                            st.rerun()
                with col_sum_pay:
                    total_fee  = sum(float(r["ค่าเรียน (฿)"]) for _, r in edited_pay.iterrows())
                    total_recv = sum(float(r["รับแล้ว (฿)"]) for _, r in edited_pay.iterrows())
                    total_owed = total_fee - total_recv
                    st.markdown(
                        f"ค่าเรียนรวม: **฿{total_fee:,.0f}**  |  "
                        f"รับแล้ว: **฿{total_recv:,.0f}**  |  "
                        f"ค้างจ่าย: **฿{total_owed:,.0f}**"
                    )

    # ══════════════════════════════════════════════════════════
    # TAB 2 — รายจ่าย (Teacher Expenses)
    # ══════════════════════════════════════════════════════════
    with tab_exp:
        st.subheader("รายจ่ายค่าสอนต่อ Sprint")

        vrs_for_exp  = get_all_victory_roads()
        expenses_all = get_teacher_expenses()
        expenses_map = {e["sprint_id"]: e for e in expenses_all if e.get("sprint_id")}

        teachers_exp = get_all_teachers()
        if not teachers_exp:
            st.info("ยังไม่มีครูในระบบ")
        else:
            t_nick_list = [t.get("nickname", "") for t in teachers_exp if t.get("nickname")]
            sel_t_exp   = st.selectbox("เลือกครู", ["—"] + t_nick_list, key="fin_sel_exp_teacher")

            if sel_t_exp != "—":
                teacher_obj = next((t for t in teachers_exp if t.get("nickname") == sel_t_exp), {})
                teacher_id  = teacher_obj.get("id", "")

                teacher_sprints = []
                for vr in vrs_for_exp:
                    # ── Personalize sprints ──────────────────────
                    for sp in vr.get("sprints", []):
                        if sp.get("teacher", "").startswith(sel_t_exp):
                            d = _to_date(sp.get("date"))
                            teacher_sprints.append({
                                **sp,
                                "_vr_id":    vr["id"],
                                "_vr_name":  vr["name"],
                                "_date_obj": d,
                            })
                    # ── Cohort sub-sprints ───────────────────────
                    for cs in vr.get("cohort_sprints", []):
                        for sub in cs.get("sub_sprints", []):
                            if sub.get("teacher", "").startswith(sel_t_exp):
                                d = _to_date(sub.get("date"))
                                teacher_sprints.append({
                                    **sub,
                                    "name":      f"{cs.get('name','')} › {sub.get('name','')}",
                                    "_vr_id":    vr["id"],
                                    "_vr_name":  vr["name"],
                                    "_date_obj": d,
                                })

                if not teacher_sprints:
                    st.info(f"ยังไม่มี Sprint ที่มอบหมายให้ {sel_t_exp}")
                else:
                    exp_rows = []
                    for sp in teacher_sprints:
                        ex = expenses_map.get(str(sp["id"]), {})
                        d  = sp["_date_obj"]
                        exp_rows.append({
                            "Victory Road": sp["_vr_name"],
                            "Sprint":       sp.get("name", ""),
                            "วิชา":         sp.get("subject", ""),
                            "วันที่":       d.strftime("%d/%m/%Y") if d else "—",
                            "ค่าสอน (฿)":  float(ex.get("amount", 0)),
                            "สถานะจ่าย":    ex.get("payment_status", "unpaid"),
                            "หมายเหตุ":     ex.get("note", ""),
                            "_sprint_id":   str(sp["id"]),
                            "_vr_id":       sp["_vr_id"],
                            "_vr_name":     sp["_vr_name"],
                            "_subject":     sp.get("subject", ""),
                            "_expense_date": d.isoformat() if d else None,
                        })

                    display_exp_cols = ["Victory Road", "Sprint", "วิชา", "วันที่", "ค่าสอน (฿)", "สถานะจ่าย", "หมายเหตุ"]
                    edited_exp = st.data_editor(
                        pd.DataFrame(exp_rows)[display_exp_cols],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Victory Road": st.column_config.TextColumn("Victory Road", disabled=True),
                            "Sprint":       st.column_config.TextColumn("Sprint",       disabled=True),
                            "วิชา":         st.column_config.TextColumn("วิชา",         disabled=True, width="small"),
                            "วันที่":       st.column_config.TextColumn("วันที่",       disabled=True, width="small"),
                            "ค่าสอน (฿)":  st.column_config.NumberColumn("ค่าสอน (฿)", min_value=0, step=50),
                            "สถานะจ่าย":    st.column_config.SelectboxColumn(
                                "สถานะ", options=["unpaid", "paid"], width="small"
                            ),
                            "หมายเหตุ":     st.column_config.TextColumn("หมายเหตุ"),
                        },
                        key="fin_expense_editor",
                    )

                    col_save_exp, col_sum_exp = st.columns([2, 3])
                    with col_save_exp:
                        if st.button("บันทึกรายจ่าย", type="primary", key="fin_save_exp_btn", width="stretch"):
                            for i, row in edited_exp.iterrows():
                                meta = exp_rows[i]
                                upsert_teacher_expense({
                                    "teacher_id":        teacher_id,
                                    "teacher_name":      sel_t_exp,
                                    "sprint_id":         meta["_sprint_id"],
                                    "sprint_name":       meta["Sprint"],
                                    "victory_road_id":   meta["_vr_id"],
                                    "victory_road_name": meta["_vr_name"],
                                    "subject":           meta["_subject"],
                                    "amount":            float(row["ค่าสอน (฿)"]),
                                    "payment_status":    row["สถานะจ่าย"],
                                    "expense_date":      meta["_expense_date"],
                                    "note":              row.get("หมายเหตุ", ""),
                                })
                            st.success("บันทึกรายจ่ายแล้ว")
                            st.rerun()
                    with col_sum_exp:
                        total_exp = sum(float(r["ค่าสอน (฿)"]) for _, r in edited_exp.iterrows())
                        paid_exp  = sum(
                            float(r["ค่าสอน (฿)"])
                            for _, r in edited_exp.iterrows()
                            if r["สถานะจ่าย"] == "paid"
                        )
                        st.markdown(
                            f"รวมค่าสอนทั้งหมด: **฿{total_exp:,.0f}**  |  "
                            f"จ่ายแล้ว: **฿{paid_exp:,.0f}**  |  "
                            f"ค้างจ่าย: **฿{total_exp - paid_exp:,.0f}**"
                        )

    # ══════════════════════════════════════════════════════════
    # TAB 3 — สรุป (Ledger + KPI + Excel)
    # ══════════════════════════════════════════════════════════
    with tab_sum:
        st.subheader("สรุปรายรับ-รายจ่าย")

        fin_payments = get_student_payments()
        fin_expenses = get_teacher_expenses()
        fin_students = {s["id"]: s for s in get_all_students()}
        fin_vrs      = {v["id"]: v for v in get_all_victory_roads()}

        # ── KPI (always full dataset, ไม่กรองเดือน) ───────────
        inc_success  = sum(float(p.get("amount", 0)) for p in fin_payments
                           if p.get("payment_status") == "success")
        exp_total    = sum(float(e.get("amount", 0)) for e in fin_expenses)
        exp_paid     = sum(float(e.get("amount", 0)) for e in fin_expenses
                           if e.get("payment_status") == "paid")
        outstanding_teacher  = exp_total - exp_paid
        outstanding_tuition  = sum(
            max(0.0, float(p.get("fee", 0)) - float(p.get("amount", 0)))
            for p in fin_payments
        )
        net = inc_success - exp_total

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("รายรับรวม",              f"฿{inc_success:,.0f}")
        k2.metric("รายจ่าย (ครู) รวม",      f"฿{exp_total:,.0f}")
        k3.metric("กำไร / ขาดทุน",          f"฿{net:,.0f}", delta=f"{net:,.0f}")
        k4.metric("ค่าสอนค้างจ่าย (ครู)",   f"฿{outstanding_teacher:,.0f}",
                  help="รวมทุก Sprint ที่ยังไม่ได้จ่ายค่าสอน")
        k5.metric("คงค้างค่าเรียน (นักเรียน)", f"฿{outstanding_tuition:,.0f}",
                  help="ค่าเรียนรวม − ยอดที่รับแล้ว")

        st.divider()

        # ── Build unified ledger rows ──────────────────────────
        ledger_rows = []

        for p in fin_payments:
            stu = fin_students.get(p.get("student_id", ""), {})
            vr  = fin_vrs.get(p.get("victory_road_id", ""), {})
            raw_date = p.get("updated_at") or p.get("created_at") or ""
            d_str = str(raw_date)[:10] if raw_date else "—"
            vr_type = "Cohort" if vr.get("road_type", "cohort") == "cohort" else "Personalize"
            ledger_rows.append({
                "วันที่":        d_str,
                "Person":        stu.get("nickname", "—"),
                "ประเภท":        "รายรับ",
                "Victory Road":  vr.get("name", "—"),
                "VR Type":       vr_type,
                "Sprint":        "—",
                "จำนวนเงิน (฿)": float(p.get("amount", 0)),
                "สถานะ":         p.get("payment_status", "pending"),
            })

        for e in fin_expenses:
            raw_date = e.get("expense_date") or e.get("created_at") or ""
            d_str = str(raw_date)[:10] if raw_date else "—"
            # หา VR type จาก fin_vrs
            vr_obj  = fin_vrs.get(e.get("victory_road_id", ""), {})
            vr_type = "Cohort" if vr_obj.get("road_type", "cohort") == "cohort" else "Personalize"
            ledger_rows.append({
                "วันที่":        d_str,
                "Person":        e.get("teacher_name", "—"),
                "ประเภท":        "รายจ่าย",
                "Victory Road":  e.get("victory_road_name", "—"),
                "VR Type":       vr_type,
                "Sprint":        e.get("sprint_name", "—"),
                "จำนวนเงิน (฿)": float(e.get("amount", 0)),
                "สถานะ":         e.get("payment_status", "unpaid"),
            })

        if not ledger_rows:
            st.info("ยังไม่มีข้อมูลทางการเงิน — กรอกในแท็บ รายรับ และ รายจ่าย ก่อน")
        else:
            df_ledger = (
                pd.DataFrame(ledger_rows)
                .sort_values("วันที่", ascending=False)
                .reset_index(drop=True)
            )

            # ── Filter bar ────────────────────────────────────
            fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
            with fcol1:
                months_avail = sorted(
                    {r[:7] for r in df_ledger["วันที่"] if r and r != "—"},
                    reverse=True,
                )
                sel_month = st.selectbox("กรองเดือน", ["ทั้งหมด"] + months_avail,
                                         key="fin_month_sel")
            with fcol2:
                sel_type = st.selectbox("ประเภท", ["ทั้งหมด", "รายรับ", "รายจ่าย"],
                                        key="fin_type_sel")
            with fcol3:
                sel_status = st.selectbox(
                    "สถานะ", ["ทั้งหมด", "success", "pending", "paid", "unpaid"],
                    key="fin_status_sel",
                )

            df_show = df_ledger.copy()
            if sel_month != "ทั้งหมด":
                df_show = df_show[df_show["วันที่"].str.startswith(sel_month)]
            if sel_type != "ทั้งหมด":
                df_show = df_show[df_show["ประเภท"] == sel_type]
            if sel_status != "ทั้งหมด":
                df_show = df_show[df_show["สถานะ"] == sel_status]

            # ── Ledger table ──────────────────────────────────
            LEDGER_COLS = ["วันที่", "Person", "ประเภท", "Victory Road",
                           "VR Type", "Sprint", "จำนวนเงิน (฿)", "สถานะ"]
            st.dataframe(
                df_show[LEDGER_COLS].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "วันที่":        st.column_config.TextColumn("วันที่",        width="small"),
                    "Person":        st.column_config.TextColumn("Person",        width="small"),
                    "ประเภท":        st.column_config.TextColumn("ประเภท",        width="small"),
                    "Victory Road":  st.column_config.TextColumn("Victory Road"),
                    "VR Type":       st.column_config.TextColumn("VR Type",       width="small"),
                    "Sprint":        st.column_config.TextColumn("Sprint"),
                    "จำนวนเงิน (฿)": st.column_config.NumberColumn("จำนวนเงิน (฿)", format="฿%,.0f"),
                    "สถานะ":         st.column_config.TextColumn("สถานะ",         width="small"),
                },
            )
            st.caption(f"แสดง {len(df_show)} รายการ จากทั้งหมด {len(df_ledger)} รายการ")

            # ── Excel / CSV Download ───────────────────────────
            st.markdown("---")
            label_suffix = sel_month if sel_month != "ทั้งหมด" else "all"
            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df_show[LEDGER_COLS].to_excel(
                        writer, sheet_name="Ledger", index=False)
                    df_ledger[df_ledger["ประเภท"] == "รายรับ"][LEDGER_COLS].to_excel(
                        writer, sheet_name="รายรับ", index=False)
                    df_ledger[df_ledger["ประเภท"] == "รายจ่าย"][LEDGER_COLS].to_excel(
                        writer, sheet_name="รายจ่าย", index=False)
                buf.seek(0)
                st.download_button(
                    "Download Excel",
                    data=buf,
                    file_name=f"financial_ledger_{label_suffix}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except ImportError:
                csv_data = df_show[LEDGER_COLS].to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "Download CSV",
                    data=csv_data.encode("utf-8-sig"),
                    file_name=f"financial_ledger_{label_suffix}.csv",
                    mime="text/csv",
                )
                st.caption("ติดตั้ง openpyxl เพื่อ Export Excel: `pip install openpyxl`")

# ═══════════════════════════════════════════════════════
# PAGE: ผลลัพธ์การสอน Victory Road
# ═══════════════════════════════════════════════════════
elif st.session_state.page == "ผลลัพธ์การสอน Victory Road":

    if st.session_state.viewing_vr:
        # ── Analytics detail ──────────────────────────
        render_analytics_view()
    else:
        # ── VR picker list ────────────────────────────
        st.title("ผลลัพธ์การสอน Victory Road")
        st.divider()
        _ana_vrs = get_all_victory_roads()
        if not _ana_vrs:
            st.info("ยังไม่มี Victory Road — ไปสร้างที่เมนู 'สร้าง Victory Road' ก่อนนะครับ")
        else:
            for _vr in _ana_vrs:
                _all_sp   = _all_sprints(_vr)
                _finished = sum(1 for s in _all_sp if calc_status(s) == "finished")
                _total    = len(_all_sp)
                _rt       = "Cohort" if _vr.get("road_type", "cohort") == "cohort" else "Personalize"
                _pct      = int(_finished / _total * 100) if _total else 0
                with st.container(border=True):
                    _ci, _cb = st.columns([5, 1])
                    with _ci:
                        st.markdown(
                            f"**{_vr['name']}**\n\n"
                            f"<span style='color:#888;font-size:0.82rem'>"
                            f"{_rt}  ·  {_vr.get('level','')}  ·  "
                            f"สำเร็จ {_finished}/{_total} sprint  ·  {_pct}%</span>",
                            unsafe_allow_html=True,
                        )
                    with _cb:
                        if st.button("ดูผล →", key=f"ana_{_vr['id']}", type="primary", use_container_width=True):
                            st.session_state.viewing_vr = _vr
                            st.rerun()

# ═══════════════════════════════════════════════════════
# PAGE: Victory Partner
# ═══════════════════════════════════════════════════════
elif st.session_state.page == "Victory Partner":
    import hashlib as _hl

    # ── Auth gate ──────────────────────────────────────
    _admin_pin = _os.getenv("ADMIN_PIN", "")
    if "vp_auth" not in st.session_state:
        st.session_state["vp_auth"] = False

    # ── Description (always visible) ──────────────────
    st.title("Victory Partner")
    st.markdown(
        "<p style='color:#666;font-size:0.95rem;margin-top:-6px;margin-bottom:20px'>"
        "ระบบวิเคราะห์ผู้เรียนเชิงลึกด้วย AI</p>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("""
**Victory Partner คืออะไร?**

Victory Partner คือระบบวิเคราะห์ข้อมูลการเรียนรู้ของนักเรียนหลังจากจบ Victory Road แล้ว
โดยใช้อัลกอริทึม 2 ตัวร่วมกัน:

- **TOPSIS** — จัดอันดับนักเรียนตามเกณฑ์หลายมิติพร้อมกัน เช่น คะแนน การเข้าเรียน และพัฒนาการ
- **SOM (Self-Organizing Map)** — จัดกลุ่มนักเรียนตาม learning profile เพื่อให้ครูเข้าใจว่านักเรียนแต่ละกลุ่มต้องการอะไร

ผลลัพธ์ที่ได้จะแสดงเป็น **Radar Chart** และ **Percentile Bar** ให้นักเรียนดูผ่าน Victory Web ได้
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PIN gate ───────────────────────────────────────
    if not st.session_state["vp_auth"]:
        st.markdown("### เปิดใช้งาน Victory Partner")
        st.caption("ระบบนี้ต้องการการยืนยันตัวตนก่อนเปิดหรือปิดการใช้งาน")
        _vp_pin_input = st.text_input("รหัสผ่าน", type="password", key="vp_pin_input",
                                      placeholder="กรอกรหัสผ่าน")
        if st.button("ยืนยันและเปิดใช้งาน", type="primary", key="vp_pin_btn"):
            if _vp_pin_input == _admin_pin:
                st.session_state["vp_auth"] = True
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
        st.stop()

    # ── Authenticated: show controls ───────────────────
    _sim_open = get_sim_open()
    _s_color  = "#16a34a" if _sim_open else "#9CA3AF"
    _s_text   = "เปิดใช้งานอยู่" if _sim_open else "ปิดใช้งาน"
    _s_dot    = "🟢" if _sim_open else "⚫"

    with st.container(border=True):
        _pa, _pb = st.columns([4, 1])
        with _pa:
            st.markdown(
                f"**สถานะปัจจุบัน**\n\n"
                f"<span style='color:{_s_color};font-size:1rem;font-weight:600'>"
                f"{_s_dot}  {_s_text}</span>",
                unsafe_allow_html=True,
            )
            st.caption("เมื่อเปิดใช้งาน นักเรียนจะเห็นผลการวิเคราะห์โปรไฟล์การเรียนรู้ใน Victory Web")
        with _pb:
            st.markdown("<br>", unsafe_allow_html=True)
            _btn_lbl  = "ปิดการใช้งาน" if _sim_open else "เปิดใช้งาน"
            _btn_type = "secondary" if _sim_open else "primary"
            if st.button(_btn_lbl, key="vp_toggle", type=_btn_type, use_container_width=True):
                set_sim_open(not _sim_open)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("ออกจากระบบ", key="vp_logout"):
        st.session_state["vp_auth"] = False
        st.rerun()
