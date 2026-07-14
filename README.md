# Daily Log

A small, self-hosted daily activity tracker. Built to log an entry in about 15 seconds, on desktop or mobile, and write output for analytics.

## Why this exists

I wanted a lightweight way to log a daily activity. Rather than reach for a no-code tool, I used it as an opportunity to build (and deploy) something small end-to-end: a Flask app with a single form, writing straight to a CSV I control, hosted on my own account rather than a third-party form service.

## Stack

- **Python / Flask** — form handling and routing
- **uv** — dependency and environment management
- **HTML/CSS** — single-page form, no JS framework needed at this scale
- **CSV** (planned migration to **SQLite**) — storage
- Deployed on PythonAnywhere
- **Claude Code** — to sharpen AI-assisted coding skills

## How it works

- A single form collects date, time, a short text entry, and a categorical "vibes" rating.
- Submissions are appended to a CSV with a server-side timestamp.
- If no time is entered, the app falls back to the submission timestamp automatically, so that logic lives in one place instead of being reconstructed later during analysis.
- The form sits behind basic auth, since it's reachable from the open internet but only meant for one user.

## Roadmap

- [x] Flask app with form → CSV pipeline
- [x] Deployed and password-protected
- [ ] Migrate storage from CSV to SQLite
- [ ] Python analysis pipeline (cleaning, transforming multi-value fields, basic trend analysis)
- [ ] Possible lightweight dashboard for viewing trends over time

## Status

Early and actively evolving — currently in daily use for data collection, with the analysis layer still to come.

---

*Setup/deployment details are kept in an internal, gitignored doc since this repo isn't meant to be a general-purpose template — but the app itself is small enough to read end-to-end in `app.py`.*