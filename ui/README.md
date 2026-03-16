# operator-control-plane UI

Next.js dashboard and API surface for `operator-control-plane`.

<p>
  <a href="https://github.com/Mickdownunder/operator-control-plane/actions/workflows/quality-gates.yml"><img alt="Quality Gates" src="https://github.com/Mickdownunder/operator-control-plane/actions/workflows/quality-gates.yml/badge.svg"></a>
  <a href="https://github.com/Mickdownunder/operator-control-plane/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/Mickdownunder/operator-control-plane"></a>
</p>

It requires the full Operator repository to be available via `OPERATOR_ROOT`.

## What It Covers

- single-user login/session gate for control-plane actions
- command center for health, jobs, and bounded workflow triggers
- research project inspection and operator actions
- audit trail writes (`logs/ui-audit.log`)

It is not a standalone backend. It is a view/control layer on top of the
Operator runtime.

## Quickstart

### Setup

```bash
cd /path/to/operator-control-plane/ui
npm ci
cp .env.local.example .env.local
```

### Required env (`.env.local`)

- `OPERATOR_ROOT` — absolute path to the `operator-control-plane` repo root
- `UI_PASSWORD_HASH` — preferred: `scrypt$N$r$p$salt_hex$hash_hex`; legacy SHA-256 hex still accepted
- `UI_SESSION_SECRET` — random string for session signing; required outside tests

### Optional env

- `UI_TELEGRAM_NOTIFY=1` — send Telegram notification for selected UI-triggered actions
- `UI_LOGIN_MAX_ATTEMPTS` — optional: attempts allowed per window before lockout (default `5`)
- `UI_LOGIN_WINDOW_SECONDS` — optional: failure counting window (default `300`)
- `UI_LOGIN_LOCK_SECONDS` — optional: lockout duration after limit reached (default `300`)

### Run

- `npm run dev` - development (port `3000`)
- `npm run build && npm run start` - production-style local run

### Validate

```bash
npm test
```

## Related Docs

- [../README.md](../README.md) - top-level repository overview
- [../docs/LOCAL_RUN.md](../docs/LOCAL_RUN.md) - local runtime guide
- [../docs/DEPLOY.md](../docs/DEPLOY.md) - deployment guide
