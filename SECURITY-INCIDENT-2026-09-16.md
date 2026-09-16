# Security incident: 16 September 2026

An unexpected hidden VS Code folder-open task invoked Node on a font-named payload. This commit removes the identified launcher and payload and disables automatic tasks. Environment files are excluded from Git.

Do not run older checkouts, cached packages, tags or release artifacts until reviewed. Existing clones are not repaired automatically. If affected tooling was executed or the workspace was opened with automatic tasks allowed, isolate the potentially affected environment, preserve evidence and obtain an endpoint assessment. Rotate credentials accessible to that environment from a known-clean device and invalidate relevant sessions. Do not put replacement credentials onto a potentially affected machine.

Source contamination is confirmed; payload execution, data theft, entry point and attribution are not established. Targeted source cleanup does not certify machines, production deployments, historical commits or release artifacts. History is preserved; no force-push or history rewrite was performed. Review distributions before resuming releases.
