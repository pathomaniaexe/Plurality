"""Proxy tag parsing — compatible with PluralKit tag matching."""

from __future__ import annotations

from plurality.db.models import Member, ProxyMatch, ProxyTag
from plurality.utils.discord_utils import extract_leading_mention


class ProxyTagParser:
    def try_match(self, members: list[Member], content: str | None) -> ProxyMatch | None:
        if content is None:
            return None

        leading_mention, input_text = extract_leading_mention(content)

        tags: list[tuple[ProxyTag, Member]] = []
        for member in members:
            for tag in member.proxy_tags:
                tags.append((tag, member))

        tags.sort(key=lambda p: len(p[0].proxy_string), reverse=True)

        for tag, member in tags:
            if tag.prefix is None and tag.suffix is None:
                continue

            inner = self._try_match_inner(input_text, tag)
            if inner is None:
                continue

            if inner.strip() == "\ufe0f":
                continue

            if leading_mention:
                inner = f"{leading_mention} {inner}"

            return ProxyMatch(member=member, content=inner, proxy_tags=tag)

        return None

    def _try_match_inner(self, input_text: str, tag: ProxyTag) -> str | None:
        prefix = tag.prefix or ""
        suffix = tag.suffix or ""

        is_match = (
            len(input_text) >= len(prefix) + len(suffix)
            and input_text.startswith(prefix)
            and input_text.endswith(suffix)
        )

        if not is_match:
            trimmed = input_text.strip()
            contentless = prefix.rstrip() + suffix.lstrip()
            if trimmed == contentless:
                return ""
            return None

        return input_text[len(prefix) : len(input_text) - len(suffix)]