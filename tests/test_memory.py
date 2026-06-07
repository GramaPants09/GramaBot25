"""Tests for the SQLite-backed agent memory."""
import json
import os

from cogs.AI.memory import Memory


def test_add_and_history(tmp_path):
    db = str(tmp_path / "brain.db")
    mem = Memory(db_path=db)
    mem.add_turn("u1", "c1", "user", "hi")
    mem.add_turn("u1", "c1", "assistant", "oi")
    # different channel is isolated
    mem.add_turn("u1", "c2", "user", "elsewhere")

    hist = mem.history("u1", "c1")
    assert hist == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "oi"},
    ]
    assert mem.history("u1", "c2") == [{"role": "user", "content": "elsewhere"}]


def test_history_limit_keeps_most_recent(tmp_path):
    mem = Memory(db_path=str(tmp_path / "b.db"))
    for i in range(10):
        mem.add_turn("u", "c", "user", f"m{i}")
    hist = mem.history("u", "c", limit=3)
    assert [h["content"] for h in hist] == ["m7", "m8", "m9"]


def test_summary_roundtrip(tmp_path):
    mem = Memory(db_path=str(tmp_path / "b.db"))
    assert mem.get_summary("u", "c") is None
    mem.set_summary("u", "c", "they like turtles")
    assert mem.get_summary("u", "c") == "they like turtles"
    mem.set_summary("u", "c", "updated")
    assert mem.get_summary("u", "c") == "updated"


def test_import_json(tmp_path):
    src = tmp_path / "memory.json"
    src.write_text(json.dumps({"448": ["User: hello", "well hello there", "User: bye"]}))
    db = str(tmp_path / "b.db")
    n = Memory.import_json(str(src), db)
    assert n == 3
    mem = Memory(db_path=db)
    hist = mem.history("448", "legacy")
    assert hist == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "well hello there"},
        {"role": "user", "content": "bye"},
    ]


def test_import_json_missing_file_is_noop(tmp_path):
    db = str(tmp_path / "b.db")
    n = Memory.import_json(str(tmp_path / "nope.json"), db)
    assert n == 0
    assert os.path.exists(db)
