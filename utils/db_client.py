"""
Victory Road — Database Client v0.4
เชื่อมต่อ Supabase (ถ้ามี .env) หรือใช้ session_state เป็น fallback

══════════════════════════════════════════════════════════════════
Supabase SQL Schema — รัน SQL นี้ใน Supabase SQL Editor ทั้งหมด
══════════════════════════════════════════════════════════════════

-- 1. Victory Roads (ไม่มี sprints column แล้ว)
CREATE TABLE IF NOT EXISTS victory_roads (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  level       TEXT DEFAULT '',
  road_type   TEXT DEFAULT 'cohort',   -- 'cohort' | 'personalize'
  students    JSONB DEFAULT '[]',
  status      TEXT DEFAULT 'draft',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2a. Cohort Sprints (parent sprint สำหรับ Cohort VR — มีแค่ ชื่อ + ระดับ)
CREATE TABLE IF NOT EXISTS cohort_sprints (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  victory_road_id UUID NOT NULL REFERENCES victory_roads(id) ON DELETE CASCADE,
  name            TEXT DEFAULT '',
  sprint_type     TEXT DEFAULT 'foundation',  -- 'foundation' | 'practice' | 'test'
  order_index     INT DEFAULT 0,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 2b. Sprints (personal sprint ของ Personalize VR + sub-sprint ของ Cohort VR)
CREATE TABLE IF NOT EXISTS sprints (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  victory_road_id  UUID NOT NULL REFERENCES victory_roads(id) ON DELETE CASCADE,
  cohort_sprint_id UUID REFERENCES cohort_sprints(id) ON DELETE CASCADE,  -- NULL = personal sprint
  name             TEXT DEFAULT '',
  subject          TEXT DEFAULT 'คณิตศาสตร์',
  sprint_type      TEXT DEFAULT 'foundation',
  date             DATE,
  minutes          INT DEFAULT 60,
  teacher          TEXT DEFAULT '—',
  lecture_link     TEXT DEFAULT '',
  ws_link          TEXT DEFAULT '',
  done             BOOLEAN DEFAULT FALSE,
  student_scores   JSONB DEFAULT '{}',
  order_index      INT DEFAULT 0,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Migration จาก schema เก่า:
-- CREATE TABLE IF NOT EXISTS cohort_sprints (...);
-- ALTER TABLE sprints ADD COLUMN IF NOT EXISTS cohort_sprint_id UUID REFERENCES cohort_sprints(id) ON DELETE CASCADE;
-- ALTER TABLE sprints DROP COLUMN IF EXISTS parent_sprint_id;
-- ALTER TABLE sprints DROP COLUMN IF EXISTS delivery_mode;

-- 5. Teacher Performance (log การสอนต่อ sprint — สำหรับ financial summary)
CREATE TABLE IF NOT EXISTS teacher_performance (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id        UUID REFERENCES teachers(id) ON DELETE SET NULL,
  teacher_name      TEXT,                         -- denormalized เพื่อ query ง่าย
  sprint_id         UUID REFERENCES sprints(id) ON DELETE CASCADE,
  sprint_name       TEXT,
  victory_road_id   UUID REFERENCES victory_roads(id) ON DELETE CASCADE,
  victory_road_name TEXT,
  subject           TEXT,
  date              DATE,
  minutes           INT DEFAULT 60,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Teacher Feedback (สำหรับอนาคต — rating ต่อ sprint)
CREATE TABLE IF NOT EXISTS teacher_feedback (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id  UUID REFERENCES teachers(id) ON DELETE CASCADE,
  sprint_id   UUID REFERENCES sprints(id) ON DELETE SET NULL,
  rating      INT CHECK (rating BETWEEN 1 AND 5),
  comment     TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Student Performance (denormalized — upserted ทุกครั้งที่ admin บันทึกคะแนน)
CREATE TABLE IF NOT EXISTS student_performance (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id      UUID REFERENCES students(id) ON DELETE CASCADE,
  sprint_id       UUID REFERENCES sprints(id)  ON DELETE CASCADE,
  victory_road_id UUID REFERENCES victory_roads(id) ON DELETE CASCADE,
  subject         TEXT,
  date            DATE,
  earned          FLOAT,
  max             FLOAT,
  score_pct       FLOAT,   -- normalized 0–100
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(student_id, sprint_id)
);

-- 3. Students
CREATE TABLE IF NOT EXISTS students (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nickname      TEXT,
  name          TEXT,
  surname       TEXT,
  level         TEXT,
  phone         TEXT,
  line_id       TEXT,
  username      TEXT UNIQUE,
  password_hash TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Teachers
CREATE TABLE IF NOT EXISTS teachers (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nickname      TEXT,
  name          TEXT,
  surname       TEXT,
  subjects      TEXT,
  phone         TEXT,
  line_id       TEXT,
  username      TEXT UNIQUE,
  password_hash TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Sprint Attendance (การเข้าเรียน + คะแนน + feedback + worksheet นักเรียน)
CREATE TABLE IF NOT EXISTS sprint_attendance (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sprint_id         UUID NOT NULL REFERENCES sprints(id) ON DELETE CASCADE,
  student_id        UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  status            TEXT DEFAULT 'absent',  -- 'present' | 'absent' | 'n/a'
  teacher_feedback  TEXT DEFAULT '',
  student_ws_link   TEXT DEFAULT '',        -- link worksheet ที่นักเรียนส่ง
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(sprint_id, student_id)
);

-- 9. App Settings (key-value สำหรับ config ระดับ app)
CREATE TABLE IF NOT EXISTS app_settings (
  key    TEXT PRIMARY KEY,
  value  TEXT
);

-- ─────────────────────────────────────────────────────────────────
-- Migration จาก v0.3 (ถ้ามีตารางเก่าอยู่แล้ว ให้รัน SQL นี้แทน):
-- ─────────────────────────────────────────────────────────────────
-- ALTER TABLE victory_roads DROP COLUMN IF EXISTS sprints;
-- ALTER TABLE victory_roads ADD COLUMN IF NOT EXISTS road_type TEXT DEFAULT 'cohort';
-- CREATE TABLE IF NOT EXISTS sprints (... same as above ...);
══════════════════════════════════════════════════════════════════
"""

import os
import json
import uuid
import hashlib
import streamlit as st
from datetime import datetime, date


def hash_password(pw: str) -> str:
    """SHA-256 hash ของรหัสผ่าน"""
    return hashlib.sha256(pw.encode()).hexdigest()


# ─────────────────────────────────────────
# Connection helpers
# ─────────────────────────────────────────
_client = None


def _use_supabase() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))


def _get_client():
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    return _client


def _ss(key: str, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


# ─────────────────────────────────────────
# Cover Photo helpers
# ─────────────────────────────────────────
COVER_PHOTO_BUCKET = "cover_photo_sprint"

DEFAULT_COVER_BY_SUBJECT: dict[str, str] = {
    "คณิตศาสตร์": "math_bd_logo.png",
    "วิทยาศาสตร์": "sci_bd_logo.png",
    "ภาษาอังกฤษ":  "eng_bd_logo.png",
    "ภาษาไทย":     "thai_bd_logo.png",
}


def _build_cover_url(filename: str) -> str:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not base or not filename:
        return ""
    return f"{base}/storage/v1/object/public/{COVER_PHOTO_BUCKET}/{filename}"


def get_sprint_cover_url(sprint: dict) -> str:
    """คืน URL รูป cover — ใช้ custom ถ้ามี ไม่งั้น default ตาม subject"""
    custom = (sprint.get("cover_photo") or "").strip()
    if custom:
        return custom if custom.startswith("http") else _build_cover_url(custom)
    filename = DEFAULT_COVER_BY_SUBJECT.get(sprint.get("subject", ""), "")
    return _build_cover_url(filename)


def upload_sprint_cover(file_bytes: bytes, filename: str,
                        content_type: str = "image/png") -> str:
    """Upload cover photo ขึ้น Supabase Storage, คืน public URL"""
    if not _use_supabase():
        return ""
    try:
        client = _get_client()
        client.storage.from_(COVER_PHOTO_BUCKET).upload(
            filename, file_bytes,
            {"content-type": content_type, "upsert": "true"},
        )
        return _build_cover_url(filename)
    except Exception:
        try:
            client.storage.from_(COVER_PHOTO_BUCKET).update(
                filename, file_bytes, {"content-type": content_type},
            )
            return _build_cover_url(filename)
        except Exception:
            return ""


# ─────────────────────────────────────────
# Sprint helpers (Supabase)
# ─────────────────────────────────────────

def _calc_mins(sp: dict) -> int:
    """คำนวณชั่วโมงสอน (นาที) จาก start_time/end_time หรือ minutes เดิม"""
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


def _serialize_cohort_sprint(cs: dict, road_id: str, order_index: int) -> dict:
    """แปลง cohort_sprint dict → row สำหรับ insert ลง cohort_sprints table"""
    return {
        "id":              str(cs.get("id") or uuid.uuid4()),
        "victory_road_id": road_id,
        "name":            cs.get("name", ""),
        "sprint_type":     cs.get("sprint_type", "foundation"),
        "order_index":     order_index,
    }


def _serialize_sprint(sp: dict, road_id: str, order_index: int,
                       cohort_sprint_id: str | None = None) -> dict:
    """แปลง sprint dict → row สำหรับ insert ลง sprints table"""
    d = sp.get("date")
    if isinstance(d, date):
        date_str = d.isoformat()
    elif isinstance(d, str) and d:
        date_str = d[:10]
    else:
        date_str = None

    scores = sp.get("student_scores", {})
    if isinstance(scores, str):
        try:
            scores = json.loads(scores)
        except Exception:
            scores = {}

    return {
        "id":               str(sp.get("id") or uuid.uuid4()),
        "victory_road_id":  road_id,
        "cohort_sprint_id": cohort_sprint_id,
        "name":             sp.get("name", ""),
        "subject":          sp.get("subject", "คณิตศาสตร์"),
        "sprint_type":      sp.get("sprint_type", "foundation"),
        "date":             date_str,
        "start_time":       sp.get("start_time", ""),
        "end_time":         sp.get("end_time", ""),
        "minutes":          _calc_mins(sp),
        "teacher":          sp.get("teacher", "—"),
        "lecture_link":     sp.get("lecture_link", ""),
        "ws_link":          sp.get("ws_link", ""),
        "done":             bool(sp.get("done", False)),
        "student_scores":   scores,
        "order_index":      order_index,
        "cover_photo":      sp.get("cover_photo", ""),
    }


def _save_road_content(road_id: str, sprints: list, cohort_sprints: list) -> bool:
    """ลบ content เก่าของ road แล้ว insert ใหม่ทั้งหมด
    - sprints: personal sprints (Personalize VR)
    - cohort_sprints: cohort parent sprints พร้อม sub_sprints: [...] (Cohort VR)
    """
    client = _get_client()
    # ลบ sprints ทั้งหมดของ road (personal + sub-sprints)
    client.table("sprints").delete().eq("victory_road_id", road_id).execute()
    # ลบ cohort_sprints ทั้งหมดของ road
    client.table("cohort_sprints").delete().eq("victory_road_id", road_id).execute()

    # Insert personal sprints
    if sprints:
        rows = [_serialize_sprint(sp, road_id, i) for i, sp in enumerate(sprints)]
        client.table("sprints").insert(rows).execute()

    # Insert cohort_sprints → sub-sprints
    if cohort_sprints:
        cs_rows = [_serialize_cohort_sprint(cs, road_id, i)
                   for i, cs in enumerate(cohort_sprints)]
        client.table("cohort_sprints").insert(cs_rows).execute()
        sub_rows = []
        for cs, cs_row in zip(cohort_sprints, cs_rows):
            for j, sub in enumerate(cs.get("sub_sprints", [])):
                sub_rows.append(_serialize_sprint(sub, road_id, j,
                                                  cohort_sprint_id=cs_row["id"]))
        if sub_rows:
            client.table("sprints").insert(sub_rows).execute()
    return True


def _load_sprints_for_roads(road_ids: list) -> tuple[dict, dict]:
    """โหลด sprints + cohort_sprints ใน 2 queries แล้วแบ่งกลุ่มตาม road_id
    คืน (personal_by_road, cohort_by_road) โดย cohort แต่ละตัวมี sub_sprints: [...]
    """
    if not road_ids:
        return {}, {}
    client = _get_client()

    # โหลด sprints ทั้งหมด (personal + sub-sprints)
    sp_res = (
        client.table("sprints")
        .select("*")
        .in_("victory_road_id", road_ids)
        .order("order_index")
        .execute()
    )
    personal_by_road: dict = {}
    sub_by_cohort: dict = {}  # {cohort_sprint_id: [sub-sprint rows]}

    for sp in (sp_res.data or []):
        ss = sp.get("student_scores", {})
        if isinstance(ss, str):
            try:
                sp["student_scores"] = json.loads(ss)
            except Exception:
                sp["student_scores"] = {}
        if sp.get("cohort_sprint_id"):
            sub_by_cohort.setdefault(sp["cohort_sprint_id"], []).append(sp)
        else:
            personal_by_road.setdefault(sp["victory_road_id"], []).append(sp)

    # โหลด cohort_sprints
    cs_res = (
        client.table("cohort_sprints")
        .select("*")
        .in_("victory_road_id", road_ids)
        .order("order_index")
        .execute()
    )
    cohort_by_road: dict = {}
    for cs in (cs_res.data or []):
        cs["sub_sprints"] = sub_by_cohort.get(cs["id"], [])
        cohort_by_road.setdefault(cs["victory_road_id"], []).append(cs)

    return personal_by_road, cohort_by_road


# ═══════════════════════════════════════════
# CACHED READ HELPERS (Supabase only — no st.* calls inside)
# ═══════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_all_victory_roads() -> list:
    client = _get_client()
    res = client.table("victory_roads").select("*").order("created_at", desc=True).execute()
    roads = res.data or []
    for r in roads:
        if isinstance(r.get("students"), str):
            try:
                r["students"] = json.loads(r["students"])
            except Exception:
                r["students"] = []
    if roads:
        road_ids = [r["id"] for r in roads]
        personal_by_road, cohort_by_road = _load_sprints_for_roads(road_ids)
        for r in roads:
            r["sprints"]        = personal_by_road.get(r["id"], [])
            r["cohort_sprints"] = cohort_by_road.get(r["id"], [])
    return roads


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_all_students() -> list:
    res = _get_client().table("students").select("*").order("created_at", desc=True).execute()
    return res.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_all_teachers() -> list:
    res = _get_client().table("teachers").select("*").order("created_at", desc=False).execute()
    return res.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_sprint_attendance(sprint_id: str) -> list:
    res = _get_client().table("sprint_attendance").select("*").eq("sprint_id", sprint_id).execute()
    return res.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_sprint_attendance_batch(sprint_ids: tuple) -> dict:
    """Batch fetch attendance — keyed by tuple for stable cache"""
    if not sprint_ids:
        return {}
    res = (
        _get_client()
        .table("sprint_attendance")
        .select("*")
        .in_("sprint_id", list(sprint_ids))
        .execute()
    )
    by_sprint: dict = {}
    for rec in (res.data or []):
        by_sprint.setdefault(rec["sprint_id"], []).append(rec)
    return by_sprint


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_student_payments() -> list:
    res = _get_client().table("student_payments").select("*").execute()
    return res.data or []


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_teacher_expenses() -> list:
    res = (
        _get_client()
        .table("teacher_expenses")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


# ═══════════════════════════════════════════
# VICTORY ROADS
# ═══════════════════════════════════════════

def get_all_victory_roads() -> list:
    if _use_supabase():
        try:
            return _fetch_all_victory_roads()
        except Exception as e:
            st.warning(f"Supabase: {e} — ใช้ข้อมูล local แทน")
    return _ss("victory_roads", [])


def create_victory_road(data: dict) -> dict:
    if _use_supabase():
        try:
            client = _get_client()
            payload = {
                "name":        data["name"],
                "description": data.get("description", ""),
                "level":       data.get("level", ""),
                "road_type":   data.get("road_type", "cohort"),
                "students":    json.dumps(data.get("students", []), ensure_ascii=False),
                "status":      data.get("status", "draft"),
            }
            res = client.table("victory_roads").insert(payload).execute()
            vr = res.data[0] if res.data else {}
            if vr.get("id"):
                _save_road_content(vr["id"],
                                   data.get("sprints", []),
                                   data.get("cohort_sprints", []))
            vr["sprints"]        = data.get("sprints", [])
            vr["cohort_sprints"] = data.get("cohort_sprints", [])
            _fetch_all_victory_roads.clear()
            return vr
        except Exception as e:
            st.error(f"Supabase create_victory_road: {e}")
    vr = {**data, "id": str(uuid.uuid4()), "created_at": datetime.now().isoformat()}
    vr.setdefault("sprints", [])
    vr.setdefault("cohort_sprints", [])
    _ss("victory_roads", []).append(vr)
    return vr


def update_victory_road(vr_id: str, data: dict) -> bool:
    if _use_supabase():
        try:
            client = _get_client()
            road_payload = {}
            for k in ("name", "description", "level", "road_type", "status"):
                if k in data and data[k] is not None:
                    road_payload[k] = data[k]
            if "students" in data:
                road_payload["students"] = json.dumps(data["students"], ensure_ascii=False)
            if road_payload:
                client.table("victory_roads").update(road_payload).eq("id", vr_id).execute()
            if "sprints" in data or "cohort_sprints" in data:
                _save_road_content(vr_id,
                                   data.get("sprints", []),
                                   data.get("cohort_sprints", []))
            _fetch_all_victory_roads.clear()
            return True
        except Exception as e:
            st.error(f"Supabase update_victory_road: {e}")
    for vr in _ss("victory_roads", []):
        if vr["id"] == vr_id:
            vr.update(data)
    return True


def delete_victory_road(vr_id: str) -> bool:
    if _use_supabase():
        try:
            _get_client().table("victory_roads").delete().eq("id", vr_id).execute()
            _fetch_all_victory_roads.clear()
            return True
        except Exception as e:
            st.error(f"Supabase: {e}")
    st.session_state.victory_roads = [v for v in _ss("victory_roads", []) if v["id"] != vr_id]
    return True


def publish_victory_road(vr_id: str, publish: bool = True) -> bool:
    return update_victory_road(vr_id, {"status": "published" if publish else "draft"})


# ═══════════════════════════════════════════
# STUDENTS
# ═══════════════════════════════════════════

def get_all_students() -> list:
    if _use_supabase():
        try:
            return _fetch_all_students()
        except Exception as e:
            st.warning(f"Supabase: {e} — ใช้ข้อมูล local แทน")
    return _ss("students", [])


def create_student(data: dict) -> dict:
    if _use_supabase():
        try:
            res = _get_client().table("students").insert(data).execute()
            _fetch_all_students.clear()
            return res.data[0] if res.data else {}
        except Exception as e:
            st.error(f"Supabase: {e}")
    student = {**data, "id": str(uuid.uuid4()), "created_at": datetime.now().isoformat()}
    _ss("students", []).append(student)
    return student


def update_student(student_id: str, data: dict) -> bool:
    if _use_supabase():
        try:
            _get_client().table("students").update(data).eq("id", student_id).execute()
            _fetch_all_students.clear()
            return True
        except Exception as e:
            st.error(f"Supabase: {e}")
    for s in _ss("students", []):
        if s["id"] == student_id:
            s.update(data)
    return True


def delete_student(student_id: str) -> bool:
    if _use_supabase():
        try:
            _get_client().table("students").delete().eq("id", student_id).execute()
            _fetch_all_students.clear()
            return True
        except Exception as e:
            st.error(f"Supabase: {e}")
    st.session_state.students = [s for s in _ss("students", []) if s["id"] != student_id]
    return True


# ═══════════════════════════════════════════
# TEACHERS
# ═══════════════════════════════════════════

def get_all_teachers() -> list:
    if _use_supabase():
        try:
            return _fetch_all_teachers()
        except Exception as e:
            st.warning(f"Supabase: {e} — ใช้ข้อมูล local แทน")
    return _ss("teachers", [])


def create_teacher(data: dict) -> dict:
    if _use_supabase():
        try:
            res = _get_client().table("teachers").insert(data).execute()
            _fetch_all_teachers.clear()
            return res.data[0] if res.data else {}
        except Exception as e:
            st.error(f"Supabase: {e}")
    teacher = {**data, "id": str(uuid.uuid4()), "created_at": datetime.now().isoformat()}
    _ss("teachers", []).append(teacher)
    return teacher


def update_teacher(teacher_id: str, data: dict) -> bool:
    if _use_supabase():
        try:
            _get_client().table("teachers").update(data).eq("id", teacher_id).execute()
            _fetch_all_teachers.clear()
            return True
        except Exception as e:
            st.error(f"Supabase: {e}")
    for t in _ss("teachers", []):
        if t["id"] == teacher_id:
            t.update(data)
    return True


def delete_teacher(teacher_id: str) -> bool:
    if _use_supabase():
        try:
            _get_client().table("teachers").delete().eq("id", teacher_id).execute()
            _fetch_all_teachers.clear()
            return True
        except Exception as e:
            st.error(f"Supabase: {e}")
    st.session_state.teachers = [t for t in _ss("teachers", []) if t["id"] != teacher_id]
    return True


# ═══════════════════════════════════════════
# STUDENT PERFORMANCE
# ═══════════════════════════════════════════

def upsert_student_performance(records: list) -> bool:
    """
    Upsert normalized score records → student_performance table
    ทุกครั้งที่ admin บันทึกคะแนน จะเรียกฟังก์ชันนี้เพื่อ sync ข้อมูล

    records: [{
        student_id, sprint_id, victory_road_id,
        subject, date, earned, max, score_pct
    }]
    records ที่ไม่มี student_id (VR เก่า string format) จะถูกข้ามไป
    """
    if not _use_supabase() or not records:
        return False
    valid = [r for r in records if r.get("student_id") and r.get("sprint_id")]
    if not valid:
        return True
    try:
        _get_client().table("student_performance").upsert(
            valid, on_conflict="student_id,sprint_id"
        ).execute()
        return True
    except Exception as e:
        st.error(f"student_performance upsert: {e}")
        return False


# ═══════════════════════════════════════════
# SCHEDULER — แปลง sprints เป็น calendar events
# ═══════════════════════════════════════════

SUBJECT_COLORS = {
    "คณิตศาสตร์": "#FF6B6B",
    "วิทยาศาสตร์": "#4ECDC4",
    "ภาษาอังกฤษ": "#45B7D1",
    "ภาษาไทย":    "#96CEB4",
}


def get_sim_open() -> bool:
    if _use_supabase():
        res = _get_client().table("app_settings").select("value").eq("key", "sim_open").execute()
        rows = res.data or []
        if rows:
            return rows[0]["value"] == "true"
    return False


def set_sim_open(value: bool) -> None:
    if _use_supabase():
        _get_client().table("app_settings").upsert(
            {"key": "sim_open", "value": "true" if value else "false"}
        ).execute()


# ═══════════════════════════════════════════
# STUDENT PAYMENTS
# ═══════════════════════════════════════════

def get_student_payments() -> list:
    """คืน payment records ทั้งหมด"""
    if _use_supabase():
        try:
            return _fetch_student_payments()
        except Exception:
            pass
    return _ss("student_payments", [])


def upsert_student_payment(student_id: str, victory_road_id: str, status: str,
                           amount: float = 0, note: str = "",
                           fee: float = 0) -> bool:
    """สร้างหรืออัปเดต payment status + amount + fee + note สำหรับ student-VR pair
    fee  = ค่าเรียนทั้งหมดที่ต้องจ่าย (total tuition)
    amount = ยอดที่รับแล้ว (received)
    outstanding = fee - amount
    """
    if _use_supabase():
        try:
            _get_client().table("student_payments").upsert(
                {
                    "student_id":      student_id,
                    "victory_road_id": victory_road_id,
                    "payment_status":  status,
                    "amount":          amount,
                    "fee":             fee,
                    "note":            note,
                    "updated_at":      datetime.now().isoformat(),
                },
                on_conflict="student_id,victory_road_id",
            ).execute()
            _fetch_student_payments.clear()
            return True
        except Exception as e:
            st.error(f"upsert_student_payment: {e}")
            return False
    payments = _ss("student_payments", [])
    for p in payments:
        if p["student_id"] == student_id and p["victory_road_id"] == victory_road_id:
            p.update({"payment_status": status, "amount": amount, "fee": fee, "note": note})
            return True
    payments.append({
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "victory_road_id": victory_road_id,
        "payment_status": status,
        "amount": amount,
        "fee": fee,
        "note": note,
        "updated_at": datetime.now().isoformat(),
    })
    return True


def check_student_can_login(student_id: str, enrolled_vr_ids: list) -> bool:
    """
    คืน True ถ้า payment_status ของ student ทุก VR ที่ลงทะเบียนเป็น 'success'
    ใช้ตรวจสอบก่อน login
    """
    if not enrolled_vr_ids:
        return True
    payments = get_student_payments()
    paid_vrs = {
        p["victory_road_id"]
        for p in payments
        if p["student_id"] == student_id and p["payment_status"] == "success"
    }
    return all(vr_id in paid_vrs for vr_id in enrolled_vr_ids)


# ═══════════════════════════════════════════
# TEACHER EXPENSES
# ═══════════════════════════════════════════

def get_teacher_expenses() -> list:
    if _use_supabase():
        try:
            return _fetch_teacher_expenses()
        except Exception:
            pass
    return _ss("teacher_expenses", [])


def upsert_teacher_expense(data: dict) -> bool:
    """Upsert teacher expense — UNIQUE(sprint_id, teacher_id)"""
    if _use_supabase():
        try:
            _get_client().table("teacher_expenses").upsert(
                data, on_conflict="sprint_id,teacher_id"
            ).execute()
            _fetch_teacher_expenses.clear()
            return True
        except Exception as e:
            st.error(f"upsert_teacher_expense: {e}")
            return False
    expenses = _ss("teacher_expenses", [])
    for ex in expenses:
        if ex.get("sprint_id") == data.get("sprint_id") and ex.get("teacher_id") == data.get("teacher_id"):
            ex.update(data)
            return True
    expenses.append({**data, "id": str(uuid.uuid4()), "created_at": datetime.now().isoformat()})
    return True


def delete_teacher_expense(expense_id: str) -> bool:
    if _use_supabase():
        try:
            _get_client().table("teacher_expenses").delete().eq("id", expense_id).execute()
            _fetch_teacher_expenses.clear()
            return True
        except Exception as e:
            st.error(f"delete_teacher_expense: {e}")
    st.session_state.teacher_expenses = [
        e for e in _ss("teacher_expenses", []) if e.get("id") != expense_id
    ]
    return True


# ═══════════════════════════════════════════
# SPRINT — individual update (ไม่ delete+recreate)
# ═══════════════════════════════════════════

def update_sprint(sprint_id: str, data: dict) -> bool:
    """อัพเดท field เฉพาะของ sprint (done, etc.) โดยไม่ลบ attendance records"""
    if _use_supabase():
        try:
            _get_client().table("sprints").update(data).eq("id", sprint_id).execute()
            _fetch_all_victory_roads.clear()
            return True
        except Exception as e:
            st.error(f"update_sprint: {e}")
    for vr in _ss("victory_roads", []):
        for sp in vr.get("sprints", []):
            if str(sp.get("id")) == str(sprint_id):
                sp.update(data)
    return True


# ═══════════════════════════════════════════
# SPRINT ATTENDANCE
# ═══════════════════════════════════════════

def get_sprint_attendance(sprint_id: str) -> list:
    """โหลด attendance records ทั้งหมดของ sprint นี้"""
    if _use_supabase():
        try:
            return _fetch_sprint_attendance(sprint_id)
        except Exception:
            pass
    return _ss(f"att_{sprint_id}", [])


def get_sprint_attendance_batch(sprint_ids: list) -> dict:
    """Fetch attendance สำหรับหลาย sprint ใน 1 query
    Returns: {sprint_id: [attendance_records]}
    """
    if _use_supabase() and sprint_ids:
        try:
            return _fetch_sprint_attendance_batch(tuple(sprint_ids))
        except Exception:
            pass
    return {sid: _ss(f"att_{sid}", []) for sid in sprint_ids}


def upsert_sprint_attendance(
    sprint_id: str,
    student_id: str,
    status: str,
    teacher_feedback: str = "",
    student_ws_link: str = "",
) -> bool:
    """Upsert attendance record ของนักเรียน 1 คนใน sprint นี้"""
    if _use_supabase():
        try:
            _get_client().table("sprint_attendance").upsert(
                {
                    "sprint_id":        sprint_id,
                    "student_id":       student_id,
                    "status":           status,
                    "teacher_feedback": teacher_feedback,
                    "student_ws_link":  student_ws_link,
                    "updated_at":       datetime.now().isoformat(),
                },
                on_conflict="sprint_id,student_id",
            ).execute()
            _fetch_sprint_attendance.clear()
            _fetch_sprint_attendance_batch.clear()
            return True
        except Exception:
            pass
    key     = f"att_{sprint_id}"
    records = _ss(key, [])
    for r in records:
        if r.get("student_id") == student_id:
            r["status"]           = status
            r["teacher_feedback"] = teacher_feedback
            r["student_ws_link"]  = student_ws_link
            return True
    records.append({
        "sprint_id": sprint_id, "student_id": student_id,
        "status": status, "teacher_feedback": teacher_feedback,
        "student_ws_link": student_ws_link,
    })
    return True


def get_calendar_events() -> list:
    def _nick(s):
        if isinstance(s, dict):
            return s.get("nickname") or s.get("name") or str(s)
        txt = str(s)
        return txt.split(":")[0].strip() if ":" in txt else txt

    vrs = get_all_victory_roads()
    events = []
    for vr in vrs:
        road_type = vr.get("road_type", "cohort")
        vr_students = [_nick(s) for s in vr.get("students", [])]

        # รวม personal sprints + sub-sprints ของ cohort (เก็บ parent cohort name ไว้ด้วย)
        all_sprints = []
        for sp in vr.get("sprints", []):
            all_sprints.append({**sp, "_cohort_name": ""})
        for cs in vr.get("cohort_sprints", []):
            for sub in cs.get("sub_sprints", []):
                all_sprints.append({**sub, "_cohort_name": cs.get("name", "")})

        for sp in all_sprints:
            raw = sp.get("date")
            if not raw:
                continue
            date_str = raw if isinstance(raw, str) else raw.isoformat()

            # Title: "VR name" หรือ "VR name - sub-sprint name" สำหรับ cohort
            cohort_suffix = f" — {sp['_cohort_name']}" if sp.get("_cohort_name") else ""
            title = f"{vr['name']}{cohort_suffix}"

            # Sprint type label
            _sprint_type_map = {
                "foundation": "Foundation",
                "regular":    "Regular",
                "test":       "ทดสอบ",
                "review":     "Review",
            }
            sprint_type_label = _sprint_type_map.get(sp.get("sprint_type", ""), sp.get("sprint_type", ""))

            _st = sp.get("start_time", "")
            _et = sp.get("end_time", "")

            props = {
                "vr_name":          vr["name"],
                "level":            vr.get("level", ""),
                "road_type":        road_type,
                "sprint_name":      sp.get("name", ""),
                "sprint_type":      sprint_type_label,
                "teacher":          sp.get("teacher", ""),
                "subject":          sp.get("subject", ""),
                "start_time":       _st,
                "end_time":         _et,
                "lecture_link":     sp.get("lecture_link", ""),
            }
            if road_type == "personalize":
                props["students"] = vr_students
            if _st and _et:
                ev_start = f"{date_str[:10]}T{_st}:00"
                ev_end   = f"{date_str[:10]}T{_et}:00"
            else:
                ev_start = date_str[:10]
                ev_end   = date_str[:10]

            events.append({
                "title": title,
                "start": ev_start,
                "end":   ev_end,
                "color": "#3788d8",
                "extendedProps": props,
            })
    return events
