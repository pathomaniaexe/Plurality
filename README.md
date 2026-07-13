# Plurality

A modern DID/OSDD proxy bot for Discord — slash commands, interactive setup, SQLite by default.

**Please keep in mind that this will be updated while I have time — I work full time and this is side stuff for me right now** <3

Built for plural systems, with love.

## Quick start (3 steps)

```bash
git clone https://github.com/pathomaniaexe/Plurality.git
cd Plurality
./setup.sh
```

Then open `.env` and paste your [Discord bot token](https://discord.com/developers/applications):

```
DISCORD_TOKEN=your_token_here
```

Run the bot:

```bash
python3 -m plurality
```

In Discord, type `/setup` to get started.

## Discord bot setup

1. [Discord Developer Portal](https://discord.com/developers/applications) → New Application → Bot
2. Copy the token into `.env`
3. Enable **Message Content Intent** + **Server Members Intent**
4. Invite the bot with: Send Messages, Manage Messages, Manage Webhooks, Read Message History

## Configuration

You can use **either** `.env` or `plurality.toml` (env vars win if both are set).

| File | Purpose |
|------|---------|
| `.env.example` → `.env` | Token (simplest) |
| `plurality.toml.example` → `plurality.toml` | Full config file |

Database is **SQLite** — a single file (`plurality.db`) created automatically. No extra install.

```
DATABASE_URL=sqlite+aiosqlite:///plurality.db
```

## Commands

| Prefix | Slash |
|--------|-------|
| `pl!system new` | `/system new` |
| `pl!member new Luna` | `/member new` |
| `pl!member proxy Luna add [text]` | `/member proxy` |
| `pl!switch Luna` | `/switch register` |
| `pl!autoproxy front` | `/autoproxy` |
| `pl!help` | `/help` |

Type `[hello]` in chat after setting proxy tags to test proxying.

## Proxy tags

```
pl!member proxy Luna add [text]
[Hello everyone!]    → proxies as Luna
```

Supported formats: `[text]`, `{text}`, `prefix|suffix`, `:: text ::`

Prefix `\` to skip autoproxy: `\this won't autoproxy`

## Docker

```bash
cp .env.example .env   # add your token
docker compose up -d
```

SQLite data is stored in `./data/plurality.db`.

## Project layout

```
plurality/          ← the bot (all Python code)
tests/              ← tests
setup.sh            ← one-command local setup
.env.example        ← copy to .env
plurality.toml.example  ← copy to plurality.toml (optional)
```

## Development

```bash
pip install -r requirements.txt pytest
pytest tests/
```

## License

Fork-inspired by [PluralKit](https://github.com/pluralkit/pluralkit) (AGPL-3.0). Built for the plural community.
