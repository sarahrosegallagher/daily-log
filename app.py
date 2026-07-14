import hmac
import os
import sqlite3
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for, flash, Response

load_dotenv()  # reads .env if present; no-op if it doesn't exist (e.g. on PythonAnywhere)

try:
    import config  # private, gitignored — real site copy
except ImportError:
    import config_example as config  # public fallback for a fresh checkout

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

# --- Config -----------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "daily_log.db")

PAGE_TITLE = config.PAGE_TITLE
PAGE_SUBTITLE = config.PAGE_SUBTITLE
ENTRY_PLACEHOLDER = config.ENTRY_PLACEHOLDER
VIBE_OPTIONS = config.VIBE_OPTIONS
HYDRATION_OPTIONS = config.HYDRATION_OPTIONS

# Basic auth credentials - set these as environment variables on the host,
# don't hardcode real values here.
AUTH_USER = os.environ.get("FORM_USER", "admin")
AUTH_PASS = os.environ.get("FORM_PASS", "changeme")


# --- Auth ---------------------------------------------------------------
def check_auth(username, password):
    return hmac.compare_digest(username, AUTH_USER) and hmac.compare_digest(password, AUTH_PASS)


def authenticate():
    return Response(
        "Login required.", 401,
        {"WWW-Authenticate": 'Basic realm="Daily Log"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# --- Storage --------------------------------------------------------------
def ensure_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                entry TEXT,
                vibes TEXT,
                hydration TEXT,
                submitted_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_meds (
                date TEXT PRIMARY KEY,
                adderall_taken INTEGER DEFAULT 0,
                adderall_time TEXT,
                nighttime_meds_taken INTEGER DEFAULT 0
            )
        """)


def append_entry(date_val, time_val, entry_val, vibes_val, hydration_val):
    ensure_db()
    now = datetime.now()
    # Fallback rule: if no time given, use the current server time.
    # (Matches the "if no time entered use timestamp field" logic
    # you'll otherwise have to do in the Python cleanup step.)
    if not time_val:
        time_val = now.strftime("%H:%M")
    if not date_val:
        date_val = now.strftime("%Y-%m-%d")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO entries (date, time, entry, vibes, hydration, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                date_val,
                time_val,
                entry_val.strip() or None,
                vibes_val,
                hydration_val,
                now.isoformat(timespec="seconds"),
            ),
        )


# --- Routes -----------------------------------------------------------
@app.route("/", methods=["GET"])
@requires_auth
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")
    return render_template(
        "index.html",
        today=today,
        now_time=now_time,
        vibe_options=VIBE_OPTIONS,
        hydration_options=HYDRATION_OPTIONS,
        page_title=PAGE_TITLE,
        page_subtitle=PAGE_SUBTITLE,
        entry_placeholder=ENTRY_PLACEHOLDER,
    )


@app.route("/submit", methods=["POST"])
@requires_auth
def submit():
    date_val = request.form.get("date", "").strip()
    time_val = request.form.get("time", "").strip()
    entry_val = request.form.get("entry", "").strip()
    vibes_val = request.form.get("vibes", "").strip()
    hydration_val = request.form.get("hydration", "").strip()

    if vibes_val and vibes_val not in VIBE_OPTIONS:
        flash("Invalid mood selection.")
        return redirect(url_for("index"))

    if hydration_val and hydration_val not in HYDRATION_OPTIONS:
        flash("Invalid hydration selection.")
        return redirect(url_for("index"))

    append_entry(date_val, time_val, entry_val, vibes_val, hydration_val)
    flash("Logged.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    ensure_db()
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)
