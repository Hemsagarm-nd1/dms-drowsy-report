import psycopg2
import psycopg2.extras
import decimal
import csv
from pathlib import Path
from datetime import datetime
from config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    RO_DB_HOST, RO_DB_PORT, RO_DB_NAME, RO_DB_USER, RO_DB_PASSWORD,
    EVENT_CODES, TENANT_IDS,
)


_USER_NAME_MAP: dict[str, str] | None = None


def _load_user_name_map() -> dict[str, str]:
    """Load user_id -> user_name mapping from user_id.csv."""
    global _USER_NAME_MAP
    if _USER_NAME_MAP is not None:
        return _USER_NAME_MAP

    csv_path = Path(__file__).with_name("user_id.csv")
    mapping: dict[str, str] = {}
    if csv_path.exists():
        with csv_path.open("r", newline="", encoding="utf-8-sig") as fh:
            header = fh.readline()
            delimiter = "\t" if "\t" in header and "," not in header else ","
            fh.seek(0)
            reader = csv.DictReader(fh, delimiter=delimiter)
            for row in reader:
                raw_id = (row.get("user_id") or "").strip()
                raw_name = (row.get("user_name") or "").strip()
                if raw_id and raw_name:
                    mapping[raw_id] = raw_name

    _USER_NAME_MAP = mapping
    return mapping


def _clean(row: dict) -> dict:
    """Convert decimal.Decimal → int/float so SQLite and JSON serialisation work."""
    out = {}
    for k, v in row.items():
        if isinstance(v, decimal.Decimal):
            out[k] = int(v) if v == v.to_integral_value() else float(v)
        else:
            out[k] = v
    return out


def get_connection():
    """Open and return a new PostgreSQL connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10,
    )


def get_ro_connection():
    """Open and return a new read-only PostgreSQL connection (NDALERTS lookup)."""
    return psycopg2.connect(
        host=RO_DB_HOST,
        port=RO_DB_PORT,
        dbname=RO_DB_NAME,
        user=RO_DB_USER,
        password=RO_DB_PASSWORD,
        connect_timeout=10,
    )


def fetch_action_logs(alert_ids: list) -> dict:
    """
    For the given alert_ids, look up management-action details from
    ndlivemanagementlogs on the primary DB.

        A single alert can have multiple log entries (one per comment). For each
        alert_id we return:
            - the latest comment / action type / user (most recent created_on)
            - "Initial Action taken On" = the earliest created_on for that alert_id

    Returns a mapping of alert_id (as str) -> dict of those fields.
    """
    ids = []
    for a in alert_ids:
        if a is None:
            continue
        try:
            ids.append(int(a))
        except (TypeError, ValueError):
            continue
    ids = list(set(ids))
    if not ids:
        return {}

    sql = """
        WITH logs AS (
            SELECT
                alert_id,
                action_type,
                comment,
                user_id,
                created_on,
                ROW_NUMBER() OVER (
                    PARTITION BY alert_id ORDER BY created_on DESC
                ) AS rn_latest,
                MIN(created_on) OVER (PARTITION BY alert_id) AS first_action_on
            FROM ndlivemanagementlogs
            WHERE alert_id = ANY(%s)
            AND action_type IN (2, 5, 6, 7)
        )
        SELECT
            alert_id,
            CASE action_type
                WHEN 1 THEN 'View only'
                WHEN 2 THEN 'Comment only'
                WHEN 3 THEN 'Added to watchlist'
                WHEN 4 THEN 'Removed from watchlist'
                WHEN 5 THEN 'No action needed'
                WHEN 6 THEN 'Contact successful'
                WHEN 7 THEN 'Contact unsuccessful'
                ELSE CAST(action_type AS TEXT)
            END AS action_type_label,
            comment,
            user_id,
            first_action_on
        FROM logs
        WHERE rn_latest = 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (ids,))
            user_name_map = _load_user_name_map()
            out = {}
            for alert_id, action_type_label, comment, user_id, first_action_on in cur.fetchall():
                user_id_str = str(user_id) if user_id is not None else ""
                user_name = user_name_map.get(user_id_str)
                out[str(alert_id)] = {
                    "Action Type": action_type_label,
                    "Comment": comment,
                    "User Name": user_name or None,
                    "Initial Action taken On": first_action_on,
                }
            return out
    finally:
        conn.close()


def fetch_alerts(start_utc: datetime, end_utc: datetime) -> list[dict]:
    """
    Fetch drowsy alerts within a UTC time window.

    The base list of alerts comes from NDALERTS (read-only DB), because
    ndlivemanagementlogs only has rows when a comment/action was recorded.
    Each alert is then enriched with the management-action details (comment,
    user, action type and the time the action was taken) from
    ndlivemanagementlogs on the primary DB.

    start_utc and end_utc must be timezone-aware datetimes in UTC.
    """
    # Ensure we hand UTC-naive timestamp to Postgres (it stores without tz)
    start_naive = start_utc.replace(tzinfo=None) if start_utc.tzinfo else start_utc
    end_naive = end_utc.replace(tzinfo=None) if end_utc.tzinfo else end_utc

    tenant_ids_str = [str(t) for t in TENANT_IDS]

    sql = """
        SELECT
            alert_id AS "Alert ID",
            tenant_id AS "Tenant ID",
            CASE
                WHEN tenant_id::text = '20220' THEN 'AFP 2024'
                WHEN tenant_id::text = '7960'  THEN 'ABC'
                ELSE 'Others'
            END AS "Tenant Name",
            driver_id AS "Driver ID",
            vehicle_id AS "Vehicle ID",
            time_stamp AS "Alert Time Stamp",
            created_on AS "Alert Created on Cloud"
        FROM ndalerts
        WHERE tenant_id::text = ANY(%s)
          AND alert_type = 16
          AND alert_severity = 1
          AND alert_confirmation_status = 1
          AND event_code = ANY(%s)
          AND time_stamp BETWEEN %s AND %s
        ORDER BY time_stamp DESC
    """

    conn = get_ro_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (tenant_ids_str, EVENT_CODES, start_naive, end_naive))
            rows = cur.fetchall()
            # Convert RealDictRow → plain dict so callers can freely mutate
            results = [_clean(dict(row)) for row in rows]
    finally:
        conn.close()

    # Enrich with management-action details from ndlivemanagementlogs and
    # compute "Action taken in Minutes" and the "SLA Compliance" verdict.
    logs_by_alert = fetch_action_logs([r.get("Alert ID") for r in results])
    for row in results:
        log = logs_by_alert.get(str(row.get("Alert ID")))
        row["Action Type"] = log["Action Type"] if log else None
        row["Latest Comment"] = log["Comment"] if log else None
        row["User Name"] = log["User Name"] if log else None
        row["Initial Action taken On"] = log["Initial Action taken On"] if log else None

        alert_created = row.get("Alert Created on Cloud")
        action_on = row.get("Initial Action taken On")
        comment = row.get("Latest Comment")

        if action_on is not None and alert_created is not None:
            minutes = int((action_on - alert_created).total_seconds() / 60)
        else:
            minutes = None
        row["Action taken in Minutes"] = minutes

        if log is None or comment is None or str(comment).strip() == "":
            row["SLA Compliance"] = "No Action Taken"
        elif minutes is not None and minutes <= 5:
            row["SLA Compliance"] = "Compliant"
        else:
            row["SLA Compliance"] = "Breached"

    return results
