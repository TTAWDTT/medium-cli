"""B站适配器 — 上游 public-clis/bilibili-cli（二进制 bili，包 bilibili-cli）。

命令面实测（2026-10）：hot/search/feed/video 支持 --json；内容读取用 `video`。
hot 输出 {data:{items:[...]}}，search 输出 {data:[...]}，两种形态都处理。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "bili")

COMMANDS = {
    "login": lambda o: ["login"],
    "search": lambda o: ["search", o["q"], "--type", o.get("type") or "video",
                         "-n", str(o.get("max", 20)), "--json"],
    "hot": lambda o: ["hot", "-n", str(o.get("max", 20)), "--json"],
    "feed": lambda o: ["feed", "--json"],
    "read": lambda o: ["video", o["id"]] + (["-c"] if o.get("comments") else []),
}


def _rows(d: object) -> list:
    data = d.get("data") if isinstance(d, dict) else d
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    if isinstance(data, list):
        return data
    return rows(d)


_FIELDS = dict(url=("url", "link"), id_keys=("bvid", "aid", "id"))


def _videos(d: object, title_keys=("title", "name")) -> list:
    return [make_item("bili", r, kind="video", title=title_keys,
                      author=("owner", "author", "owner_name"), **_FIELDS)
            for r in _rows(d) if pick(r, *title_keys)]


PARSERS = {
    "search": lambda d: _videos(d),
    "hot": lambda d: _videos(d, ("title",)),
    "feed": lambda d: _videos(d, ("title",)),
}