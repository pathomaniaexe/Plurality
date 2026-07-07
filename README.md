# Plurality

**The best DID/OSDD proxy bot for Discord.**

Plurality is a modern Python rewrite built for plural systems — with everything PluralKit does, plus a better experience out of the box.

## Why Plurality?

| Feature | PluralKit | Plurality |
|---------|-----------|-----------|
| Slash commands | ❌ | ✅ Full slash + autocomplete |
| Setup wizard | ❌ | ✅ Interactive `/setup` |
| Database | PostgreSQL required | SQLite by default (zero config) |
| Prefix commands | ✅ | ✅ `pl!` + `plurality!` |
| Proxy tags | ✅ | ✅ 100% compatible |
| Autoproxy modes | ✅ | ✅ front, latch, member |
| Switch tracking | ✅ | ✅ |
| Groups | ✅ | ✅ |
| Import/Export | ✅ | ✅ PluralKit-compatible |
| Mental health tools | Some forks | ✅ Built-in |
| Message edit sync | ✅ | ✅ |
| Privacy controls | ✅ | ✅ |

## Quick Start

### 1. Create a Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create an application → Bot → copy the token
3. Enable **Message Content Intent** and **Server Members Intent**
4. Invite with permissions: Send Messages, Manage Messages, Manage Webhooks, Read Message History

### 2. Install & run

```bash
git clone https://github.com/yourusername/Plurality.git
cd Plurality
pip install -r requirements.txt
cp plurality.toml.example plurality.toml
# Edit plurality.toml with your bot token
python -m plurality
```

Or with environment variables:

```bash
export DISCORD_TOKEN="your_token_here"
python -m plurality
```

### 3. Set up your system

In Discord:

```
/setup          ← interactive wizard (recommended!)
pl!system new   ← or use commands
pl!member new Luna
pl!member proxy Luna add [text]
pl!switch Luna
pl!autoproxy front
```

Then type `[hello!]` in chat and watch it proxy. ✨

## Commands

**Prefix:** `pl!` or `plurality!`

| Category | Examples |
|----------|---------|
| System | `pl!system new`, `pl!system list`, `/system members` |
| Members | `pl!member new <name>`, `pl!member proxy <name> add [text]` |
| Switching | `pl!switch <member>`, `pl!switch out`, `/switch history` |
| Autoproxy | `pl!autoproxy front`, `pl!autoproxy latch`, `pl!autoproxy off` |
| Groups | `pl!group new <name>`, `pl!group add <group> <member>` |
| Server | `pl!blacklist add #channel`, `/permcheck` |
| Data | `pl!export`, `pl!import` (attach JSON file) |
| Support | `pl!grounding`, `pl!breathing`, `pl!hotlines` |

Use `pl!help <topic>` or `/help` for detailed help.

## Proxy Tags

Set tags for a member, then type them around your message:

```
pl!member proxy Luna add [text]
[Hello everyone!]    → proxies as Luna
```

Supported formats: `[text]`, `{text}`, `prefix|suffix`, `:: text ::`

Prefix `\` to skip autoproxy: `\this won't autoproxy`

## Docker

```bash
export DISCORD_TOKEN="your_token"
docker compose -f docker-compose.python.yml up -d
```

## Development

```bash
pip install -r requirements.txt pytest
pytest tests/
```

## License

Plurality is a fork inspired by [PluralKit](https://github.com/pluralkit/pluralkit) by xSke, licensed under the **GNU Affero General Public License v3.0**.

## For the community

Built with love for DID/OSDD systems. You deserve tools that actually work for you. 💜
