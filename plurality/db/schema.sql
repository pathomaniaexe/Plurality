-- Plurality database schema (SQLite-compatible)

CREATE TABLE IF NOT EXISTS info (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version INTEGER NOT NULL DEFAULT 1
);
INSERT OR IGNORE INTO info (id, schema_version) VALUES (1, 1);

CREATE TABLE IF NOT EXISTS systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hid TEXT UNIQUE NOT NULL,
    name TEXT,
    description TEXT,
    tag TEXT,
    avatar_url TEXT,
    token TEXT,
    color TEXT,
    created TEXT NOT NULL DEFAULT (datetime('now')),
    ui_tz TEXT NOT NULL DEFAULT 'UTC',
    pings_enabled INTEGER NOT NULL DEFAULT 1,
    description_privacy INTEGER NOT NULL DEFAULT 2,
    member_list_privacy INTEGER NOT NULL DEFAULT 2,
    front_privacy INTEGER NOT NULL DEFAULT 2,
    front_history_privacy INTEGER NOT NULL DEFAULT 2,
    group_list_privacy INTEGER NOT NULL DEFAULT 2,
    member_limit_override INTEGER,
    group_limit_override INTEGER
);

CREATE TABLE IF NOT EXISTS system_guild (
    system INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    guild INTEGER NOT NULL,
    proxy_enabled INTEGER NOT NULL DEFAULT 1,
    autoproxy_mode INTEGER NOT NULL DEFAULT 0,
    autoproxy_member INTEGER,
    PRIMARY KEY (system, guild)
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hid TEXT UNIQUE NOT NULL,
    system INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    color TEXT,
    avatar_url TEXT,
    name TEXT NOT NULL,
    display_name TEXT,
    birthday TEXT,
    pronouns TEXT,
    description TEXT,
    proxy_tags TEXT NOT NULL DEFAULT '[]',
    keep_proxy INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT (datetime('now')),
    member_visibility INTEGER NOT NULL DEFAULT 2,
    description_privacy INTEGER NOT NULL DEFAULT 2,
    avatar_privacy INTEGER NOT NULL DEFAULT 2,
    name_privacy INTEGER NOT NULL DEFAULT 2,
    birthday_privacy INTEGER NOT NULL DEFAULT 2,
    pronoun_privacy INTEGER NOT NULL DEFAULT 2,
    metadata_privacy INTEGER NOT NULL DEFAULT 2
);

CREATE TABLE IF NOT EXISTS member_guild (
    member INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    guild INTEGER NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    PRIMARY KEY (member, guild)
);

CREATE TABLE IF NOT EXISTS accounts (
    uid INTEGER PRIMARY KEY,
    system INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    mid INTEGER PRIMARY KEY,
    channel INTEGER NOT NULL,
    guild INTEGER,
    member INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    sender INTEGER NOT NULL,
    original_mid INTEGER
);

CREATE TABLE IF NOT EXISTS switches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS switch_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    switch INTEGER NOT NULL REFERENCES switches(id) ON DELETE CASCADE,
    member INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hid TEXT UNIQUE NOT NULL,
    system INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    display_name TEXT,
    description TEXT,
    icon TEXT,
    color TEXT,
    created TEXT NOT NULL DEFAULT (datetime('now')),
    description_privacy INTEGER NOT NULL DEFAULT 2,
    icon_privacy INTEGER NOT NULL DEFAULT 2,
    visibility INTEGER NOT NULL DEFAULT 2
);

CREATE TABLE IF NOT EXISTS group_members (
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    member INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, member)
);

CREATE TABLE IF NOT EXISTS webhooks (
    channel INTEGER PRIMARY KEY,
    webhook INTEGER NOT NULL,
    token TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY,
    log_channel INTEGER,
    log_blacklist TEXT NOT NULL DEFAULT '[]',
    blacklist TEXT NOT NULL DEFAULT '[]',
    log_cleanup INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS command_messages (
    message_id INTEGER PRIMARY KEY,
    author_id INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_members_system ON members(system);
CREATE INDEX IF NOT EXISTS idx_switches_system ON switches(system);
CREATE INDEX IF NOT EXISTS idx_switch_members_switch ON switch_members(switch);
CREATE INDEX IF NOT EXISTS idx_messages_member ON messages(member);
CREATE INDEX IF NOT EXISTS idx_groups_system ON groups(system);