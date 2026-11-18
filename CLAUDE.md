# relic5 — Oraclep-World fork

Owner: tinky
Upstream: Soul-Brews-Studio/relic5 (Nat) — read-only for us. Never push or open PRs upstream.

This fork runs relic5 as our own hub on machine `main` (WSL2 Ubuntu 24.04).
Pleam, 18 Nov 2026: "เปลี่ยนเป็นชื่อเราเลย" · "ทำให้เป็นของเรา" · "เริ่มเลย".

Rules:
- Branch `alpha` tracks our fork (`origin` = Oraclep-World/relic5).
- No secrets in commits. The hub indexes every house's transcripts, so bind it to loopback or our tailnet only — never a public address.
- Nothing is Deleted: disable Nat-specific paths with a clear message. Don't remove code.
- Changes from upstream are listed in `docs/OURS.md`.
