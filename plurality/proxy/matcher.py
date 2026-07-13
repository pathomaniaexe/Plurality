"""Proxy matching including autoproxy modes."""

from __future__ import annotations

import time

from plurality.constants import AUTOPROXY_ESCAPE, LATCH_EXPIRY_HOURS, AutoproxyMode
from plurality.db.models import Member, MessageContext, ProxyMatch
from plurality.proxy.parser import ProxyTagParser
from plurality.utils.ids import snowflake_to_datetime


class ProxyMatcher:
    def __init__(self):
        self.parser = ProxyTagParser()

    def try_match(
        self,
        ctx: MessageContext,
        members: list[Member],
        content: str,
        has_attachments: bool,
        allow_autoproxy: bool = True,
    ) -> ProxyMatch | None:
        tag_match = self._try_match_tags(members, content, has_attachments)
        if tag_match:
            return tag_match

        if allow_autoproxy:
            return self._try_match_autoproxy(ctx, members, content)

        return None

    def _try_match_tags(
        self, members: list[Member], content: str, has_attachments: bool
    ) -> ProxyMatch | None:
        match = self.parser.try_match(members, content)
        if not match:
            return None
        if has_attachments or match.content.strip():
            return match
        return None

    def _try_match_autoproxy(
        self, ctx: MessageContext, members: list[Member], content: str
    ) -> ProxyMatch | None:
        if content.startswith(AUTOPROXY_ESCAPE):
            return None

        member: Member | None = None
        member_map = {m.id: m for m in members}

        if ctx.autoproxy_mode == AutoproxyMode.MEMBER and ctx.autoproxy_member:
            member = member_map.get(ctx.autoproxy_member)
        elif ctx.autoproxy_mode == AutoproxyMode.FRONT and ctx.last_switch_members:
            member = member_map.get(ctx.last_switch_members[0])
        elif (
            ctx.autoproxy_mode == AutoproxyMode.LATCH
            and ctx.last_message_member
            and not self._is_latch_expired(ctx.last_message)
        ):
            member = member_map.get(ctx.last_message_member)

        if not member:
            return None

        proxy_tags = member.proxy_tags[0] if member.proxy_tags else None
        return ProxyMatch(
            member=member,
            content=content,
            proxy_tags=proxy_tags,
            is_autoproxy=True,
        )

    def _is_latch_expired(self, message_id: int | None) -> bool:
        if message_id is None:
            return True
        ts = snowflake_to_datetime(message_id)
        return (time.time() - ts) > (LATCH_EXPIRY_HOURS * 3600)