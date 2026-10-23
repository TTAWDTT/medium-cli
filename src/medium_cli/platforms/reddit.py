"""Reddit 适配器 — 上游 public-clis/rdt-cli（二进制 rdt，包 rdt-cli）。

命令面实测（2026-10）：search (-r subreddit / -s sort / -n limit)、popular、feed（需登录）、
read、comment、login（自动提取浏览器 cookies）。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "reddit")

COMMANDS = {
    "login": lambda o: ["login"],
    "search": lambda o: ["search", o["q"], "-n", str(o.get("max", 20)), "--json"],
    "hot": lambda o: ["popular", "-n", str(o.get("max", 20)), "--json"],
    "feed": lambda o: ["feed", "-n", str(o.get("max", 20)), "--json"],
    "read": lambda o: ["read", o["id"]],
    "comment": lambda o: ["comment", o["id"], o["text"]],
}


def _rows(d: object) -> list:
    out = []
    for r in rows(d, ("data", "posts", "children", "items", "results")):
        # Reddit 常见形态 children:[{data:{...}}]
        if isinstance(r, dict) and isinstance(r.get("data"), dict):
            r = r["data"]
        out.append(r)
    return out


_P = dict(title=("title", "selftext", "text"),
          url=("url", "permalink", "link"),
          id_keys=("id", "post_id", "name"),
          author=("author", "username", "user"),
          created=("created_utc", "created", "timestamp"))


def _posts(d: object, kind: str = "post") -> list:
    return [make_item("reddit", r, kind=kind, **_P)
            for r in _rows(d) if pick(r, *_P["title"])]


PARSERS = {"search": _posts, "hot": _posts, "feed": _posts}