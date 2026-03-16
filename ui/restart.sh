#!/bin/bash
cd "$(dirname "$0")"

echo "1. Stopping old Next.js processes..."
pkill -f next-server || true
pkill -f "next start" || true

echo "2. Clearing Next.js cache..."
rm -rf .next

echo "3. Rebuilding UI..."
npm run build

echo "4. Starting server in the background (0.0.0.0:3000)..."
nohup npm run start -- -p 3000 -H 0.0.0.0 > ui.log 2>&1 < /dev/null &

echo "5. Server starting. Follow logs with 'tail -f ui.log'."
