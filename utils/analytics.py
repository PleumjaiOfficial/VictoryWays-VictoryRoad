"""
Victory Road — Analytics Utilities
เครื่องมือวิเคราะห์คะแนนนักเรียน: normalize → regression → chart
"""

from datetime import date, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go


# ─────────────────────────────────────────────────────────────
# 1. Data Loading
# ─────────────────────────────────────────────────────────────

def load_scores_df(sprints: list, nickname: str | None = None) -> pd.DataFrame:
    """
    แปลง sprints list → DataFrame พร้อม normalized score (%)

    ถ้า nickname=None → เฉลี่ยคะแนนนักเรียนทุกคนใน sprint (cohort mode)
    ถ้า nickname=str  → ดึงเฉพาะคะแนนของนักเรียนคนนั้น (personalize mode)

    คอลัมน์ผลลัพธ์:
        date        : date
        subject     : str
        sprint_name : str
        sprint_type : str
        score_pct   : float   (earned/max * 100, normalized)
        n_students  : int     (จำนวนนักเรียนที่มีคะแนน — cohort mode เท่านั้น)
    """
    rows = []
    for sp in sprints:
        raw_date = sp.get("date")
        if not raw_date:
            continue
        if isinstance(raw_date, str):
            try:
                sp_date = date.fromisoformat(raw_date[:10])
            except ValueError:
                continue
        elif isinstance(raw_date, date):
            sp_date = raw_date
        else:
            continue

        subject     = sp.get("subject", "")
        sprint_name = sp.get("name", "")
        sprint_type = sp.get("sprint_type", "foundation")
        scores_map  = sp.get("student_scores", {}) or {}

        if nickname is not None:
            # personalize: คะแนนของคนเดียว
            sc = scores_map.get(nickname, {})
            if sc and sc.get("max"):
                pct = sc["earned"] / sc["max"] * 100
                rows.append({
                    "date":        sp_date,
                    "subject":     subject,
                    "sprint_name": sprint_name,
                    "sprint_type": sprint_type,
                    "score_pct":   round(pct, 1),
                    "n_students":  1,
                })
        else:
            # cohort: เฉลี่ยทุกคนที่มีคะแนน
            pcts = [
                sc["earned"] / sc["max"] * 100
                for sc in scores_map.values()
                if sc and sc.get("max")
            ]
            if pcts:
                rows.append({
                    "date":        sp_date,
                    "subject":     subject,
                    "sprint_name": sprint_name,
                    "sprint_type": sprint_type,
                    "score_pct":   round(np.mean(pcts), 1),
                    "n_students":  len(pcts),
                })

    if not rows:
        return pd.DataFrame(columns=["date", "subject", "sprint_name",
                                     "sprint_type", "score_pct", "n_students"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────
# 2. Regression
# ─────────────────────────────────────────────────────────────

def compute_regression_by_subject(df: pd.DataFrame,
                                  min_points: int = 3) -> pd.DataFrame:
    """
    คำนวณ linear regression ต่อ subject

    ต้องการ ≥ min_points จุดต่อ subject ถึงจะ fit

    คอลัมน์เพิ่มในผลลัพธ์:
        x_num      : int    (วันนับจาก sprint แรกของ subject)
        regression : float  (ค่า regression ที่จุดนั้น)
        slope_pct  : float  (slope หน่วย %/วัน)
        r2         : float  (R² coefficient of determination)
    """
    result_parts = []
    for subject, g in df.groupby("subject"):
        g = g.sort_values("date").copy()
        origin = g["date"].iloc[0]
        g["x_num"] = (g["date"] - origin).dt.days

        x = g["x_num"].values
        y = g["score_pct"].values

        if len(x) >= min_points:
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs
            g["regression"] = slope * x + intercept
            # R²
            y_hat = slope * x + intercept
            ss_res = np.sum((y - y_hat) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
            g["slope_pct"] = round(slope, 4)
            g["r2"]        = round(r2, 3)
        else:
            g["regression"] = np.nan
            g["slope_pct"]  = np.nan
            g["r2"]         = np.nan

        result_parts.append(g)

    if not result_parts:
        return df.copy()
    return pd.concat(result_parts).sort_values(["subject", "date"]).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────
# 3. Bar Chart (แยกตามวิชา)
# ─────────────────────────────────────────────────────────────

SUBJECT_COLOR = {
    "คณิตศาสตร์": "#FF6B6B",
    "วิทยาศาสตร์": "#4ECDC4",
    "ภาษาอังกฤษ": "#45B7D1",
    "ภาษาไทย":    "#96CEB4",
}


def build_subject_bar_chart(df: pd.DataFrame,
                            title: str = "📊 คะแนนเฉลี่ยรายวิชา") -> go.Figure:
    """
    Bar chart: X = subject, Y = avg score_pct
    แต่ละ subject = bar 1 อัน, สีตาม SUBJECT_COLOR
    แสดง sprint ย่อยแต่ละอันเป็น scatter overlay เพื่อดู distribution
    """
    if df.empty:
        return go.Figure()

    # สรุปเฉลี่ยต่อ subject
    summary = (
        df.groupby("subject")
        .agg(avg_pct=("score_pct", "mean"),
             min_pct=("score_pct", "min"),
             max_pct=("score_pct", "max"),
             n_sprints=("score_pct", "count"))
        .reset_index()
    )

    subjects  = summary["subject"].tolist()
    colors    = [SUBJECT_COLOR.get(s, "#AAAAAA") for s in subjects]
    avg_pcts  = summary["avg_pct"].round(1).tolist()

    fig = go.Figure()

    # ── bars (เฉลี่ยต่อวิชา)
    fig.add_trace(go.Bar(
        x=subjects,
        y=avg_pcts,
        marker_color=colors,
        marker_line_color="white",
        marker_line_width=1.5,
        text=[f"{v:.1f}%" for v in avg_pcts],
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "เฉลี่ย: %{y:.1f}%<br>"
            "ต่ำสุด: %{customdata[0]:.1f}%<br>"
            "สูงสุด: %{customdata[1]:.1f}%<br>"
            "Sprint: %{customdata[2]} ครั้ง<extra></extra>"
        ),
        customdata=list(zip(
            summary["min_pct"].round(1),
            summary["max_pct"].round(1),
            summary["n_sprints"],
        )),
        showlegend=False,
    ))

    # ── scatter overlay (แต่ละ sprint แสดงเป็นจุด)
    for subj, g in df.groupby("subject"):
        fig.add_trace(go.Scatter(
            x=[subj] * len(g),
            y=g["score_pct"].tolist(),
            mode="markers",
            marker=dict(
                size=8,
                color="white",
                line=dict(width=1.5, color=SUBJECT_COLOR.get(str(subj), "#888")),
            ),
            text=g["sprint_name"].tolist(),
            hovertemplate="Sprint: %{text}<br>คะแนน: %{y:.1f}%<extra></extra>",
            showlegend=False,
        ))

    # reference lines
    fig.add_hline(y=80, line_dash="dash", line_color="green",
                  annotation_text="เป้าหมาย 80%", opacity=0.6)
    fig.add_hline(y=50, line_dash="dash", line_color="orange",
                  annotation_text="เส้นผ่าน 50%", opacity=0.6)

    fig.update_layout(
        title=title,
        xaxis_title="วิชา",
        yaxis_title="คะแนนเฉลี่ย (%)",
        yaxis=dict(range=[0, 115]),
        height=500,
        plot_bgcolor="white",
        paper_bgcolor="white",
        bargap=0.35,
    )
    return fig


# ─────────────────────────────────────────────────────────────
# 4. Summary Stats (per subject)
# ─────────────────────────────────────────────────────────────

def summarize_by_subject(df: pd.DataFrame) -> pd.DataFrame:
    """สรุปสถิติต่อ subject: sprint count, avg%, min%, max%"""
    rows = []
    for subject, g in df.groupby("subject"):
        g = g.sort_values("date")
        rows.append({
            "วิชา":       subject,
            "Sprint":     int(len(g)),
            "เฉลี่ย (%)": round(g["score_pct"].mean(), 1),
            "ต่ำสุด (%)": round(g["score_pct"].min(), 1),
            "สูงสุด (%)": round(g["score_pct"].max(), 1),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# 5. Regression (reserved for future use)
# ─────────────────────────────────────────────────────────────

def compute_regression_by_subject(df: pd.DataFrame,
                                  min_points: int = 3) -> pd.DataFrame:
    """
    [สำรองไว้ — ยังไม่ใช้งาน]
    คำนวณ linear regression ต่อ subject
    """
    result_parts = []
    for subject, g in df.groupby("subject"):
        g = g.sort_values("date").copy()
        origin = g["date"].iloc[0]
        g["x_num"] = (g["date"] - origin).dt.days
        x = g["x_num"].values
        y = g["score_pct"].values
        if len(x) >= min_points:
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs
            y_hat = slope * x + intercept
            ss_res = np.sum((y - y_hat) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
            g["regression"] = slope * x + intercept
            g["slope_pct"]  = round(slope, 4)
            g["r2"]         = round(r2, 3)
        else:
            g["regression"] = np.nan
            g["slope_pct"]  = np.nan
            g["r2"]         = np.nan
        result_parts.append(g)
    if not result_parts:
        return df.copy()
    return pd.concat(result_parts).sort_values(["subject", "date"]).reset_index(drop=True)
