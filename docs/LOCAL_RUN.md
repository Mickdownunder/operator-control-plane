# Local Run

## Prerequisites

- Python 3.11+
- Node.js 20+
- npm
- optionally Docker for sandbox-backed paths

## Backend Setup

```bash
cd /path/to/operator-control-plane
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-research.txt -r requirements-test.txt
```

## UI Setup

```bash
cd /path/to/operator-control-plane/ui
npm ci
cp .env.local.example .env.local
```

Set:

- `OPERATOR_ROOT`
- `UI_PASSWORD_HASH`
- `UI_SESSION_SECRET`
- optional: `UI_LOGIN_MAX_ATTEMPTS`, `UI_LOGIN_WINDOW_SECONDS`, `UI_LOGIN_LOCK_SECONDS`

## Start The UI

```bash
cd /path/to/operator-control-plane/ui
npm run dev
```

For production-style local runs:

```bash
cd /path/to/operator-control-plane/ui
npm run build
npm run start
```

## Server Deployment

Use [DEPLOY.md](DEPLOY.md) if you want a long-running server deployment.
