import hmac
import os
import sqlite3
from collections import Counter
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
SYMPTOM_OPTIONS = config.SYMPTOM_OPTIONS
MED_AM_LABEL = config.MED_AM_LABEL
MED_PM_LABEL = config.MED_PM_LABEL

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
        try:
            conn.execute("ALTER TABLE entries ADD COLUMN symptom TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists


ensure_db()  # run at import time so DB/tables exist regardless of how the app is started


def get_entry_suggestions():
    """Past entry values for the datalist: deduped case-insensitively,
    most-frequently-used casing wins, sorted most- to least-used."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT entry FROM entries WHERE entry IS NOT NULL AND entry != ''"
        ).fetchall()

    casing_counts = {}  # lowercased entry -> Counter of original casings
    for (entry_val,) in rows:
        key = entry_val.lower()
        casing_counts.setdefault(key, Counter())[entry_val] += 1

    def total_uses(counter):
        return sum(counter.values())

    ranked = sorted(casing_counts.values(), key=total_uses, reverse=True)
    return [counter.most_common(1)[0][0] for counter in ranked]


def split_entry_text(entry_val):
    """Split a comma-separated entry ('latte, grilled cheese') into individual
    items. Empty/whitespace-only pieces are dropped. Returns [None] for blank
    input, matching the existing "entry is optional" behavior."""
    if not entry_val or not entry_val.strip():
        return [None]
    pieces = [piece.strip() for piece in entry_val.split(",")]
    pieces = [piece for piece in pieces if piece]
    return pieces or [None]


def append_entry(date_val, time_val, entry_val, vibes_val, hydration_val, symptom_val):
    ensure_db()
    now = datetime.now()
    # Fallback rule: if no time given, use the current server time.
    # (Matches the "if no time entered use timestamp field" logic
    # you'll otherwise have to do in the Python cleanup step.)
    if not time_val:
        time_val = now.strftime("%H:%M")
    if not date_val:
        date_val = now.strftime("%Y-%m-%d")

    submitted_at = now.isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH) as conn:
        for entry_piece in split_entry_text(entry_val):
            conn.execute(
                """
                INSERT INTO entries (date, time, entry, vibes, hydration, symptom, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date_val,
                    time_val,
                    entry_piece,
                    vibes_val or None,
                    hydration_val or None,
                    symptom_val or None,
                    submitted_at,
                ),
            )


def get_today_meds(date_str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT adderall_taken, adderall_time, nighttime_meds_taken "
            "FROM daily_meds WHERE date = ?",
            (date_str,),
        ).fetchone()
    if row is None:
        return {"adderall_taken": False, "adderall_time": "", "nighttime_meds_taken": False}
    adderall_taken, adderall_time, nighttime_meds_taken = row
    return {
        "adderall_taken": bool(adderall_taken),
        "adderall_time": adderall_time or "",
        "nighttime_meds_taken": bool(nighttime_meds_taken),
    }


def upsert_meds(date_str, adderall_taken, adderall_time, nighttime_meds_taken):
    ensure_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO daily_meds (date, adderall_taken, adderall_time, nighttime_meds_taken)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                adderall_taken = excluded.adderall_taken,
                adderall_time = excluded.adderall_time,
                nighttime_meds_taken = excluded.nighttime_meds_taken
            """,
            (date_str, int(adderall_taken), adderall_time, int(nighttime_meds_taken)),
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
        symptom_options=SYMPTOM_OPTIONS,
        entry_suggestions=get_entry_suggestions(),
        page_title=PAGE_TITLE,
        page_subtitle=PAGE_SUBTITLE,
        entry_placeholder=ENTRY_PLACEHOLDER,
        med_am_label=MED_AM_LABEL,
        med_pm_label=MED_PM_LABEL,
        meds=get_today_meds(today),
    )


@app.route("/submit", methods=["POST"])
@requires_auth
def submit():
    date_val = request.form.get("date", "").strip()
    time_val = request.form.get("time", "").strip()
    entry_val = request.form.get("entry", "").strip()
    vibes_val = request.form.get("vibes", "").strip()
    hydration_val = request.form.get("hydration", "").strip()
    symptom_val = request.form.get("symptom", "").strip()

    if vibes_val and vibes_val not in VIBE_OPTIONS:
        flash("Invalid mood selection.")
        return redirect(url_for("index"))

    if hydration_val and hydration_val not in HYDRATION_OPTIONS:
        flash("Invalid hydration selection.")
        return redirect(url_for("index"))

    if symptom_val and symptom_val not in SYMPTOM_OPTIONS:
        flash("Invalid symptom selection.")
        return redirect(url_for("index"))

    append_entry(date_val, time_val, entry_val, vibes_val, hydration_val, symptom_val)
    flash("Logged.")
    return redirect(url_for("index"))


@app.route("/meds", methods=["POST"])
@requires_auth
def meds():
    date_val = request.form.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
    adderall_taken = "adderall_taken" in request.form
    adderall_time = request.form.get("adderall_time", "").strip() if adderall_taken else ""
    nighttime_meds_taken = "nighttime_meds_taken" in request.form

    upsert_meds(date_val, adderall_taken, adderall_time, nighttime_meds_taken)
    flash("Meds updated.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    ensure_db()
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)
