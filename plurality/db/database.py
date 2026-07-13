"""Async SQLite database layer."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any

from plurality.constants import AutoproxyMode, PrivacyLevel
from plurality.db import dialect
from plurality.db.backends import SqliteBackend
from plurality.db.models import Group, Member, MessageContext, ProxyTag, Switch, System
from plurality.db.url import parse_sqlite_path
from plurality.utils.ids import generate_hid


class Database:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///plurality.db"):
        self.path = parse_sqlite_path(database_url)
        self._backend = SqliteBackend(self.path)

    async def connect(self) -> None:
        await self._backend.connect()
        await self._backend.migrate()

    async def close(self) -> None:
        await self._backend.close()

    async def _fetchone(self, query: str, params: tuple = ()) -> dict | None:
        return await self._backend.fetchone(query, params)

    async def _fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        return await self._backend.fetchall(query, params)

    async def _execute(self, query: str, params: tuple = ()) -> int:
        return await self._backend.execute(query, params)

    async def _insert_id(self, query: str, params: tuple = ()) -> int:
        return await self._backend.insert_returning_id(query, params)

    def _parse_id_list(self, value: Any) -> list[int]:
        if value is None:
            return []
        if isinstance(value, list):
            return [int(x) for x in value]
        if isinstance(value, str):
            return json.loads(value) if value else []
        return []

    def _encode_id_list(self, values: list[int]) -> str:
        return json.dumps(values)

    # ── Systems ──────────────────────────────────────────────────────────

    async def get_system_by_account(self, uid: int) -> System | None:
        row = await self._fetchone(
            """
            SELECT s.* FROM systems s
            JOIN accounts a ON a.system = s.id
            WHERE a.uid = ?
            """,
            (uid,),
        )
        return self._row_to_system(row) if row else None

    async def get_system(self, system_id: int | str) -> System | None:
        if isinstance(system_id, str):
            row = await self._fetchone("SELECT * FROM systems WHERE hid = ?", (system_id,))
        else:
            row = await self._fetchone("SELECT * FROM systems WHERE id = ?", (system_id,))
        return self._row_to_system(row) if row else None

    async def create_system(self, uid: int, name: str | None = None) -> System:
        hid = await self._unique_hid("systems")
        token = secrets.token_urlsafe(32)
        sys_id = await self._insert_id(
            "INSERT INTO systems (hid, name, token) VALUES (?, ?, ?)",
            (hid, name, token),
        )
        await self._execute("INSERT INTO accounts (uid, system) VALUES (?, ?)", (uid, sys_id))
        system = await self.get_system(sys_id)
        assert system is not None
        return system

    async def update_system(self, system_id: int, **fields: Any) -> None:
        allowed = {
            "name", "description", "tag", "avatar_url", "color", "ui_tz",
            "pings_enabled", "description_privacy", "member_list_privacy",
            "front_privacy", "front_history_privacy", "group_list_privacy",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return
        cols = ", ".join(f"{k} = ?" for k in updates)
        await self._execute(
            f"UPDATE systems SET {cols} WHERE id = ?",
            (*updates.values(), system_id),
        )

    async def delete_system(self, system_id: int) -> None:
        await self._execute("DELETE FROM systems WHERE id = ?", (system_id,))

    async def link_account(self, uid: int, system_id: int) -> None:
        sql = dialect.insert_replace("accounts", "uid, system", "?, ?")
        await self._execute(sql, (uid, system_id))

    async def unlink_account(self, uid: int) -> None:
        await self._execute("DELETE FROM accounts WHERE uid = ?", (uid,))

    async def get_linked_accounts(self, system_id: int) -> list[int]:
        rows = await self._fetchall(
            "SELECT uid FROM accounts WHERE system = ?", (system_id,)
        )
        return [r["uid"] for r in rows]

    # ── Members ──────────────────────────────────────────────────────────

    async def get_members(self, system_id: int, guild_id: int | None = None) -> list[Member]:
        order = dialect.order_name("m.name")
        if guild_id:
            rows = await self._fetchall(
                f"""
                SELECT m.*, mg.display_name AS guild_display_name,
                       mg.avatar_url AS guild_avatar_url,
                       (SELECT COUNT(*) FROM messages msg WHERE msg.member = m.id) AS message_count
                FROM members m
                LEFT JOIN member_guild mg ON mg.member = m.id AND mg.guild = ?
                WHERE m.system = ?
                ORDER BY {order}
                """,
                (guild_id, system_id),
            )
        else:
            rows = await self._fetchall(
                f"""
                SELECT m.*,
                       (SELECT COUNT(*) FROM messages msg WHERE msg.member = m.id) AS message_count
                FROM members m WHERE m.system = ?
                ORDER BY {order}
                """,
                (system_id,),
            )
        return [Member.from_row(r) for r in rows]

    async def get_member(self, member_id: int | str, guild_id: int | None = None) -> Member | None:
        if isinstance(member_id, str):
            base = "SELECT m.* FROM members m WHERE m.hid = ?"
            params: tuple = (member_id,)
        else:
            base = "SELECT m.* FROM members m WHERE m.id = ?"
            params = (member_id,)

        if guild_id:
            row = await self._fetchone(
                base.replace(
                    "FROM members m",
                    "FROM members m LEFT JOIN member_guild mg ON mg.member = m.id AND mg.guild = ?",
                ).replace(
                    "m.*",
                    "m.*, mg.display_name AS guild_display_name, mg.avatar_url AS guild_avatar_url",
                ),
                (guild_id, *params),
            )
        else:
            row = await self._fetchone(base, params)

        if not row:
            return None
        row_dict = dict(row)
        count_row = await self._fetchone(
            "SELECT COUNT(*) AS c FROM messages WHERE member = ?",
            (row_dict["id"],),
        )
        row_dict["message_count"] = count_row["c"] if count_row else 0
        return Member.from_row(row_dict)

    async def find_member(self, system_id: int, query: str, guild_id: int | None = None) -> Member | None:
        members = await self.get_members(system_id, guild_id)
        query_lower = query.lower()
        for m in members:
            if m.hid == query_lower or m.name.lower() == query_lower:
                return m
            if m.display_name and m.display_name.lower() == query_lower:
                return m
            if m.guild_display_name and m.guild_display_name.lower() == query_lower:
                return m
        for m in members:
            if query_lower in m.name.lower():
                return m
            if m.display_name and query_lower in m.display_name.lower():
                return m
        return None

    async def create_member(self, system_id: int, name: str) -> Member:
        hid = await self._unique_hid("members")
        member_id = await self._insert_id(
            "INSERT INTO members (hid, system, name) VALUES (?, ?, ?)",
            (hid, system_id, name),
        )
        member = await self.get_member(member_id)
        assert member is not None
        return member

    async def update_member(self, member_id: int, **fields: Any) -> None:
        allowed = {
            "name", "display_name", "description", "pronouns", "birthday",
            "avatar_url", "color", "proxy_tags", "keep_proxy",
            "member_visibility", "description_privacy", "avatar_privacy",
            "name_privacy", "birthday_privacy", "pronoun_privacy", "metadata_privacy",
        }
        updates: dict[str, Any] = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == "proxy_tags" and isinstance(v, list):
                tag_dicts = [t.to_dict() if isinstance(t, ProxyTag) else t for t in v]
                updates[k] = json.dumps(tag_dicts)
            elif k == "keep_proxy":
                updates[k] = int(v)
            elif k.endswith("_privacy") and isinstance(v, PrivacyLevel):
                updates[k] = int(v)
            elif v is not None:
                updates[k] = v

        if not updates:
            return
        cols = ", ".join(f"{k} = ?" for k in updates)
        await self._execute(
            f"UPDATE members SET {cols} WHERE id = ?",
            (*updates.values(), member_id),
        )

    async def delete_member(self, member_id: int) -> None:
        await self._execute("DELETE FROM members WHERE id = ?", (member_id,))

    async def upsert_member_guild(
        self, member_id: int, guild_id: int, display_name: str | None = None, avatar_url: str | None = None
    ) -> None:
        await self._execute(
            """
            INSERT INTO member_guild (member, guild, display_name, avatar_url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(member, guild) DO UPDATE SET
                display_name = COALESCE(exCLUDED.display_name, member_guild.display_name),
                avatar_url = COALESCE(EXCLUDED.avatar_url, member_guild.avatar_url)
            """,
            (member_id, guild_id, display_name, avatar_url),
        )

    # ── Groups ───────────────────────────────────────────────────────────

    async def get_groups(self, system_id: int) -> list[Group]:
        order = dialect.order_name("name")
        rows = await self._fetchall(
            f"SELECT * FROM groups WHERE system = ? ORDER BY {order}",
            (system_id,),
        )
        return [self._row_to_group(r) for r in rows]

    async def get_group(self, group_id: int | str) -> Group | None:
        if isinstance(group_id, str):
            row = await self._fetchone("SELECT * FROM groups WHERE hid = ?", (group_id,))
        else:
            row = await self._fetchone("SELECT * FROM groups WHERE id = ?", (group_id,))
        return self._row_to_group(row) if row else None

    async def find_group(self, system_id: int, query: str) -> Group | None:
        groups = await self.get_groups(system_id)
        query_lower = query.lower()
        for g in groups:
            if g.hid == query_lower or g.name.lower() == query_lower:
                return g
            if g.display_name and g.display_name.lower() == query_lower:
                return g
        for g in groups:
            if query_lower in g.name.lower():
                return g
        return None

    async def create_group(self, system_id: int, name: str) -> Group:
        hid = await self._unique_hid("groups")
        gid = await self._insert_id(
            "INSERT INTO groups (hid, system, name) VALUES (?, ?, ?)",
            (hid, system_id, name),
        )
        group = await self.get_group(gid)
        assert group is not None
        return group

    async def update_group(self, group_id: int, **fields: Any) -> None:
        allowed = {
            "name", "display_name", "description", "icon", "color",
            "description_privacy", "icon_privacy", "visibility",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return
        cols = ", ".join(f"{k} = ?" for k in updates)
        await self._execute(
            f"UPDATE groups SET {cols} WHERE id = ?",
            (*updates.values(), group_id),
        )

    async def delete_group(self, group_id: int) -> None:
        await self._execute("DELETE FROM groups WHERE id = ?", (group_id,))

    async def add_group_member(self, group_id: int, member_id: int) -> None:
        sql = dialect.insert_ignore("group_members", "group_id, member", "?, ?")
        await self._execute(sql, (group_id, member_id))

    async def remove_group_member(self, group_id: int, member_id: int) -> None:
        await self._execute(
            "DELETE FROM group_members WHERE group_id = ? AND member = ?",
            (group_id, member_id),
        )

    async def get_group_members(self, group_id: int) -> list[Member]:
        order = dialect.order_name("m.name")
        rows = await self._fetchall(
            f"""
            SELECT m.* FROM members m
            JOIN group_members gm ON gm.member = m.id
            WHERE gm.group_id = ?
            ORDER BY {order}
            """,
            (group_id,),
        )
        return [Member.from_row(r) for r in rows]

    # ── Switches ─────────────────────────────────────────────────────────

    async def register_switch(self, system_id: int, member_ids: list[int]) -> Switch:
        switch_id = await self._insert_id(
            "INSERT INTO switches (system) VALUES (?)",
            (system_id,),
        )
        for mid in member_ids:
            await self._execute(
                "INSERT INTO switch_members (switch, member) VALUES (?, ?)",
                (switch_id, mid),
            )
        return await self.get_switch(switch_id)  # type: ignore

    async def get_switch(self, switch_id: int) -> Switch | None:
        row = await self._fetchone("SELECT * FROM switches WHERE id = ?", (switch_id,))
        if not row:
            return None
        members = await self._fetchall(
            "SELECT member FROM switch_members WHERE switch = ?", (switch_id,)
        )
        return Switch(
            id=row["id"],
            system=row["system"],
            timestamp=row["timestamp"],
            members=[m["member"] for m in members],
        )

    async def get_latest_switch(self, system_id: int) -> Switch | None:
        row = await self._fetchone(
            "SELECT id FROM switches WHERE system = ? ORDER BY timestamp DESC LIMIT 1",
            (system_id,),
        )
        return await self.get_switch(row["id"]) if row else None

    async def delete_latest_switch(self, system_id: int) -> bool:
        row = await self._fetchone(
            "SELECT id FROM switches WHERE system = ? ORDER BY timestamp DESC LIMIT 1",
            (system_id,),
        )
        if not row:
            return False
        await self._execute("DELETE FROM switches WHERE id = ?", (row["id"],))
        return True

    async def delete_all_switches(self, system_id: int) -> int:
        rows = await self._fetchall(
            "SELECT id FROM switches WHERE system = ?", (system_id,)
        )
        for r in rows:
            await self._execute("DELETE FROM switches WHERE id = ?", (r["id"],))
        return len(rows)

    async def get_switch_history(self, system_id: int, limit: int = 20) -> list[Switch]:
        rows = await self._fetchall(
            "SELECT id FROM switches WHERE system = ? ORDER BY timestamp DESC LIMIT ?",
            (system_id, limit),
        )
        switches = []
        for r in rows:
            s = await self.get_switch(r["id"])
            if s:
                switches.append(s)
        return switches

    # ── Proxy / Messages ─────────────────────────────────────────────────

    async def get_proxy_members(self, uid: int, guild_id: int | None) -> list[Member]:
        system = await self.get_system_by_account(uid)
        if not system:
            return []
        return await self.get_members(system.id, guild_id)

    async def get_message_context(
        self, uid: int, guild_id: int | None, channel_id: int
    ) -> MessageContext:
        ctx = MessageContext()
        system = await self.get_system_by_account(uid)
        if not system:
            return ctx

        ctx.system_id = system.id
        ctx.system_tag = system.tag
        ctx.system_avatar = system.avatar_url

        if guild_id:
            sg = await self._fetchone(
                "SELECT * FROM system_guild WHERE system = ? AND guild = ?",
                (system.id, guild_id),
            )
            if sg:
                ctx.proxy_enabled = bool(sg["proxy_enabled"])
                ctx.autoproxy_mode = AutoproxyMode(sg["autoproxy_mode"])
                ctx.autoproxy_member = sg["autoproxy_member"]

            server = await self._fetchone("SELECT * FROM servers WHERE id = ?", (guild_id,))
            if server:
                blacklist = self._parse_id_list(server.get("blacklist"))
                log_blacklist = self._parse_id_list(server.get("log_blacklist"))
                ctx.in_blacklist = channel_id in blacklist
                ctx.in_log_blacklist = channel_id in log_blacklist
                ctx.log_channel = server["log_channel"]
                ctx.log_cleanup_enabled = bool(server["log_cleanup"])
            else:
                ctx.proxy_enabled = sg["proxy_enabled"] if sg else True

        last_msg = await self._fetchone(
            """
            SELECT mid, member FROM messages
            WHERE sender = ? AND channel = ?
            ORDER BY mid DESC LIMIT 1
            """,
            (uid, channel_id),
        )
        if last_msg:
            ctx.last_message = last_msg["mid"]
            ctx.last_message_member = last_msg["member"]

        latest = await self.get_latest_switch(system.id)
        if latest:
            ctx.last_switch = latest.id
            ctx.last_switch_members = latest.members
            ctx.last_switch_timestamp = latest.timestamp

        return ctx

    async def add_message(
        self,
        mid: int,
        channel: int,
        guild: int | None,
        member: int,
        sender: int,
        original_mid: int | None = None,
    ) -> None:
        sql = dialect.insert_replace(
            "messages",
            "mid, channel, guild, member, sender, original_mid",
            "?, ?, ?, ?, ?, ?",
        )
        await self._execute(sql, (mid, channel, guild, member, sender, original_mid))

    async def get_message(self, mid: int) -> dict | None:
        return await self._fetchone("SELECT * FROM messages WHERE mid = ?", (mid,))

    async def delete_message_record(self, mid: int) -> None:
        await self._execute("DELETE FROM messages WHERE mid = ?", (mid,))

    # ── Guild / Server settings ──────────────────────────────────────────

    async def upsert_system_guild(
        self,
        system_id: int,
        guild_id: int,
        proxy_enabled: bool | None = None,
        autoproxy_mode: AutoproxyMode | None = None,
        autoproxy_member: int | None = None,
    ) -> None:
        existing = await self._fetchone(
            "SELECT * FROM system_guild WHERE system = ? AND guild = ?",
            (system_id, guild_id),
        )
        if existing:
            updates = []
            params: list[Any] = []
            if proxy_enabled is not None:
                updates.append("proxy_enabled = ?")
                params.append(int(proxy_enabled))
            if autoproxy_mode is not None:
                updates.append("autoproxy_mode = ?")
                params.append(int(autoproxy_mode))
            if autoproxy_member is not None:
                updates.append("autoproxy_member = ?")
                params.append(autoproxy_member)
            if updates:
                params.extend([system_id, guild_id])
                await self._execute(
                    f"UPDATE system_guild SET {', '.join(updates)} WHERE system = ? AND guild = ?",
                    tuple(params),
                )
        else:
            await self._execute(
                """
                INSERT INTO system_guild (system, guild, proxy_enabled, autoproxy_mode, autoproxy_member)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    system_id,
                    guild_id,
                    int(proxy_enabled if proxy_enabled is not None else True),
                    int(autoproxy_mode or AutoproxyMode.OFF),
                    autoproxy_member,
                ),
            )

    async def ensure_server(self, guild_id: int) -> None:
        sql = dialect.insert_ignore("servers", "id", "?")
        await self._execute(sql, (guild_id,))

    async def update_server(self, guild_id: int, **fields: Any) -> None:
        await self.ensure_server(guild_id)
        allowed = {"log_channel", "log_blacklist", "blacklist", "log_cleanup"}
        updates: dict[str, Any] = {}
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k in ("log_blacklist", "blacklist") and isinstance(v, list):
                updates[k] = self._encode_id_list(v)
            elif k == "log_cleanup":
                updates[k] = int(v)
            elif v is not None:
                updates[k] = v
        if not updates:
            return
        cols = ", ".join(f"{k} = ?" for k in updates)
        await self._execute(
            f"UPDATE servers SET {cols} WHERE id = ?",
            (*updates.values(), guild_id),
        )

    async def get_server(self, guild_id: int) -> dict | None:
        await self.ensure_server(guild_id)
        return await self._fetchone("SELECT * FROM servers WHERE id = ?", (guild_id,))

    # ── Webhooks ─────────────────────────────────────────────────────────

    async def get_webhook(self, channel_id: int) -> dict | None:
        return await self._fetchone(
            "SELECT * FROM webhooks WHERE channel = ?", (channel_id,)
        )

    async def save_webhook(self, channel_id: int, webhook_id: int, token: str) -> None:
        sql = dialect.insert_replace("webhooks", "channel, webhook, token", "?, ?, ?")
        await self._execute(sql, (channel_id, webhook_id, token))

    async def delete_webhook(self, channel_id: int) -> None:
        await self._execute("DELETE FROM webhooks WHERE channel = ?", (channel_id,))

    # ── Stats ────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, int]:
        systems = await self._fetchone("SELECT COUNT(*) AS c FROM systems")
        members = await self._fetchone("SELECT COUNT(*) AS c FROM members")
        messages = await self._fetchone("SELECT COUNT(*) AS c FROM messages")
        switches = await self._fetchone("SELECT COUNT(*) AS c FROM switches")
        return {
            "systems": systems["c"] if systems else 0,
            "members": members["c"] if members else 0,
            "messages": messages["c"] if messages else 0,
            "switches": switches["c"] if switches else 0,
        }

    # ── Import/Export ────────────────────────────────────────────────────

    async def export_system(self, system_id: int) -> dict:
        system = await self.get_system(system_id)
        members = await self.get_members(system_id)
        groups = await self.get_groups(system_id)
        return {
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "system": {
                "hid": system.hid,
                "name": system.name,
                "description": system.description,
                "tag": system.tag,
                "avatar_url": system.avatar_url,
                "color": system.color,
                "ui_tz": system.ui_tz,
            },
            "members": [
                {
                    "hid": m.hid,
                    "name": m.name,
                    "display_name": m.display_name,
                    "pronouns": m.pronouns,
                    "description": m.description,
                    "birthday": m.birthday,
                    "color": m.color,
                    "avatar_url": m.avatar_url,
                    "proxy_tags": [t.to_dict() for t in m.proxy_tags],
                    "keep_proxy": m.keep_proxy,
                }
                for m in members
            ],
            "groups": [
                {
                    "hid": g.hid,
                    "name": g.name,
                    "display_name": g.display_name,
                    "description": g.description,
                    "icon": g.icon,
                    "color": g.color,
                    "members": [m.hid for m in await self.get_group_members(g.id)],
                }
                for g in groups
            ],
        }

    async def import_system_data(self, uid: int, data: dict, merge: bool = False) -> System:
        system_data = data.get("system") or data
        existing = await self.get_system_by_account(uid)

        if existing and not merge:
            await self.delete_system(existing.id)

        if existing and merge:
            system = existing
        else:
            system = await self.create_system(uid, system_data.get("name"))
            await self.update_system(
                system.id,
                description=system_data.get("description"),
                tag=system_data.get("tag"),
                avatar_url=system_data.get("avatar_url") or system_data.get("avatar"),
                color=system_data.get("color"),
                ui_tz=system_data.get("ui_tz", "UTC"),
            )

        member_map: dict[str, int] = {}
        for mdata in data.get("members", []):
            member = await self.create_member(system.id, mdata["name"])
            await self.update_member(
                member.id,
                display_name=mdata.get("display_name") or mdata.get("displayName"),
                pronouns=mdata.get("pronouns"),
                description=mdata.get("description"),
                birthday=mdata.get("birthday"),
                color=mdata.get("color"),
                avatar_url=mdata.get("avatar_url") or mdata.get("avatar"),
                proxy_tags=[
                    ProxyTag.from_dict(t) for t in mdata.get("proxy_tags", mdata.get("proxyTags", []))
                ],
                keep_proxy=mdata.get("keep_proxy", mdata.get("keepProxy", False)),
            )
            member_map[mdata.get("hid", member.hid)] = member.id

        for gdata in data.get("groups", []):
            group = await self.create_group(system.id, gdata["name"])
            await self.update_group(
                group.id,
                display_name=gdata.get("display_name") or gdata.get("displayName"),
                description=gdata.get("description"),
                icon=gdata.get("icon"),
                color=gdata.get("color"),
            )
            for mref in gdata.get("members", []):
                mid = member_map.get(mref)
                if mid:
                    await self.add_group_member(group.id, mid)

        return await self.get_system(system.id)  # type: ignore

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _unique_hid(self, table: str) -> str:
        for _ in range(100):
            hid = generate_hid()
            row = await self._fetchone(f"SELECT 1 FROM {table} WHERE hid = ?", (hid,))
            if not row:
                return hid
        raise RuntimeError("Failed to generate unique HID")

    def _row_to_system(self, row: dict) -> System:
        return System(
            id=row["id"],
            hid=row["hid"],
            name=row.get("name"),
            description=row.get("description"),
            tag=row.get("tag"),
            avatar_url=row.get("avatar_url"),
            token=row.get("token"),
            color=row.get("color"),
            created=row.get("created"),
            ui_tz=row.get("ui_tz", "UTC"),
            pings_enabled=bool(row.get("pings_enabled", 1)),
            description_privacy=PrivacyLevel(row.get("description_privacy", 2)),
            member_list_privacy=PrivacyLevel(row.get("member_list_privacy", 2)),
            front_privacy=PrivacyLevel(row.get("front_privacy", 2)),
            front_history_privacy=PrivacyLevel(row.get("front_history_privacy", 2)),
            group_list_privacy=PrivacyLevel(row.get("group_list_privacy", 2)),
        )

    def _row_to_group(self, row: dict) -> Group:
        return Group(
            id=row["id"],
            hid=row["hid"],
            system=row["system"],
            name=row["name"],
            display_name=row.get("display_name"),
            description=row.get("description"),
            icon=row.get("icon"),
            color=row.get("color"),
            created=row.get("created"),
            description_privacy=PrivacyLevel(row.get("description_privacy", 2)),
            icon_privacy=PrivacyLevel(row.get("icon_privacy", 2)),
            visibility=PrivacyLevel(row.get("visibility", 2)),
        )