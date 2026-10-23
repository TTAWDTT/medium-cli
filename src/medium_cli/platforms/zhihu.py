"""知乎适配器 — 上游 BAIGUANGMEI/zhihu-cli（即 zhihu-cli-plus，二进制 zhihu，包 pyzhihu-cli）。

命令面实测（2026-10）：search / hot / feed / answer 均支持 --json；内容读取用 `answer`（无 read 子命令）。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "zhihu")

COMMANDS = {
    "login": lambda o: ["login", "--qrcode"],
    "search": lambda o: ["search", o["q"], "-l", str(o.get("max", 10)), "--json"]
    + (["-t", o["type"]] if o.get("type") else []),
    "hot": lambda o: ["hot", "-l", str(o.get("max", 20)), "--json"],
    "feed": lambda o: ["feed", "-l", str(o.get("max", 10)), "--json"],
    "read": lambda o: ["answer", o["id"]] + (["-c"] if o.get("comments") else []),
}


def _search_rows(d: object) -> list:
    """search 的结果是 {data:[{type, object:{...}}]}，object 里可能是 question/article 等。"""
    out = []
    for r in rows(d, ("data",)):
        if not isinstance(r, dict):
            continue
        row = r.get("object") if isinstance(r.get("object"), dict) else r
        if isinstance(row, dict) and isinstance(row.get("question"), dict):
            row = row["question"]
        kind = row.get("type") if isinstance(row, dict) else None
        out.append((row, kind or r.get("type")))
    return out


_ZH = {
    "question": "question", "article": "article", "pin": "pin",
    "topic": "topic", "people": "person", "video": "video", "zvideo": "video",
}


def _zhihu_item(row: dict, kind: str | None) -> object:
    from ..schema import Item
    kind = _ZH.get(str(kind), "") or "post"
    if kind == "post" and pick(row, "id", "question_id"):
        kind = "question"
    return make_item("zhihu", row, kind=kind, title=("title", "name", "excerpt"),
                     url=("url", "link"), id_keys=("id", "question_id"),
                     author=("author", "creator"))


def _hot_items(d: object) -> list:
    out = []
    for r in rows(d, ("data",)):
        if not isinstance(r, dict) or not isinstance(r.get("question"), dict):
            continue
        q = r["question"]
        it = _zhihu_item(q, "question")
        it.extra["hot_answer_count"] = len(r.get("answers") or [])
        out.append(it)
    return out


PARSERS = {
    "hot": _hot_items,
    "search": lambda d: [
        _zhihu_item(row, kind)
        for row, kind in _search_rows(d)
        if isinstance(row, dict) and str(kind) != "hot_timing" and pick(row, "title", "name", "excerpt")
    ],
    "feed": lambda d: [
        _zhihu_item(row, kind)
        for row, kind in _search_rows(d)
        if isinstance(row, dict) and pick(row, "title", "name", "excerpt")
    ],
}