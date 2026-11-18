# OURS: what this fork changes from upstream

This is Oraclep-World's fork of Soul-Brews-Studio/relic5 (Nat's). It runs as **our** hub on machine `main`
(Ubuntu 24.04 on WSL2, user `pleamvelli`). Upstream is read-only for us: never push or open PRs there.
Issue: Oraclep-World/relic5#1. Requested by Pleam, 18 Nov 2026.

## What changed

Nothing was deleted (Nothing is Deleted): Nat-specific paths are switched off with a message or turned into env settings.

| Area | Upstream default | Ours |
|---|---|---|
| Hub URL (`RELIC5_URL`, Rust CLI `cli/src/hub.rs`, `evaluate.py`, `bin/relic5-rule-check`, `bin/relic5-mcp-headers`, `bin/relic5-month-recap`) | `http://white.follow-rankine.ts.net:8795` | `http://127.0.0.1:8795` |
| Hub ssh target (`RELIC5_HUB_SSH`, `worker.py`, `cli.py import relic3`, `bin/relic5-month-recap`) | `nat@white.follow-rankine.ts.net` | `pleamvelli@main-wsl` (our tailnet name once Tailscale is up) |
| `bin/relic5-push` hub (`RELIC5_HUB`) | `nat@white…` over ssh | `local`: this machine is the hub, no ssh to itself. A loopback URL means local. A non-loopback URL means `${RELIC5_HUB_USER:-$USER}@host` |
| `relic5 import` (`cli/src/import.rs`) | ssh `nat@<host>` for index and the sync verdict | `local` for a loopback hub (runs `relic5 index --wait` with `sh -c`); else `${RELIC5_HUB_USER:-$USER}@<host>` |
| `deploy/systemd/relic5-serve.service` | binds `127.0.0.1,100.103.52.67` | binds `127.0.0.1` only. A systemd *user* unit runs as whoever installs it (`pleamvelli`) |
| S3 (`store.py`, `bin/relic5-push` s3 hub) | `http://black.follow-rankine.ts.net:9200`, region `black-ssd-rustfs` | `http://127.0.0.1:9200`, region `us-east-1`; set `RELIC5_S3_ENDPOINT` to use one |
| `bin/relic5-offsite` | copies to Nat's black RustFS | **off** until `RELIC5_S3_ENDPOINT` is set (exits 2 with a message) |
| `worker.py` gb300 engine | `RELIC5_RELIC4` = retired `agent-relic-v4` under `/opt/Code/...` | **disabled**: `--engine gb300` stops with a clear message unless `RELIC5_RELIC4` points at a relic4 checkout with `.venv/bin/python`. Code kept. |
| `worker.py` rsync target | `nat@white` | `pleamvelli@main-wsl` (`RELIC5_HUB_SSH`). Vectors are a separate issue; not run here |
| `bin/relic5-backup` | pulls from `nat@white` into `<volume>/white`, `/opt/homebrew/bin/rsync` | hub `local` by default (`RELIC5_HUB_SSH=user@host` for a remote one), target `~/relic5-backup/main` (`RELIC5_BACKUP_DIR`), `rsync` from PATH (Homebrew's only if present) |
| `bin/relic5-restore-test` | APFS `cp -c` | Linux: `cp -R --reflink=auto`, plain copy fallback; macOS keeps `cp -c` |
| `deploy/hub-switch/*` (white to m5 failover) | Nat's two hubs, hard-coded | not used on `main`; every host is an env var (`RELIC5_STANDBY_HOST`, `RELIC5_STANDBY_SSH`, `RELIC5_PRIMARY_SSH`, `RELIC5_HUB_TAILNET_IP`, `RELIC5_PUBLIC_DOOR_IP`) and the scripts refuse to run without them |
| `deploy/launchd/*claude-sync*` | `/Users/nat/.claude` | placeholder `/Users/<other>/.claude` (macOS only) |
| Comments, docstrings | names Nat's machines | explain upstream; no machine names |

Also fixed (found while running it on `main`):

- `doors.tailscale_self()` crashed `relic5 serve` when Tailscale is installed but not logged in (`"User": null`). It now
  serves on the loopback door only.
- The CLI (`relic5 search`, `status`, ...) needed `~/.config/relic5/token` even against a loopback hub. A missing token
  file is now fine when `RELIC5_URL` is loopback; the hub's loopback door needs none.
- `bin/relic5-push`: new `RELIC5_MEMORY=0` switch to skip copying `~/.claude*/projects/*/memory` notes (default is unchanged: on).

Not touched: vectors/embeddings (GPU is a separate issue), the Hours and Family pages (their sources, odin-oracle and
mother-oracle, are not public: those pages stay empty), `~/.claude`, `~/.oracle`, other houses' repos.

Remaining mentions of Nat's names in `src bin cli/src deploy` are comments saying what upstream did.
`grep -rn "follow-rankine\|nat@white\|100.103.52.67\|/Users/nat" src bin cli/src deploy` returns only the comment
in `bin/relic5-push` (the `/Users/nat` realpath-guard note).

## Environment variables

All optional; the defaults are ours.

| Variable | Default | Meaning |
|---|---|---|
| `RELIC5_ROOT` | `~/relic5` | the hub's data root |
| `RELIC5_URL` | `http://127.0.0.1:8795` | where clients find the hub |
| `RELIC5_HUB` | `local` | `bin/relic5-push`: `local`, `user@host`, or the hub's http URL |
| `RELIC5_HUB_SSH` | `pleamvelli@main-wsl` (`local` for push and backup) | ssh target of a hub elsewhere |
| `RELIC5_HUB_USER` | `$USER` | user for `RELIC5_HUB` given as a URL |
| `RELIC5_HUB_INDEX` | `relic5 index --wait` (local hub) | the command that indexes on the hub (`relic5 import`) |
| `RELIC5_MACHINE` or `~/.config/relic5/machine` | none | this machine's name (we use `main`) |
| `RELIC5_BACKUP_DIR` | `~/relic5-backup/main` | where `bin/relic5-backup` writes snapshots |
| `RELIC5_S3_ENDPOINT` | `http://127.0.0.1:9200` | S3 hub / offsite endpoint (offsite is off unless set) |
| `RELIC5_RELIC4` | empty | relic4 checkout for the (disabled) gb300 engine |
| `RELIC5_MEMORY`, `RELIC5_CONFIG`, `RELIC5_GIT` | `1` | set `0` to skip memory notes / config files / git commits in `bin/relic5-push` |

## Run it on `main` (no vectors)

One time:

```sh
# 1. this repo
cd ~/ghq/github.com/Oraclep-World/relic5            # or a worktree of it
uv sync --no-dev

# 2. relic-extract from our fork, unmodified
uv tool install git+https://github.com/Oraclep-World/relic-extract

# 3. name the machine
mkdir -p ~/.config/relic5 && echo main > ~/.config/relic5/machine
```

Scan data: `~/.relic-scan` (relic4-scan, our fork `Oraclep-World/relic4-scan`). Run `relic-scan run` to refresh it. It reads
every transcript on the machine, so ask Pleam first. The scan is read-only for transcripts and writes only `~/.relic-scan`.

Each time (the manual steps of `relic5 import`, without the scan and without vectors):

```sh
relic-extract run                                   # ~/.relic-scan -> ~/.relic-extract (text stream)
RELIC5_NEW_MACHINE=1 RELIC5_MEMORY=0 RELIC5_CONFIG=0 RELIC5_GIT=0 bin/relic5-push   # -> ~/relic5/parts/main  (drop RELIC5_NEW_MACHINE after the first push)
uv run relic5 index --root ~/relic5 --wait          # manifests + BM25 tables
uv run relic5 serve --root ~/relic5 --host 127.0.0.1 --port 8795
```

`relic5 import` (the Rust CLI, `just cli`) does scan, extract, push, index, embed and sync in one go. On `main` it needs
`relic-scan` on PATH and `RELIC5_HUB_INDEX="cd <checkout> && uv run relic5 index --root ~/relic5 --wait"`
(or `relic5` on PATH). Its embed stage skips itself on Linux.

Check:

```sh
curl -s http://127.0.0.1:8795/health                # {"ok":true}
uv run relic5 search ferris --limit 3
uv run relic5 status
```

MCP (words only, no vectors): `claude mcp add --transport http relic5 http://127.0.0.1:8795/mcp`. The tool argument is `query`.

Run it as a service: `cp deploy/systemd/relic5-serve.service ~/.config/systemd/user/`, then edit its `ExecStart` to your
checkout (`uv run relic5 serve ...` or a `.venv/bin/relic5`), `systemctl --user daemon-reload`,
`systemctl --user enable --now relic5-serve`.

Backup and restore test:

```sh
bin/relic5-backup                # -> ~/relic5-backup/main/<date>, hub = this machine
bin/relic5-restore-test          # rebuilds a scratch hub from the newest snapshot; exit 0 = counts match
```

## Privacy

The hub indexes every house's transcripts. Keep it on `127.0.0.1` (or our tailnet later, in its own issue). Never bind
`0.0.0.0` or a public address.
