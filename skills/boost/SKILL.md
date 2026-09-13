---
name: boost
description: Minimal local control surface for social accounts.
---

# Boost

Use the one-screen dashboard to switch platform account tabs, add an account, choose its connection method (Official API via xurl or Browser automation via a signed-in browser session), complete its provider integration, review follower/engagement metrics, set daily post/reply targets, manage repeatable post/reply-to-others/reply-to-own-post/DM loops, review the weekly bar calendar, toggle the single Boost mode switch (which represents opt-in Boost network participation), and tune project, usage, theme, and timezone preferences. The Schedule, Cycles, Accounts, Activity, and Settings screens expose the same selected account and local schedule state; Settings also controls Codex task sync and shows the selected platform's documented handoff tactic. Keep provider actions behind the selected connection method and respect the selected approval mode.

Record only useful receipts: account, action, timestamp, and provider confirmation. Reconcile uncertain writes before retrying. Do not add extra strategy, analytics, or workflow layers unless the user asks for them.

V1 is local planning and draft control: do not claim live publishing or engagement until xurl authentication and an explicit approval policy are present.

Start with `python scripts/serve.py` and open `http://127.0.0.1:8765/mockup.html`.
