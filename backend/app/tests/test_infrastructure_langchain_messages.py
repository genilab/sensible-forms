from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.infrastructure.llm.langchain_messages import (
    ensure_last_human_message,
    to_langchain_messages,
)


def test_to_langchain_messages_from_string_creates_human_message():
    out = to_langchain_messages("hello")
    assert len(out) == 1
    assert isinstance(out[0], HumanMessage)
    assert out[0].content == "hello"


def test_to_langchain_messages_from_list_of_dicts_converts_roles_and_defaults():
    out = to_langchain_messages(
        [
            {"role": "system", "content": "rules"},
            {"role": "assistant", "content": "hi"},
            {"role": "ai", "content": "yo"},
            {"role": "user", "content": "u"},
            {"content": "missing-role-defaults-to-user"},
            {"role": "unknown", "content": "also-user"},
            {"role": None, "content": None},
        ]
    )

    assert [type(m) for m in out] == [
        SystemMessage,
        AIMessage,
        AIMessage,
        HumanMessage,
        HumanMessage,
        HumanMessage,
        HumanMessage,
    ]
    assert out[0].content == "rules"
    assert out[1].content == "hi"
    assert out[2].content == "yo"
    assert out[3].content == "u"
    assert out[4].content == "missing-role-defaults-to-user"
    assert out[5].content == "also-user"
    assert out[6].content == ""  # content None coerces to empty string


def test_to_langchain_messages_mixed_list_keeps_non_dict_items_as_is():
    existing = SystemMessage(content="s")
    sentinel = object()

    out = to_langchain_messages([existing, sentinel, {"role": "user", "content": "u"}])
    assert out[0] is existing
    assert out[1] is sentinel
    assert isinstance(out[2], HumanMessage)
    assert out[2].content == "u"


def test_to_langchain_messages_non_list_non_str_falls_back_to_stringified_human_message():
    out = to_langchain_messages(123)
    assert len(out) == 1
    assert isinstance(out[0], HumanMessage)
    assert out[0].content == "123"


def test_ensure_last_human_message_returns_same_list_when_already_last_human():
    msgs = [SystemMessage(content="s"), HumanMessage(content="u")]
    out = ensure_last_human_message(msgs)
    assert out is msgs
    assert isinstance(out[-1], HumanMessage)


def test_ensure_last_human_message_moves_last_human_to_end_when_needed():
    # Last message is AI, but there's a human earlier.
    h1 = HumanMessage(content="first-user")
    a1 = AIMessage(content="assistant")
    s1 = SystemMessage(content="system")

    msgs = [h1, a1, s1]
    out = ensure_last_human_message(msgs)

    assert out is not msgs
    assert out[-1] is h1
    assert out[:-1] == [a1, s1]


@pytest.mark.parametrize(
    "last_user_prompt,fallback_prompt,expected",
    [
        ("please respond", "", "please respond"),
        ("  please respond  ", "fallback", "  please respond  "),
        (None, "fallback", "fallback"),
        ("   ", "fallback", "fallback"),
    ],
)
def test_ensure_last_human_message_appends_when_no_human_exists(last_user_prompt, fallback_prompt, expected):
    msgs = [SystemMessage(content="s"), AIMessage(content="a")]
    out = ensure_last_human_message(msgs, last_user_prompt=last_user_prompt, fallback_prompt=fallback_prompt)

    assert len(out) == 3
    assert isinstance(out[-1], HumanMessage)
    assert out[-1].content == expected
