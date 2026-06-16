import os
from dotenv import load_dotenv

load_dotenv()

# Database
DB_HOST = os.getenv("DB_HOST", "production-postgresql-idms-dashboard.1.netradyne.info")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "beta-prod-idms-db")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Polling
POLL_INTERVAL_SECONDS = 30

# Local SQLite path (shared between notifier and dashboard)
SQLITE_DB_PATH = "notifier_state.db"

# Fleet definitions
TENANT_IDS = [20220, 7960]

FLEET_NAMES = {
    "20220": "Amazon AFP",
    "7960": "ABC Supply",
}

# DMS drowsy event codes
EVENT_CODES = [
    "401.1.5.0.51",
    "401.1.5.0.53",
    "401.1.5.0.0",
    "401.1.5.0.30",
    "401.1.5.0.52",
    "401.1.5.0.54",
]

EVENT_CODE_NAMES = {
    "401.1.5.0.51": "Drowsy Lane Deviation",
    "401.1.5.0.53": "Excessive Blinking",
    "401.1.5.0.0":  "Extended Eye Closure",
    "401.1.5.0.30": "Intermittent Eye Closure",
    "401.1.5.0.52": "Nodding",
    "401.1.5.0.54": "Slow Blinking",
}

# Timezones available in the dashboard
TIMEZONE_OPTIONS = {
    "UTC (UTC+00:00)": "UTC",
    "IST (UTC+5:30)": "Asia/Kolkata",
    "EST/EDT (UTC-5/UTC-4)":   "America/New_York",
    "CST/CDT (UTC-6/UTC-5)":    "America/Chicago",
    "MST/MDT (UTC-7/UTC-6)":   "America/Denver",
    "PST/PDT (UTC-8/UTC-7)":    "America/Los_Angeles",
}
