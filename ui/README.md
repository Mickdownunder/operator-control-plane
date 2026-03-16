# Worldclass Agent — Operator UI

Next.js dashboard for the Operator. Requires the Operator repo to be available at
`OPERATOR_ROOT`.

## Run

- `npm run dev` — development (port 3000)
- `npm run build` && `npm run start` — production

## Env (.env.local)

- Copy `.env.local.example` to `.env.local`
- `OPERATOR_ROOT` — absolute path to the Operator repo
- `UI_PASSWORD_HASH` — hex SHA-256 of login password (e.g. `echo -n "mypass" | sha256sum | cut -d' ' -f1`)
- `UI_SESSION_SECRET` — random string for session signing; required outside tests
- `UI_TELEGRAM_NOTIFY=1` — optional: send Telegram when UI triggers factory/brain/retry

## Features

- Login (single user, password)
- Command Center: health, recent activity, Run Factory / Brain Cycle
- Jobs: list, detail, retry
- Packs: list, detail
- Brain & Memory: episodes, reflections, playbooks
- Clients: config list
- Actions logged to `operator/logs/ui-audit.log`
