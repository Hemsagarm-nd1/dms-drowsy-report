import psycopg2
import psycopg2.extras
import decimal
from datetime import datetime
from config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    RO_DB_HOST, RO_DB_PORT, RO_DB_NAME, RO_DB_USER, RO_DB_PASSWORD,
)


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


def fetch_alert_created_on(alert_ids: list) -> dict:
    """
    Look up alert creation timestamps from NDALERTS on the read-only DB.
    Returns a mapping of alert_id (as str) -> created_on datetime.
    """
    # Use the column's native (numeric) type so the index on alert_id is used.
    # Casting the column to text would force a sequential scan over NDALERTS.
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

    sql = 'SELECT alert_id, created_on FROM ndalerts WHERE alert_id = ANY(%s)'
    conn = get_ro_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (ids,))
            return {str(alert_id): created_on for alert_id, created_on in cur.fetchall()}
    finally:
        conn.close()


def fetch_alerts(start_utc: datetime, end_utc: datetime) -> list[dict]:
    """
    Fetch live management actions within a UTC time window.
    Returns a list of dicts (one per alert row).
    start_utc and end_utc must be timezone-aware datetimes in UTC.
    """
    # Ensure we hand UTC-naive timestamp to Postgres (it stores without tz)
    start_naive = start_utc.replace(tzinfo=None) if start_utc.tzinfo else start_utc
    end_naive = end_utc.replace(tzinfo=None) if end_utc.tzinfo else end_utc

    sql = """
        WITH action_data AS (
            SELECT
                tenant_id,
                driver_id,
                vehicle_id,
                action_type,
                comment,
                alert_id,
                user_id,
                alert_time_stamp,
                created_on,
                EXTRACT(EPOCH FROM (created_on - alert_time_stamp)) / 60 AS action_minutes
            FROM ndlivemanagementlogs
            WHERE alert_severity = 1
              AND action_type IN (2, 5, 6, 7)
                            AND alert_time_stamp BETWEEN %s AND %s
        ),
        ranked_data AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY vehicle_id, alert_id
                       ORDER BY alert_time_stamp ASC, created_on ASC
                   ) AS rn
            FROM action_data
        )
        SELECT
            alert_id AS "Alert ID",
            tenant_id AS "Tenant ID",
            driver_id AS "Driver ID",
            vehicle_id AS "Vehicle ID",
            CASE action_type
                WHEN 1 THEN 'View only'
                WHEN 2 THEN 'Comment only'
                WHEN 3 THEN 'Added to watchlist'
                WHEN 4 THEN 'Removed from watchlist'
                WHEN 5 THEN 'No action needed'
                WHEN 6 THEN 'Contact successful'
                WHEN 7 THEN 'Contact unsuccessful'
                ELSE CAST(action_type AS TEXT)
            END AS "Action Type",
            comment AS "Comment",
            user_id AS "User ID",
            alert_time_stamp AS "Alert Time Stamp",
            CAST(NULL AS TIMESTAMP) AS "Alert Created On",
            created_on AS "Action taken On",
            CAST(action_minutes AS INT) AS "Action taken in Minutes",
            CASE
                WHEN action_minutes <= 5 THEN 'PASSED'
                ELSE 'FAILED'
            END AS "Action SLA Status"
        FROM ranked_data
        WHERE rn = 1
        ORDER BY alert_time_stamp DESC
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (start_naive, end_naive))
            rows = cur.fetchall()
            # Convert RealDictRow → plain dict so callers can freely mutate
            results = [_clean(dict(row)) for row in rows]
    finally:
        conn.close()

    # Enrich with NDALERTS.created_on from the read-only DB and recompute
    # "Action taken in Minutes" = Action taken On - Alert Created On.
    created_on_by_alert = fetch_alert_created_on([r.get("Alert ID") for r in results])
    for row in results:
        alert_created = created_on_by_alert.get(str(row.get("Alert ID")))
        row["Alert Created On"] = alert_created
        action_on = row.get("Action taken On")
        if alert_created is not None and action_on is not None:
            minutes = int((action_on - alert_created).total_seconds() / 60)
            row["Action taken in Minutes"] = minutes
            row["Action SLA Status"] = "PASSED" if minutes <= 5 else "FAILED"

    return results
