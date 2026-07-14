import csv
import hmac
import os
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
CSV_PATH = os.path.join(DATA_DIR, "entries.csv")
CSV_HEADERS = ["date", "time", "entry", "vibes", "submitted_at"]

PAGE_TITLE = config.PAGE_TITLE
PAGE_SUBTITLE = config.PAGE_SUBTITLE
ENTRY_PLACEHOLDER = config.ENTRY_PLACEHOLDER
VIBE_OPTIONS = config.VIBE_OPTIONS

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
def ensure_csv():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def append_entry(date_val, time_val, entry_val, vibes_val):
    ensure_csv()
    now = datetime.now()
    # Fallback rule: if no time given, use the current server time.
    # (Matches the "if no time entered use timestamp field" logic
    # you'll otherwise have to do in the Python cleanup step.)
    if not time_val:
        time_val = now.strftime("%H:%M")
    if not date_val:
        date_val = now.strftime("%Y-%m-%d")

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            date_val,
            time_val,
            entry_val.strip(),
            vibes_val,
            now.isoformat(timespec="seconds"),
        ])


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

    if not entry_val:
        flash("Entry text can't be empty.")
        return redirect(url_for("index"))

    if vibes_val and vibes_val not in VIBE_OPTIONS:
        flash("Invalid mood selection.")
        return redirect(url_for("index"))

    append_entry(date_val, time_val, entry_val, vibes_val)
    flash("Logged.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    ensure_csv()
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)
