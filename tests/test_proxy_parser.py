"""Tests for proxy tag parsing."""

import pytest

from plurality.db.models import Member, ProxyTag
from plurality.proxy.parser import ProxyTagParser


def make_member(name: str, tags: list[tuple[str, str]]) -> Member:
    return Member(
        id=1,
        hid="abc123",
        system=1,
        name=name,
        proxy_tags=[ProxyTag(prefix=p, suffix=s) for p, s in tags],
    )


@pytest.fixture
def parser():
    return ProxyTagParser()


def test_bracket_tags(parser):
    members = [make_member("Luna", [("[", "]")])]
    match = parser.try_match(members, "[hello world]")
    assert match is not None
    assert match.content == "hello world"
    assert match.member.name == "Luna"


def test_curly_tags(parser):
    members = [make_member("Sol", [("{", "}")])]
    match = parser.try_match(members, "{test}")
    assert match is not None
    assert match.content == "test"


def test_prefix_suffix_tags(parser):
    members = [make_member("Kai", [("V|", "|V")])]
    match = parser.try_match(members, "V|message|V")
    assert match is not None
    assert match.content == "message"


def test_specificity_order(parser):
    members = [make_member("A", [("[", "]")]), make_member("B", [("[[", "]]")])]
    match = parser.try_match(members, "[[inner]]")
    assert match is not None
    assert match.member.name == "B"


def test_no_match(parser):
    members = [make_member("A", [("[", "]")])]
    assert parser.try_match(members, "no tags here") is None


def test_empty_attachment_proxy(parser):
    members = [make_member("A", [("[", "]")])]
    match = parser.try_match(members, "[]")
    assert match is not None
    assert match.content == ""