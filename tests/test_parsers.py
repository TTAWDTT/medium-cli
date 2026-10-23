"""parser 层断言：fixtures/{key}_{verb}.json → 归一化 Item 列表。fixtures 目录自动收集。"""

import json
from pathlib import Path

import pytest

from medium_cli import platforms as P
from medium_cli.adapter import make_item, pick, rows, try_json

FIX = Path(__file__).parent / "fixtures"


def _fixtures() -> list[tuple[str, str, Path]]:
    cases = []
    for f in sorted(FIX.glob("*.json")):
        stem = f.stem  # "{key}_{verb}"
        if "_" not in stem:
            continue
        key, verb = stem.rsplit("_", 1)
        cases.append((key, verb, f))
    return cases


@pytest.mark.parametrize("key,verb,path", _fixtures())
def test_fixture_parses(key, verb, path):
    mod = P.ADAPTERS.get(key)
    assert mod is not None, f"平台 {key} 未适配"
    parser = (getattr(mod, "PARSERS", {}) or {}).get(verb)
    assert parser is not None, f"{key}/{verb} 缺 parser"

    payload = json.loads(path.read_text(encoding="utf-8"))
    items = parser(payload) or []
    assert items, f"{key}/{verb} 解析出空结果"
    for it in items:
        assert it.platform == key
        assert it.title.strip(), f"{key}/{verb} 有条目缺 title: {it}"


# --------------------------------------------------------------------------- 工具函数单测


def test_pick_aliases():
    row = {"title": "A", "content": "B"}
    assert pick(row, "text", "title") == "A"
    assert pick(row, "text") == ""


def test_rows_variants():
    assert rows([{"a": 1}]) and rows({"items": [{"a": 1}]}) and rows({"data": {"rows": [{"a": 1}]}})
    assert rows(None) == []
    assert rows({"items": [1, "x"]}) == []  # 非 dict 行被过滤


def test_try_json_recovers_embedded():
    assert try_json('{"a": 1}') == {"a": 1}
    assert try_json('LOG line\n{"a": 2}') == {"a": 2}
    assert try_json("no json here") is None


def test_make_item_extracts_nested_author():
    it = make_item("xhs", {"note_id": "xyz", "title": "T", "user": {"nickname": "阿布"}, "url": "http://x"})
    assert it.id == "xyz"
    assert it.author == "阿布"