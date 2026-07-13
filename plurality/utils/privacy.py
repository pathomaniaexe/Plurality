"""Privacy level helpers."""

from __future__ import annotations

from enum import Enum, auto
from typing import TypeVar

from plurality.constants import PrivacyLevel

T = TypeVar("T")


class LookupContext(Enum):
    PUBLIC = auto()
    OWNER = auto()


def can_access(level: PrivacyLevel, ctx: LookupContext) -> bool:
    return level == PrivacyLevel.PUBLIC or ctx == LookupContext.OWNER


def get_privacy_value(
    level: PrivacyLevel,
    ctx: LookupContext,
    value: T,
    fallback: T | None = None,
) -> T | None:
    if can_access(level, ctx):
        return value
    return fallback


def level_name(level: PrivacyLevel) -> str:
    return "public" if level == PrivacyLevel.PUBLIC else "private"