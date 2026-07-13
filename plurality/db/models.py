"""Data models for Plurality."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from plurality.constants import AutoproxyMode, PrivacyLevel


@dataclass
class ProxyTag:
    prefix: str = ""
    suffix: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProxyTag:
        return cls(prefix=data.get("prefix") or "", suffix=data.get("suffix") or "")

    def to_dict(self) -> dict[str, str]:
        return {"prefix": self.prefix, "suffix": self.suffix}

    @property
    def proxy_string(self) -> str:
        return f"{self.prefix}{self.suffix}"


@dataclass
class System:
    id: int
    hid: str
    name: str | None = None
    description: str | None = None
    tag: str | None = None
    avatar_url: str | None = None
    token: str | None = None
    color: str | None = None
    created: datetime | None = None
    ui_tz: str = "UTC"
    pings_enabled: bool = True
    description_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    member_list_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    front_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    front_history_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    group_list_privacy: PrivacyLevel = PrivacyLevel.PUBLIC


@dataclass
class Member:
    id: int
    hid: str
    system: int
    name: str
    color: str | None = None
    avatar_url: str | None = None
    display_name: str | None = None
    birthday: str | None = None
    pronouns: str | None = None
    description: str | None = None
    proxy_tags: list[ProxyTag] = field(default_factory=list)
    keep_proxy: bool = False
    created: datetime | None = None
    member_visibility: PrivacyLevel = PrivacyLevel.PUBLIC
    description_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    avatar_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    name_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    birthday_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    pronoun_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    metadata_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    message_count: int = 0
    guild_display_name: str | None = None
    guild_avatar_url: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Member:
        tags_raw = row.get("proxy_tags", "[]")
        if isinstance(tags_raw, str):
            tags_data = json.loads(tags_raw) if tags_raw else []
        elif isinstance(tags_raw, list):
            tags_data = tags_raw
        else:
            tags_data = tags_raw or []
        return cls(
            id=row["id"],
            hid=row["hid"],
            system=row["system"],
            name=row["name"],
            color=row.get("color"),
            avatar_url=row.get("avatar_url"),
            display_name=row.get("display_name"),
            birthday=row.get("birthday"),
            pronouns=row.get("pronouns"),
            description=row.get("description"),
            proxy_tags=[ProxyTag.from_dict(t) for t in tags_data],
            keep_proxy=bool(row.get("keep_proxy")),
            created=row.get("created"),
            member_visibility=PrivacyLevel(row.get("member_visibility", 2)),
            description_privacy=PrivacyLevel(row.get("description_privacy", 2)),
            avatar_privacy=PrivacyLevel(row.get("avatar_privacy", 2)),
            name_privacy=PrivacyLevel(row.get("name_privacy", 2)),
            birthday_privacy=PrivacyLevel(row.get("birthday_privacy", 2)),
            pronoun_privacy=PrivacyLevel(row.get("pronoun_privacy", 2)),
            metadata_privacy=PrivacyLevel(row.get("metadata_privacy", 2)),
            message_count=row.get("message_count", 0),
            guild_display_name=row.get("guild_display_name"),
            guild_avatar_url=row.get("guild_avatar_url"),
        )

    def proxy_name(self, system_tag: str | None = None) -> str:
        base = self.guild_display_name or self.display_name or self.name
        if system_tag:
            return f"{base}{system_tag}"
        return base

    def proxy_avatar(self) -> str | None:
        return self.guild_avatar_url or self.avatar_url


@dataclass
class Group:
    id: int
    hid: str
    system: int
    name: str
    display_name: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    created: datetime | None = None
    description_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    icon_privacy: PrivacyLevel = PrivacyLevel.PUBLIC
    visibility: PrivacyLevel = PrivacyLevel.PUBLIC


@dataclass
class Switch:
    id: int
    system: int
    timestamp: datetime
    members: list[int] = field(default_factory=list)


@dataclass
class MessageContext:
    system_id: int | None = None
    log_channel: int | None = None
    in_blacklist: bool = False
    in_log_blacklist: bool = False
    log_cleanup_enabled: bool = False
    proxy_enabled: bool = True
    autoproxy_mode: AutoproxyMode = AutoproxyMode.OFF
    autoproxy_member: int | None = None
    last_message: int | None = None
    last_message_member: int | None = None
    last_switch: int | None = None
    last_switch_members: list[int] = field(default_factory=list)
    last_switch_timestamp: datetime | None = None
    system_tag: str | None = None
    system_avatar: str | None = None


@dataclass
class ProxyMatch:
    member: Member
    content: str
    proxy_tags: ProxyTag | None = None
    is_autoproxy: bool = False