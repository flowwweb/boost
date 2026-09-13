# Boost

Boost is a small, local-first Codex plugin for planning and reviewing social activity across X accounts.

## Run locally

```powershell
python scripts/serve.py --port 8765
```

Open `http://127.0.0.1:8765/mockup.html`.

Fresh installs start with no accounts; use **Add account** to choose X, LinkedIn, Instagram, YouTube, or Threads and add its handle or profile name. Each project can choose **Official API** (the local xurl OAuth path) or **Browser automation** (a signed-in browser session); the choice is visible in Accounts and Settings and clears prior verification when changed. The dashboard keeps platform account tabs, core metrics, repeatable post/reply/DM cycles, a weekly bar calendar, local activity, token estimates, and per-project settings in one surface. Boost mode is the single opt-in switch for network participation and platform-aware handoffs; the current V1 only plans and records those actions locally. Preferences and schedules stay local. X credentials remain with [`xurl`](https://github.com/xdevplatform/xurl); Boost only calls its privacy-safe `whoami` probe.

## V1 boundary

V1 is a local planning and draft-control surface. It includes schedule persistence, per-account cycle assignments, explicit action targets (post, reply to others, reply to your posts, or DM), official API or browser connection selection, theme and timezone settings, xurl status checks, and receipt export. Live publishing, automated engagement, browser-session execution, cross-member Boost network actions, analytics ingestion, and team permissions stay out of V1 until the provider contract and approval workflow are explicit.

Authenticate xurl manually, then use **Accounts → Refresh status**:

```powershell
xurl auth oauth2
```

Boost never reads or stores the credentials under xurl's control.
