#!/usr/bin/env bash
# One-command setup for Plurality
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Plurality setup"
echo

# Python 3 check
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found. Install Python 3.9+ first."
  exit 1
fi

echo "==> Installing dependencies..."
python3 -m pip install -r requirements.txt

# Config files
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env — add your DISCORD_TOKEN there"
else
  echo "==> .env already exists, skipping"
fi

if [[ ! -f plurality.toml ]]; then
  cp plurality.toml.example plurality.toml
  echo "==> Created plurality.toml — add your bot token there (or use .env)"
else
  echo "==> plurality.toml already exists, skipping"
fi

echo
echo "Done! Next steps:"
echo "  1. Add your Discord bot token to .env or plurality.toml"
echo "  2. Run: python3 -m plurality"
echo
echo "Uses SQLite by default (plurality.db) — no database install needed."
echo
