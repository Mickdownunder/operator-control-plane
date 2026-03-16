# Deploy

## Prerequisites

- Node.js 20+
- Python 3.11+
- `npm`
- the full repository available on the target machine

If you need sandbox-backed experiment paths, Docker should also be available.

## 1. Put The Repo On The Server

Example:

```bash
git clone <your-repo-url> /srv/operator-control-plane
cd /srv/operator-control-plane
```

The UI expects the entire repository, not just the `ui/` folder.

## 2. Configure Runtime Variables

The UI needs:

- `OPERATOR_ROOT`
- `UI_PASSWORD_HASH`
- `UI_SESSION_SECRET`
- optional hardening: `UI_LOGIN_MAX_ATTEMPTS`, `UI_LOGIN_WINDOW_SECONDS`, `UI_LOGIN_LOCK_SECONDS`
- optionally `PORT`

You can use `ui/.env.local`:

```bash
cd /srv/operator-control-plane/ui
cp .env.local.example .env.local
```

Or export them from your shell or service manager:

```bash
export OPERATOR_ROOT=/srv/operator-control-plane
export UI_PASSWORD_HASH="$(node -e 'const crypto=require(\"crypto\"); const password=\"replace-me\"; const salt=crypto.randomBytes(16); const N=16384,r=8,p=1; const hash=crypto.scryptSync(password,salt,64,{N,r,p,maxmem:128*N*r+1024*1024}); process.stdout.write(`scrypt$${N}$${r}$${p}$${salt.toString(\"hex\")}$${hash.toString(\"hex\")}`)')"
export UI_SESSION_SECRET="$(openssl rand -hex 32)"
export UI_LOGIN_MAX_ATTEMPTS=5
export UI_LOGIN_WINDOW_SECONDS=300
export UI_LOGIN_LOCK_SECONDS=300
export PORT=3000
```

## 3. Build And Start

```bash
cd /srv/operator-control-plane/ui
npm ci
npm run build
npm run start
```

The application will listen on `http://<host>:3000` unless you override
`PORT`.

## 4. Run As A Service

The repository includes a sample systemd unit:

```bash
sudo cp /srv/operator-control-plane/scripts/operator-ui.service.example /etc/systemd/system/operator-ui.service
sudo systemctl daemon-reload
sudo systemctl enable operator-ui
sudo systemctl start operator-ui
```

## 5. Reverse Proxy

For public internet access, put a reverse proxy in front of the Next.js app:

- nginx
- Caddy
- another HTTP reverse proxy of your choice

Proxy to `127.0.0.1:$PORT`.

## 6. Verify

```bash
cd /srv/operator-control-plane
./scripts/run-system-check.sh
```

Then log into the UI and confirm that projects, jobs, and health surfaces load
correctly.
