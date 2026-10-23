"""微博适配器 — 上游 jackwener/weibo-cli（二进制 weibo，包 kabi-weibo-cli）。

命令面实测（2026-10）：hot 免登录返回 {realtime:[...]}；search/feed/detail 需登录，均支持 --json。
热搜条目无 URL，这里补成微博搜索链接（可点开）。
"""

from __future__ import annotations

from urllib.parse import quote

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "weibo")

COMMANDS = {
    "login": lambda o: ["login"],
    "search": lambda o: ["search", o["q"], "-n", str(o.get("max", 20)), "--json"],
    "hot": lambda o: ["hot", "-n", str(o.get("max", 20)), "--json"],
    "feed": lambda o: ["feed", "-n", str(o.get("max", 20)), "--json"],
    "read": lambda o: ["detail", o["id"], "--json"],
}


def _hot(d: object) -> list:
    out = []
    for r in rows(d, ("realtime",)):
        word = pick(r, "word", "note")
        if not word:
            continue
        it = make_item("weibo", r, kind="hot", title=("word", "note"),
                       id_keys=("realpos", "id"))
        it.url = f"https://s.weibo.com/weibo?q={quote(word)}"
        if r.get("num"):
            it.extra["heat"] = r["num"]
        out.append(it)
    return out


_P = dict(title=("text", "text_raw", "content", "title"),
          url=("url", "mblog_url", "link"),
          id_keys=("mblogid", "id"),
          author=("user", "user_name", "author"))


def _generic(d: object, kind: str = "post") -> list:
    return [make_item("weibo", r, kind=kind, **_P)
            for r in rows(d, ("data", "weibos", "items", "results"))
            if pick(r, *_P["title"])]


PARSERS = {
    "hot": _hot,
    "search": lambda d: _generic(d),
    "feed": lambda d: _generic(d),
}