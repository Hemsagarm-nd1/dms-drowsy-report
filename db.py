import psycopg2
import psycopg2.extras
import decimal
from datetime import datetime
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


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
            tenant_id AS "Tenant ID",
            driver_id AS "Driver ID",
            vehicle_id AS "Vehicle ID",
            action_type AS "Action Type",
            comment AS "Comment",
            alert_id AS "Alert ID",
            user_id AS "User ID",
            alert_time_stamp AS "Alert Time Stamp",
            created_on AS "Created On",
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
            return [_clean(dict(row)) for row in rows]
    finally:
        conn.close()
