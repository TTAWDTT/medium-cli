"""Discord 适配器 — 上游 jackwener/discord-cli（二进制 discord，包 kabi-discord-cli）。

命令面实测（2026-10）：search KEYWORD、recent、stats、export；`auth` 从本地浏览器/Discord 客户端
提取 token（对应统一 login 语义）。本地优先：先 dc sync 再搜索。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "discord")

COMMANDS = {
    "login": lambda o: ["auth"],
    "search": lambda o: ["search", o["q"], "-n", str(o.get("max", 20)), "--json"],
    "feed": lambda o: ["recent", "-n", str(o.get("max", 20)), "--json"],
}

_P = dict(title=("message", "text", "content"),
          url=("",),
          id_keys=("id", "message_id"),
          author=("author", "sender", "name", "username"),
          created=("timestamp", "date", "created"))


def _msgs(d: object, kind: str = "chat") -> list:
    return [make_item("discord", r, kind=kind, **_P)
            for r in rows(d, ("messages", "data", "items", "results"))
            if pick(r, *_P["title"])]


PARSERS = {"search": _msgs, "feed": _msgs}