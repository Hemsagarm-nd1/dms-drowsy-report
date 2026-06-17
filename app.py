from __future__ import annotations

import io
import sqlite3
import time as _time
from datetime import datetime, timedelta, timezone, time as dt_time
from zoneinfo import ZoneInfo

import pandas as pd
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
    page_icon="📄",
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


# ── SQLite helpers (shared with notifier) ─────────────────────────────────────

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
    """)
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
        if "created_on" in record:
            record["created_on"] = fmt_ts(record.get("created_on"), selected_tz)
        if "Created On" in record:
            record["Created On"] = fmt_ts(record.get("Created On"), selected_tz)
        records.append(record)
    return pd.DataFrame(records)


# ── Init ──────────────────────────────────────────────────────────────────────

_ensure_tables()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Configuration")

    # Timezone selector
    tz_values = list(TIMEZONE_OPTIONS.values())
    tz_label_to_value = {tz_dropdown_label(ZoneInfo(v)): v for v in tz_values}
    tz_labels = list(tz_label_to_value.keys())
    default_index = 1 if len(tz_labels) > 1 else 0
    tz_label = st.selectbox("Display timezone", tz_labels, index=default_index)
    selected_tz = ZoneInfo(tz_label_to_value[tz_label])

    st.markdown("**Filter alerts by time window**")
    st.caption("Choose a quick date range or use Custom Date.")

    now_local = datetime.now(selected_tz)
    range_label = st.selectbox(
        "Date range",
        [
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
        index=6,
        key="range_label",
    )

    local_start = now_local - timedelta(days=7)
    local_end = now_local

    if range_label == "Last 12 Hours":
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
        start_date = st.date_input("Start date", value=now_local.date(), key="start_date")
        start_time = st.time_input("Start time", value=dt_time(0, 0), key="start_time", step=60)
        end_date = st.date_input("End date", value=now_local.date(), key="end_date")
        end_time = st.time_input(
            "End time",
            value=dt_time(now_local.hour, now_local.minute),
            key="end_time",
            step=60,
        )
        local_start = datetime.combine(start_date, start_time, tzinfo=selected_tz)
        local_end = datetime.combine(end_date, end_time, tzinfo=selected_tz)

    st.caption(
        f"Selected: {local_start.strftime('%Y-%m-%d %H:%M')} to "
        f"{local_end.strftime('%Y-%m-%d %H:%M')} {tz_display_label_for_range(selected_tz, local_start, local_end)}"
    )

    if st.button("🔍 Apply time window", use_container_width=True):
        if local_end < local_start:
            st.error("End time must be after start time.")
        elif range_label == "Custom Date" and (local_end - local_start).days > 31:
            st.error("Custom Date range cannot exceed 31 days.")
        else:
            set_time_window(local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc))
            st.success("Time window applied.")
            st.rerun()

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

    st.divider()

    # Live countdown to next refresh
    if st.session_state["auto_refresh_enabled"]:
        seconds_remaining = 30
        last_load = datetime.now(selected_tz).strftime('%H:%M:%S')
        components.html(f"""
<p style="font-size:0.78rem; color:#888; margin:0; font-family:sans-serif; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; line-height:1.2;">
    Next refresh in <strong><span id="dms-countdown">{seconds_remaining}s</span></strong>
    &nbsp;·&nbsp; Last load: {last_load}&nbsp;
</p>
<script>
    var remaining = {seconds_remaining};
    var span = document.getElementById('dms-countdown');
    setInterval(function() {{
        remaining--;
        if (remaining < 0) remaining = 0;
        if (span) span.textContent = remaining + 's';
    }}, 1000);
</script>
""", height=22)
    else:
        st.caption("Auto refresh is paused.")

# ── Main content ──────────────────────────────────────────────────────────────

st.markdown(
        """
        <div class="sticky-report-header">
                        <h1 id="dms-drowsy-report">📄 DMS Drowsy Report</h1>
            <p>Monitoring fleets: Amazon AFP (tenant 20220) · ABC Supply (tenant 7960)</p>
        </div>
        """,
        unsafe_allow_html=True,
)

if stored_start is None or stored_end is None:
    st.info("👈 Set a start and end time in the sidebar to begin monitoring.")
    st.stop()

# Fetch alerts
try:
    alerts = fetch_alerts(stored_start, stored_end)
except Exception as exc:
    st.error(f"❌ Database error: {exc}")
    st.stop()

# Summary metrics row
amazon_alerts = [a for a in alerts if str(a.get("tenant_id", a.get("Tenant ID"))) == "20220"]
abc_alerts    = [a for a in alerts if str(a.get("tenant_id", a.get("Tenant ID"))) == "7960"]

col1, col2, col3 = st.columns(3)
col1.metric("Total Alerts", len(alerts))
col2.metric("Amazon AFP",   len(amazon_alerts))
col3.metric("ABC Supply",   len(abc_alerts))

st.divider()

if not alerts:
    st.success("✅ No drowsy alerts found in the selected time window.")
    st.stop()

# Table controls
_, refresh_col = st.columns([0.82, 0.18])
with refresh_col:
    auto_refresh_value = st.toggle(
        "Auto refresh",
        value=st.session_state["auto_refresh_enabled"],
        key="auto_refresh_toggle_tabs",
    )
    if auto_refresh_value != st.session_state["auto_refresh_enabled"]:
        st.session_state["auto_refresh_enabled"] = auto_refresh_value
        st.rerun()

# Fleet tabs
tab_all, tab_amazon, tab_abc = st.tabs(["📋 All Alerts", "🚛 Amazon AFP", "🏗️ ABC Supply"])


def render_table(rows, key: str = "table"):
    if not rows:
        st.info("No alerts for this fleet.")
        return
    display_df = build_display_df(rows)
    tz_short = tz_display_label(selected_tz, datetime.now(selected_tz))
    rename_map = {}
    if "Alert Time Stamp" in display_df.columns:
        rename_map["Alert Time Stamp"] = f"Alert Time Stamp ({tz_short})"
    if "Created On" in display_df.columns:
        rename_map["Created On"] = f"Created On ({tz_short})"
    if "time_stamp" in display_df.columns:
        rename_map["time_stamp"] = f"time_stamp ({tz_short})"
    if "created_on" in display_df.columns:
        rename_map["created_on"] = f"created_on ({tz_short })"
    if rename_map:
        display_df = display_df.rename(columns=rename_map)

    st.dataframe(
        display_df,
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
        label="⬇️ Download as Excel (.xlsx)",
        data=buffer.getvalue(),
        file_name=f"dms_drowsy_report_{key}_{range_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_xlsx_{key}",
    )
    st.caption(f"{len(display_df)} alert(s) shown")


with tab_all:
    render_table(alerts, key="all")

with tab_amazon:
    render_table(amazon_alerts, key="amazon")

with tab_abc:
    render_table(abc_alerts, key="abc")
