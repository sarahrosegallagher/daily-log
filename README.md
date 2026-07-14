# Daily Log

A tiny, private Flask form for logging a daily entry (date, time, short text,
vibes) straight to a CSV file.

## What's here

```
daily-log/
├── app.py               # Flask app: form + submit route + CSV writer
├── requirements.txt
├── templates/
│   └── index.html       # the form itself
└── data/
    └── entries.csv       # created automatically on first run/submission
```

## Local test run (optional, before deploying)

```bash
cd daily-log
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

export FORM_USER=yourname
export FORM_PASS=apasswordyoupick
export SECRET_KEY=any-random-string

python app.py
```

Visit `http://127.0.0.1:5000` — your browser will prompt for the
username/password you set above.

## Deploying to PythonAnywhere (free tier)

1. **Sign up** at pythonanywhere.com (free "Beginner" account, no card needed).
2. **Upload the project.** Easiest path: zip the `daily-log` folder, then in
   the PythonAnywhere "Files" tab upload the zip and unzip it via a Bash
   console (`unzip daily-log.zip`). Or push this folder to a GitHub repo and
   `git clone` it from a PythonAnywhere Bash console.
3. **Create a virtualenv** (from a Bash console on PythonAnywhere):
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 daily-log-env
   pip install -r daily-log/requirements.txt
   ```
4. **Set up the Web app:**
   - Go to the **Web** tab → **Add a new web app** → choose **Manual
     configuration** (not the Flask wizard) → pick the Python version
     matching your virtualenv.
   - Under **Virtualenv**, point it at `/home/yourusername/.virtualenvs/daily-log-env`.
   - Under **Code**, set the **Source code** path to your `daily-log` folder.
   - Open the **WSGI configuration file** link and replace its contents with:
     ```python
     import sys
     path = '/home/yourusername/daily-log'
     if path not in sys.path:
         sys.path.append(path)

     import os
     os.environ['FORM_USER'] = 'yourname'
     os.environ['FORM_PASS'] = 'apasswordyoupick'
     os.environ['SECRET_KEY'] = 'any-random-string'

     from app import app as application
     ```
     (Swap in real values — this is the one place it's fine to hardcode
     them, since this file isn't public.)
5. Hit the green **Reload** button on the Web tab. Your form is now live at
   `yourusername.pythonanywhere.com`, password-protected, writing to a CSV
   that lives on PythonAnywhere's persistent storage (survives reloads and
   restarts — it's not ephemeral like some free hosts).

## Getting your data out

- **Quick peek:** PythonAnywhere's Files tab lets you open
  `daily-log/data/entries.csv` directly and view/download it.
- **Bash console:** `cat daily-log/data/entries.csv` or zip it up and
  download via the Files tab.
- For your Python cleanup step, just download the CSV and work with it
  locally as planned (comma-list splitting, etc.) — the fallback-to-timestamp
  logic for missing time is already handled at write-time in `app.py`, so you
  shouldn't need to redo that part in your cleaning script, but it's easy to
  double check/override there later if you change your mind.

## Notes / things you might want to change

- **Vibes options** are set in `app.py` as `VIBE_OPTIONS` — edit that list to
  match whatever scale you actually want.
- **Backups:** it's just one CSV file. Worth periodically downloading a copy
  somewhere else (or, once this feels stable, wiring up a simple weekly
  download-to-local-machine habit).
- **Migrating to SQLite later:** since you mentioned that as a possible next
  step — the cleanest path is to write a one-off script that reads
  `entries.csv` with `csv.DictReader` and inserts rows into a SQLite table via
  `sqlite3`, then switch `append_entry()` in `app.py` to write to SQLite
  instead of CSV going forward. Happy to build that when you're ready; no
  need to plan it now.
- **Security note:** HTTP Basic Auth (what this uses) is fine for a
  low-stakes personal log, but credentials are sent base64-encoded, not
  encrypted, on plain HTTP. PythonAnywhere serves your app over HTTPS by
  default though, which encrypts the whole connection — so this is fine as
  configured. Just don't reuse a password you care about elsewhere.
