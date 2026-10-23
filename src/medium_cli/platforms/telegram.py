"""Telegram 适配器 — 上游 jackwener/tg-cli（二进制 tg，包 kabi-tg-cli）。

命令面实测（2026-10）：search KEYWORD (-c chat / -s sender / -n limit)、recent、send、sync、export。
本地优先：先 sync/refresh 缓存再搜索；无 login 命令（Telethon 会话），有 status。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "telegram")

COMMANDS = {
    "search": lambda o: ["search", o["q"], "-n", str(o.get("max", 20)), "--json"],
    "feed": lambda o: ["recent", "-n", str(o.get("max", 20)), "--json"],
    # 发消息走逃生舱：tg send <chat> <msg>
}

_P = dict(title=("message", "text", "content"),
          url=("",),
          id_keys=("id", "message_id"),
          author=("sender", "sender_name", "name", "username", "from"),
          created=("date", "created", "timestamp"))


def _msgs(d: object, kind: str = "chat") -> list:
    return [make_item("telegram", r, kind=kind, **_P)
            for r in rows(d, ("messages", "data", "items", "results"))
            if pick(r, *_P["title"])]


PARSERS = {"search": _msgs, "feed": _msgs}