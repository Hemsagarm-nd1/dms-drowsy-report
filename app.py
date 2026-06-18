from __future__ import annotations

import io
import json
import sqlite3
import time as _time
from datetime import datetime, timedelta, timezone, time as dt_time
from zoneinfo import ZoneInfo

import pandas as pd
import altair as alt
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

from config import (
    SQLITE_DB_PATH,
    TIMEZONE_OPTIONS,
)
from db import fetch_alerts

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="DMS Drowsy Report",
    page_icon=" ",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# Frontend theme and layout styling
st.markdown("""
<style>
:root {
    --dms-bg: #eef3f9;
    --dms-panel: #ffffff;
    --dms-sidebar: #0f172a;
    --dms-sidebar-2: #111827;
    --dms-sidebar-text: #e5edf6;
    --dms-sidebar-muted: #9fb2c9;
    --dms-text: #0f172a;
    --dms-muted: #64748b;
    --dms-border: #dbe7f3;
    --dms-accent: #0284c7;
    --dms-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    --dms-control-height: 56px;
    --dms-control-radius: 14px;
}

@media (prefers-color-scheme: dark) {
    :root {
        --dms-bg: #070f1d;
        --dms-panel: #111827;
        --dms-sidebar: #060d19;
        --dms-sidebar-2: #0b1324;
        --dms-sidebar-text: #dbe7f3;
        --dms-sidebar-muted: #93a6c1;
        --dms-text: #e5edf6;
        --dms-muted: #94a3b8;
        --dms-border: #253347;
        --dms-accent: #38bdf8;
        --dms-shadow: 0 10px 26px rgba(2, 8, 23, 0.45);
    }
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 4% 5%, rgba(14, 165, 233, 0.08), transparent 32%),
        radial-gradient(circle at 96% 0%, rgba(15, 23, 42, 0.08), transparent 30%),
        var(--dms-bg);
    color: var(--dms-text);
}

[data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 0 !important;
    padding-bottom: 1rem;
    max-width: 100%;
}

h1, h2, h3 {
    letter-spacing: 0.01em;
}

iframe[title="streamlit_autorefresh.st_autorefresh"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
}

div:has(> iframe[title="streamlit_autorefresh.st_autorefresh"]) {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--dms-sidebar) 0%, var(--dms-sidebar-2) 100%);
    border-right: 1px solid rgba(148, 163, 184, 0.25);
}

section[data-testid="stSidebar"] * {
    color: var(--dms-sidebar-text);
}

section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--dms-sidebar-muted);
}

section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="input"] > div {
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(148, 163, 184, 0.35);
    border-radius: 10px;
}

section[data-testid="stSidebar"] [data-testid="stAlert"] {
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.35);
}

section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

section[data-testid="stSidebar"] h1 {
    margin-top: 0 !important;
    font-size: 1.75rem;
}

/* Sidebar brand header */
.dms-nav-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    min-height: var(--dms-control-height);
    padding: 0.65rem 0.9rem;
    margin: 0 0 0.35rem 0;
    box-sizing: border-box;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: var(--dms-control-radius);
    background: rgba(15, 23, 42, 0.35);
}
.dms-nav-logo {
    width: 1.7rem;
    min-width: 1.7rem;
    height: 1.7rem;
    display: inline-flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.18rem;
    padding: 0.32rem;
    border-radius: 12px;
    background: rgba(56, 189, 248, 0.12);
    box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.18);
}
.dms-nav-logo span {
    display: block;
    height: 2px;
    width: 100%;
    border-radius: 999px;
    background: var(--dms-sidebar-text);
}
.dms-nav-title {
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.2px;
    line-height: 1.1;
}
.dms-nav-sub {
    font-size: 0.72rem;
    color: var(--dms-sidebar-muted);
}

/* Sidebar page navigation styled as nav items */
section[data-testid="stSidebar"] [data-testid="stRadio"] {
    width: 100% !important;
    max-width: none !important;
    margin-bottom: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    width: 100% !important;
    max-width: none !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] {
    width: 100% !important;
    max-width: none !important;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}
section[data-testid="stSidebar"] [data-testid="stDivider"] {
    margin-top: 0.35rem !important;
    margin-bottom: 0.75rem !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] > label,
section[data-testid="stSidebar"] [role="radiogroup"] > div,
section[data-testid="stSidebar"] [role="radiogroup"] [data-baseweb="radio"] {
    width: 100% !important;
    max-width: none !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] label {
    display: flex !important;
    align-items: center;
    justify-content: flex-start;
    width: 100% !important;
    max-width: none !important;
    flex: 1 1 auto;
    box-sizing: border-box;
    min-height: var(--dms-control-height);
    padding: 0.65rem 0.9rem;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.62);
    border-radius: var(--dms-control-radius);
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(148, 163, 184, 0.14);
    border-color: rgba(148, 163, 184, 0.55);
}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(56, 189, 248, 0.22);
    border-color: rgba(56, 189, 248, 0.9);
    box-shadow: inset 3px 0 0 var(--dms-accent);
    font-weight: 600;
}
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
    display: none;
}

section[data-testid="stSidebar"] [data-testid="stButton"] > button,
section[data-testid="stSidebar"] [data-testid="stDownloadButton"] > button {
    border-radius: 10px;
}

.sticky-report-header {
    position: sticky;
    top: 0;
    z-index: 40;
    background: color-mix(in srgb, var(--dms-panel) 92%, transparent);
    border: 1px solid var(--dms-border);
    border-radius: 14px;
    box-shadow: var(--dms-shadow);
    padding: 0.7rem 1rem;
    margin-bottom: 0.8rem;
    backdrop-filter: blur(6px);
}

.sticky-report-header h1 {
    margin: 0 !important;
    color: var(--dms-text);
}

.sticky-report-header p {
    margin: 0.2rem 0 0 0;
    color: var(--dms-muted);
    font-size: 0.95rem;
}

[data-testid="stMetric"] {
    background: var(--dms-panel);
    border: 1px solid var(--dms-border);
    border-radius: 14px;
    padding: 0.8rem 0.9rem;
    box-shadow: 0 4px 14px color-mix(in srgb, var(--dms-text) 12%, transparent);
}

[data-testid="stMetricLabel"] {
    color: var(--dms-muted);
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: var(--dms-text);
}

[data-baseweb="tab-list"] {
    gap: 0.45rem;
}

button[role="tab"] {
    border-radius: 10px 10px 0 0 !important;
    padding: 0.5rem 0.8rem !important;
}

button[role="tab"][aria-selected="true"] {
    color: var(--dms-accent) !important;
    border-bottom-color: var(--dms-accent) !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--dms-border);
    border-radius: 12px;
    overflow: visible;
    box-shadow: 0 6px 18px color-mix(in srgb, var(--dms-text) 10%, transparent);
}
[data-testid="stDataFrame"] [data-testid="stElementToolbar"] {
    opacity: 1 !important;
    visibility: visible !important;
}
[data-testid="stDataFrame"] [data-testid="stElementToolbarButton"] {
    opacity: 1 !important;
    visibility: visible !important;
}

[data-testid="stToggle"] {
    background: var(--dms-panel);
    border: 1px solid var(--dms-border);
    border-radius: 12px;
    padding: 0.35rem 0.55rem;
}
</style>
""", unsafe_allow_html=True)

# Auto-refresh UI every 30 seconds (can be paused from sidebar)
if "auto_refresh_enabled" not in st.session_state:
    st.session_state["auto_refresh_enabled"] = False

if st.session_state["auto_refresh_enabled"]:
    st_autorefresh(interval=30_000, key="dashboard_refresh")


# ── SQLite helpers (Local Cache) ──────────────────────────────────────────────

def _db():
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_tables():
    conn = _db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS alerts_cache (
            window_key TEXT PRIMARY KEY,
            data_json  TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def get_cached_alerts(window_key: str) -> list[dict] | None:
    conn = _db()
    row = conn.execute(
        "SELECT data_json FROM alerts_cache WHERE window_key = ?", (window_key,)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def set_cached_alerts(window_key: str, data: list[dict]):
    conn = _db()
    # Optional: Clear old cache entries to keep DB small
    conn.execute("DELETE FROM alerts_cache WHERE window_key != ?", (window_key,))
    conn.execute(
        "INSERT OR REPLACE INTO alerts_cache (window_key, data_json) VALUES (?, ?)",
        (window_key, json.dumps(data, default=str)),
    )
    conn.commit()
    conn.close()


def get_stored_start_ts() -> datetime | None:
    conn = _db()
    row = conn.execute(
        "SELECT value FROM config WHERE key = 'start_timestamp'"
    ).fetchone()
    conn.close()
    if row:
        dt = datetime.fromisoformat(row[0])
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def get_stored_end_ts() -> datetime | None:
    conn = _db()
    row = conn.execute(
        "SELECT value FROM config WHERE key = 'end_timestamp'"
    ).fetchone()
    conn.close()
    if row:
        dt = datetime.fromisoformat(row[0])
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def set_time_window(start_utc: datetime, end_utc: datetime):
    conn = _db()
    conn.executemany(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        [
            ("start_timestamp", start_utc.isoformat()),
            ("end_timestamp", end_utc.isoformat()),
        ],
    )
    conn.commit()
    conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_ts(ts, tz: ZoneInfo) -> str:
    if ts is None:
        return "—"
    if isinstance(ts, datetime):
        aware = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
        return aware.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)


def tz_display_label(tz: ZoneInfo, ref_dt: datetime) -> str:
    abbrev = ref_dt.astimezone(tz).tzname() or "UTC"
    offset = ref_dt.astimezone(tz).strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else offset
    if abbrev == "UTC":
        return "UTC"
    return f"{abbrev} (UTC{offset})"


def _utc_offset_label(tz: ZoneInfo, ref_dt: datetime) -> str:
    offset = ref_dt.astimezone(tz).strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else offset
    return f"UTC{offset}"


def tz_dropdown_label(tz: ZoneInfo) -> str:
    if tz.key == "UTC":
        return "UTC"

    jan_ref = datetime(2026, 1, 15, tzinfo=timezone.utc)
    jul_ref = datetime(2026, 7, 15, tzinfo=timezone.utc)

    jan_abbr = jan_ref.astimezone(tz).tzname() or "TZ"
    jul_abbr = jul_ref.astimezone(tz).tzname() or "TZ"
    jan_utc = _utc_offset_label(tz, jan_ref)
    jul_utc = _utc_offset_label(tz, jul_ref)

    if jan_abbr == jul_abbr and jan_utc == jul_utc:
        return f"{jan_abbr} ({jan_utc})"
    return f"{jan_abbr}/{jul_abbr} ({jan_utc}/{jul_utc})"


def tz_display_label_for_range(tz: ZoneInfo, start_dt: datetime, end_dt: datetime) -> str:
    start_label = tz_display_label(tz, start_dt)
    end_label = tz_display_label(tz, end_dt)
    if start_label == end_label:
        return start_label
    return f"{start_label} → {end_label}"


def build_display_df(rows: list[dict]) -> pd.DataFrame:
    records = []
    for r in rows:
        record = dict(r)
        if "time_stamp" in record:
            record["time_stamp"] = fmt_ts(record.get("time_stamp"), selected_tz)
        if "Alert Time Stamp" in record:
            record["Alert Time Stamp"] = fmt_ts(record.get("Alert Time Stamp"), selected_tz)
        if "Alert Created on Cloud" in record:
            record["Alert Created on Cloud"] = fmt_ts(record.get("Alert Created on Cloud"), selected_tz)
        if "Action taken On" in record:
            record["Action taken On"] = fmt_ts(record.get("Action taken On"), selected_tz)
        if "created_on" in record:
            record["created_on"] = fmt_ts(record.get("created_on"), selected_tz)
        if "Created On" in record:
            record["Created On"] = fmt_ts(record.get("Created On"), selected_tz)
        records.append(record)
    df = pd.DataFrame(records)
    if "Driver ID" in df.columns:
        df["Driver ID"] = pd.to_numeric(df["Driver ID"], errors="coerce").astype("Int64")
    return df


# ── Init ──────────────────────────────────────────────────────────────────────

_ensure_tables()

# Debug: Track if we are hitting the DB
if "db_fetch_count" not in st.session_state:
    st.session_state["db_fetch_count"] = 0

# ── Sidebar ───────────────────────────────────────────────────────────────────

# ── Chart + table renderers ───────────────────────────────────────────────────

SLA_COLOR_SCALE = alt.Scale(
    domain=["Compliant", "Breached", "No Action Taken"],
    range=["#16a34a", "#a855f7", "#dc2626"],
)


def render_pie(rows: list[dict], field: str, color_scale=None):
    vals = [(r.get(field) if r.get(field) not in (None, "") else "None") for r in rows]
    src = pd.DataFrame({field: vals})
    agg = src.groupby(field).size().reset_index(name="count")
    if agg.empty:
        st.info("No data.")
        return
    if color_scale is not None:
        color = alt.Color(f"{field}:N", scale=color_scale, legend=alt.Legend(orient="bottom", title=None))
    else:
        color = alt.Color(f"{field}:N", legend=alt.Legend(orient="bottom", title=None))
    chart = (
        alt.Chart(agg)
        .mark_arc(innerRadius=55)
        .encode(theta="count:Q", color=color, tooltip=[field, "count"])
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)


def apply_volume_granularity(df: pd.DataFrame, granularity: str) -> tuple[str, str, str]:
    if granularity == "Hourly":
        df["bucket"] = df["ts"].dt.floor("h")
        return "Time", "%Y-%m-%d %H:%M", "hour"
    if granularity == "Weekly":
        df["bucket"] = df["ts"].dt.tz_localize(None).dt.to_period("W-SUN").dt.to_timestamp()
        return "Week", "%Y-%m-%d", "week"
    df["bucket"] = df["ts"].dt.floor("D")
    return "Date", "%Y-%m-%d", "day"


def render_volume_chart(rows: list[dict], tz: ZoneInfo, granularity: str):
    data = [
        {"ts": r.get("Alert Time Stamp")}
        for r in rows
        if r.get("Alert Time Stamp") is not None
    ]
    if not data:
        st.info("No data.")
        return
    df = pd.DataFrame(data)
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(str(tz))
    axis_title, time_format, tick_unit = apply_volume_granularity(df, granularity)
    agg = df.groupby("bucket").size().reset_index(name="Alerts")
    chart = (
        alt.Chart(agg)
        .mark_area(opacity=0.35, line=True, point=True)
        .encode(
            x=alt.X(
                "bucket:T", 
                title=axis_title, 
                axis=alt.Axis(
                    format=time_format, 
                    labelAngle=-45, 
                    labelBound=True, 
                    labelOverlap="parity",
                    tickCount=tick_unit
                )
            ),
            y=alt.Y("Alerts:Q", title="Alert count"),
            tooltip=[alt.Tooltip("bucket:T", title=axis_title, format=time_format), "Alerts:Q"],
        )
        .properties(height=340)
    )
    st.altair_chart(chart, use_container_width=True)


def render_volume_by_sla_chart(rows: list[dict], tz: ZoneInfo, granularity: str):
    data = [
        {
            "ts": r.get("Alert Time Stamp"),
            "SLA Compliance": r.get("SLA Compliance") or "No Action Taken",
        }
        for r in rows
        if r.get("Alert Time Stamp") is not None
    ]
    if not data:
        st.info("No data.")
        return
    df = pd.DataFrame(data)
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(str(tz))
    axis_title, time_format, tick_unit = apply_volume_granularity(df, granularity)
    agg = (
        df.groupby(["bucket", "SLA Compliance"]).size().reset_index(name="Alerts")
    )
    chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X(
                "bucket:T", 
                title=axis_title, 
                axis=alt.Axis(
                    format=time_format, 
                    labelAngle=-45, 
                    labelBound=True, 
                    labelOverlap="parity",
                    tickCount=tick_unit
                )
            ),
            xOffset="SLA Compliance:N",
            y=alt.Y("Alerts:Q", title="Alert count"),
            color=alt.Color(
                "SLA Compliance:N",
                scale=SLA_COLOR_SCALE,
                legend=alt.Legend(orient="bottom", title=None),
            ),
            tooltip=[
                alt.Tooltip("bucket:T", title=axis_title, format=time_format),
                "SLA Compliance:N",
                "Alerts:Q",
            ],
        )
        .properties(height=420, width=800)
    )
    st.altair_chart(chart, use_container_width=True)


def render_home(rows: list[dict], tz: ZoneInfo, granularity: str):
    if not rows:
        st.info("No alerts match the current filters.")
        return
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("**SLA Compliance**")
        render_pie(rows, "SLA Compliance", SLA_COLOR_SCALE)
    with p2:
        st.markdown("**Alerts by Fleet**")
        render_pie(rows, "Tenant Name")
    with p3:
        st.markdown("**Action Type**")
        render_pie(rows, "Action Type")
    st.subheader("Alert Volume Over Time")
    render_volume_chart(rows, tz, granularity)
    st.subheader("Alert Volume by SLA Status")
    render_volume_by_sla_chart(rows, tz, granularity)


def render_table(rows: list[dict], key: str = "data"):
    if not rows:
        st.info("No alerts match the current filters.")
        return
    display_df = build_display_df(rows)
    tz_short = tz_display_label(selected_tz, datetime.now(selected_tz))
    rename_map = {}
    if "Alert Time Stamp" in display_df.columns:
        rename_map["Alert Time Stamp"] = f"Alert Time Stamp ({tz_short})"
    if "Alert Created on Cloud" in display_df.columns:
        rename_map["Alert Created on Cloud"] = f"Alert Created on Cloud ({tz_short})"
    if "Action taken On" in display_df.columns:
        rename_map["Action taken On"] = f"Action taken On ({tz_short})"
    if rename_map:
        display_df = display_df.rename(columns=rename_map)

    search = st.text_input(
        "Search", key=f"search_{key}", placeholder="Search all columns..."
    )
    if search:
        mask = display_df.apply(
            lambda r: r.astype(str).str.contains(search, case=False, na=False).any(),
            axis=1,
        )
        display_df = display_df[mask]

    def _sla_style(val):
        if val == "Compliant":
            return "color: #16a34a; font-weight: bold;"
        if val == "Breached":
            return "color: #a855f7; font-weight: bold;"
        if val == "No Action Taken":
            return "color: #dc2626; font-weight: bold;"
        return ""

    sla_col = "SLA Compliance"
    table_data = display_df
    if sla_col in display_df.columns:
        table_data = display_df.style.map(_sla_style, subset=[sla_col])

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        display_df.to_excel(writer, index=False, sheet_name="Alerts")
    range_start = stored_start.astimezone(selected_tz).strftime("%Y%m%d")
    range_end = stored_end.astimezone(selected_tz).strftime("%Y%m%d")
    range_str = range_start if range_start == range_end else f"{range_start}-{range_end}"
    st.download_button(
        label="Download as Excel (.xlsx)",
        data=buffer.getvalue(),
        file_name=f"dms_drowsy_report_{range_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_xlsx_{key}",
    )
    st.caption(f"{len(display_df)} alert(s) shown")


# ── Sidebar: page navigation ──────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <div class="dms-nav-brand">
            <div>
                <div class="dms-nav-title">DMS Drowsy Report</div>
                <div class="dms-nav-sub">Monitoring fleets: Amazon AFP (tenant 20220) · ABC Supply (tenant 7960)</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

# ── Layout: content + left filters ───────────────────────────────────────────

content_col = st.container()
filters_container = st.sidebar

# Time-window + timezone filters (needed before fetching data).
with filters_container:
    st.subheader("Filters")

    tz_values = list(TIMEZONE_OPTIONS.values())
    tz_label_to_value = {tz_dropdown_label(ZoneInfo(v)): v for v in tz_values}
    tz_labels = list(tz_label_to_value.keys())
    default_index = 1 if len(tz_labels) > 1 else 0
    tz_label = st.selectbox("Display timezone", tz_labels, index=default_index, key="tz_label")
    selected_tz = ZoneInfo(tz_label_to_value[tz_label])

    now_local = datetime.now(selected_tz)
    range_label = st.selectbox(
        "Date range",
        [
            "Last 1 Hour",
            "Last 6 Hours",
            "Last 12 Hours",
            "Last 24 Hours",
            "Today",
            "Yesterday",
            "This Week",
            "Last Week",
            "Last 7 Days",
            "This Month",
            "Last Month",
            "Last 30 Days",
            "Custom Date",
        ],
        index=3, # "Last 24 Hours"
        key="range_label",
    )

    local_start = now_local - timedelta(days=7)
    local_end = now_local

    if range_label == "Last 1 Hour":
        local_start = now_local - timedelta(hours=1)
    elif range_label == "Last 6 Hours":
        local_start = now_local - timedelta(hours=6)
    elif range_label == "Last 12 Hours":
        local_start = now_local - timedelta(hours=12)
    elif range_label == "Last 24 Hours":
        local_start = now_local - timedelta(hours=24)
    elif range_label == "Today":
        local_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_label == "Yesterday":
        yesterday = now_local.date() - timedelta(days=1)
        local_start = datetime.combine(yesterday, dt_time(0, 0), tzinfo=selected_tz)
        local_end = datetime.combine(yesterday, dt_time(23, 59, 59), tzinfo=selected_tz)
    elif range_label == "This Week":
        week_start = now_local.date() - timedelta(days=now_local.weekday())
        local_start = datetime.combine(week_start, dt_time(0, 0), tzinfo=selected_tz)
    elif range_label == "Last Week":
        this_week_start = now_local.date() - timedelta(days=now_local.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)
        local_start = datetime.combine(last_week_start, dt_time(0, 0), tzinfo=selected_tz)
        local_end = datetime.combine(last_week_end, dt_time(23, 59, 59), tzinfo=selected_tz)
    elif range_label == "Last 7 Days":
        local_start = now_local - timedelta(days=7)
    elif range_label == "This Month":
        local_start = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif range_label == "Last Month":
        this_month_start = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = this_month_start - timedelta(seconds=1)
        local_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        local_end = last_month_end
    elif range_label == "Last 30 Days":
        local_start = now_local - timedelta(days=30)
    elif range_label == "Custom Date":
        manual_input = st.toggle("Type date/time manually", value=False, key="custom_manual_mode")

        if manual_input:
            st.caption("Format: YYYY-MM-DD HH:MM")
            default_start_str = (now_local - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
            default_end_str = now_local.strftime("%Y-%m-%d %H:%M")
            start_raw = st.text_input("Start", value=default_start_str, key="custom_start_text")
            end_raw = st.text_input("End", value=default_end_str, key="custom_end_text")

            try:
                start_naive = datetime.strptime(start_raw.strip(), "%Y-%m-%d %H:%M")
                end_naive = datetime.strptime(end_raw.strip(), "%Y-%m-%d %H:%M")
                local_start = start_naive.replace(tzinfo=selected_tz)
                local_end = end_naive.replace(tzinfo=selected_tz)
            except ValueError:
                st.error("Invalid format. Use YYYY-MM-DD HH:MM")
                local_start = now_local - timedelta(hours=24)
                local_end = now_local
        else:
            # Streamlit's date_input supports range selection with a tuple.
            dates = st.date_input(
                "Select Date Range",
                value=(now_local.date() - timedelta(days=1), now_local.date()),
                max_value=now_local.date(),
                key="custom_date_range",
            )

            # Handle the case where user has only clicked the first date.
            if isinstance(dates, (list, tuple)) and len(dates) == 2:
                start_date, end_date = dates
            else:
                start_date = dates[0] if (isinstance(dates, (list, tuple)) and len(dates) > 0) else now_local.date()
                end_date = start_date

            t1, t2 = st.columns(2)
            with t1:
                start_time = st.time_input("Start Time", value=dt_time(0, 0), key="start_time")
            with t2:
                end_time = st.time_input(
                    "End Time", value=dt_time(now_local.hour, now_local.minute), key="end_time"
                )

            local_start = datetime.combine(start_date, start_time, tzinfo=selected_tz)
            local_end = datetime.combine(end_date, end_time, tzinfo=selected_tz)

    st.caption(
        f"Selected: {local_start.strftime('%Y-%m-%d %H:%M')} to "
        f"{local_end.strftime('%Y-%m-%d %H:%M')} {tz_display_label_for_range(selected_tz, local_start, local_end)}"
    )

    if range_label == "Custom Date":
        # Custom range: wait for the user to confirm with Apply.
        if st.button("Apply time window", use_container_width=True, key="apply_window"):
            if local_end < local_start:
                st.error("End time must be after start time.")
            elif (local_end - local_start).days > 31:
                st.error("Custom Date range cannot exceed 31 days.")
            else:
                set_time_window(local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc))
                st.success("Time window applied.")
                st.rerun()
    else:
        # Quick ranges apply immediately on selection (no Apply button).
        if local_end >= local_start:
            set_time_window(local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc))

    stored_start = get_stored_start_ts()
    stored_end = get_stored_end_ts()
    if stored_start and stored_end:
        stored_start_local = stored_start.astimezone(selected_tz)
        stored_end_local = stored_end.astimezone(selected_tz)
        st.info(
            f"**Showing alerts window**\n\n"
            f"{stored_start_local.strftime('%Y-%m-%d %H:%M')} to "
            f"{stored_end_local.strftime('%Y-%m-%d %H:%M')} {tz_display_label_for_range(selected_tz, stored_start_local, stored_end_local)}"
        )
    else:
        st.warning("No time window set yet.")

if stored_start is None or stored_end is None:
    with content_col:
        st.info("Set a start and end time in the left Filters panel to begin monitoring.")
    st.stop()

window_key_str = f"{stored_start.isoformat()}_{stored_end.isoformat()}"
if st.session_state.get("alerts_window_key") != window_key_str:
    # Always clear UI-only filters when the time window changes
    # to maintain consistency with the new dataset.
    for k in ["fleet_filter", "sla_filter", "type_filter"]:
        if k in st.session_state:
            del st.session_state[k]

    # 1. Check local persistent cache
    cached = get_cached_alerts(window_key_str)
    if cached is not None:
        st.session_state["alerts_for_window"] = cached
        st.session_state["alerts_window_key"] = window_key_str
    else:
        # 2. Fetch from database
        try:
            st.session_state["db_fetch_count"] += 1
            rows = fetch_alerts(stored_start, stored_end)
            # Store in local cache
            set_cached_alerts(window_key_str, rows)

            st.session_state["alerts_for_window"] = rows
            st.session_state["alerts_window_key"] = window_key_str
        except Exception as exc:
            with content_col:
                st.error(f"Database error: {exc}")
            st.stop()

alerts = st.session_state.get("alerts_for_window", [])

# Data-driven filters (shared across Home and Data pages)
with filters_container:
    st.divider()

    fleet_options = sorted({a.get("Tenant Name") for a in alerts if a.get("Tenant Name")})
    selected_fleets = st.multiselect(
        "Fleet", fleet_options, default=st.session_state.get("fleet_filter", fleet_options), key="fleet_filter"
    )

    sla_options = sorted({a.get("SLA Compliance") for a in alerts if a.get("SLA Compliance")})
    selected_sla = st.multiselect(
        "SLA Compliance", sla_options, default=st.session_state.get("sla_filter", sla_options), key="sla_filter"
    )

    type_options = sorted({a.get("Action Type") for a in alerts if a.get("Action Type")})
    selected_types = st.multiselect(
        "Action Type", type_options, default=st.session_state.get("type_filter", type_options), key="type_filter"
    )

    granularity = st.selectbox(
        "Volume granularity", ["Hourly", "Daily", "Weekly"], key="granularity"
    )

    st.divider()
    auto_refresh_value = st.toggle(
        "Auto refresh",
        value=st.session_state["auto_refresh_enabled"],
        key="auto_refresh_toggle",
    )
    if auto_refresh_value != st.session_state["auto_refresh_enabled"]:
        st.session_state["auto_refresh_enabled"] = auto_refresh_value
        st.rerun()

# Apply the shared filters to the alert list
filtered = []
for a in alerts:
    if a.get("Tenant Name") not in selected_fleets:
        continue
    if a.get("SLA Compliance") not in selected_sla:
        continue
    at = a.get("Action Type")
    if at is not None and at not in selected_types:
        continue
    filtered.append(a)

with content_col:
    amazon_alerts = [a for a in filtered if str(a.get("Tenant ID")) == "20220"]
    abc_alerts = [a for a in filtered if str(a.get("Tenant ID")) == "7960"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Alerts", len(filtered))
    m2.metric("Amazon AFP", len(amazon_alerts))
    m3.metric("ABC Supply", len(abc_alerts))
    st.divider()

    if not alerts:
        st.success("No drowsy alerts found in the selected time window.")
    else:
        # Render charts first
        render_home(filtered, selected_tz, granularity)
        st.divider()
        # Render data table below
        st.subheader("Alert Details")
        render_table(filtered, key="data")
