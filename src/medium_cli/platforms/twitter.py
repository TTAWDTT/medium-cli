"""Twitter/X 适配器 — 上游 public-clis/twitter-cli（二进制 twitter，包 twitter-cli）。

命令面实测（2026-10）：feed/search (-t type / -n max) / tweet / post（TEXT 位置参数 + -i 图）。
无 login 命令（浏览器 cookies 自动提取），有 status 查登录态。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "twitter")

COMMANDS = {
    "search": lambda o: ["search", o["q"]]
    + (["-t", o["type"]] if o.get("type") else [])
    + ["-n", str(o.get("max", 20)), "--json"],
    "feed": lambda o: ["feed", "-n", str(o.get("max", 20)), "--json"],
    "read": lambda o: ["tweet", o["id"]],
    "post": lambda o: ["post", o.get("content") or o["title"]]
    + [a for img in (o.get("images") or []) for a in ("-i", img)],
}

_P = dict(title=("full_text", "text", "content", "title"),
          url=("url", "permalink", "link"),
          id_keys=("id_str", "tweet_id", "id"),
          author=("user_name", "screen_name", "name", "user"))


def _tweets(d: object, kind: str = "tweet") -> list:
    return [make_item("twitter", r, kind=kind, **_P)
            for r in rows(d, ("tweets", "data", "items", "results"))
            if pick(r, *_P["title"])]


PARSERS = {"search": _tweets, "feed": _tweets, "read": _tweets}