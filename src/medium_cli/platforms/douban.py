"""豆瓣适配器 — 上游 Marvae/douban-cli（npm: @marvae24/douban-cli，二进制 douban）。

命令面实测（2026-10）：`douban search <kw> [--json]` 查电影/剧集，`douban book search <kw>` 查图书，
`douban hot --json` 热门电影，`douban movie <id-or-title>` / `douban book info <q>` 看详情。
全公开 API，无需登录。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "douban")

COMMANDS = {
    "search": lambda o: (["book", "search"] if o.get("type") == "book" else ["search"])
    + [o["q"], "-n", str(o.get("max", 20)), "--json"],
    "hot": lambda o: ["hot", "--json"],
    "read": lambda o: (["book", "info"] if o.get("type") == "book" else ["movie"]) + [o["id"]],
}


def _media(d: object, title_keys=("title", "name")) -> list:
    return [make_item("douban", r, kind=pick(r, "type", "kind", default="media"),
                      title=title_keys, url=("url",), id_keys=("id",),
                      author=("author", "creator"))
            for r in rows(d) if r.get("title")]


PARSERS = {
    "search": _media,
    "hot": _media,  # 热门电影条目同样带 title
}