# operator-control-plane UI

Next.js dashboard for the Operator. Requires the Operator repo to be available at
`OPERATOR_ROOT`.

## Run

- `npm run dev` — development (port 3000)
- `npm run build` && `npm run start` — production

## Env (.env.local)

- Copy `.env.local.example` to `.env.local`
- `OPERATOR_ROOT` — absolute path to the Operator repo
- `UI_PASSWORD_HASH` — preferred: `scrypt$N$r$p$salt_hex$hash_hex`; legacy SHA-256 hex still accepted
- `UI_SESSION_SECRET` — random string for session signing; required outside tests
- `UI_TELEGRAM_NOTIFY=1` — optional: send Telegram when UI triggers factory/brain/retry
- `UI_LOGIN_MAX_ATTEMPTS` — optional: attempts allowed per window before lockout (default `5`)
- `UI_LOGIN_WINDOW_SECONDS` — optional: failure counting window (default `300`)
- `UI_LOGIN_LOCK_SECONDS` — optional: lockout duration after limit reached (default `300`)

## Features

- Login (single user, password)
- Command Center: health, recent activity, Run Factory / Brain Cycle
- Jobs: list, detail, retry
- Packs: list, detail
- Brain & Memory: episodes, reflections, playbooks
- Clients: config list
- Actions logged to `operator/logs/ui-audit.log`
