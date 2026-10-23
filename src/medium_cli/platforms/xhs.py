"""小红书适配器 — 上游 jackwener/xhs-cli（二进制 xhs，包 xhs-cli）。

命令面实测（2026-10）：search/hot/feed/read 支持 --json；post 用 --title/--body/--images 标志。
注意：post 的 --body/--images 上游必填；登录靠浏览器 cookie 自动提取或 --qrcode。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "xhs")

COMMANDS = {
    "login": lambda o: ["login", "--qrcode"],
    "search": lambda o: ["search", o["q"]]
    + (["--type", o["type"]] if o.get("type") else [])
    + (["--page", str(o["page"])] if o.get("page", 1) > 1 else [])
    + ["--json"],
    "hot": lambda o: ["hot"]
    + (["-c", o["category"]] if o.get("category") else [])
    + ["--json"],
    "feed": lambda o: ["feed", "--json"],
    "read": lambda o: ["read", o["id"]],  # 原样渲染，透传给终端
    "post": lambda o: ["post", "--title", o["title"], "--body", o.get("content") or ""]
    + [a for img in (o.get("images") or []) for a in ("--images", img)],
    "comment": lambda o: ["comment", o["id"], o["text"]],
}

_FIELDS = dict(title=("title", "note_title", "desc"),
               url=("url", "note_url"),
               id_keys=("note_id", "id"),
               author=("user", "nickname"))


def _notes(d: object) -> list:
    return [make_item("xhs", r, kind="note", **_FIELDS)
            for r in rows(d, ("data", "notes", "items", "results"))
            if pick(r, *_FIELDS["title"])]


PARSERS = {"search": _notes, "hot": _notes, "feed": _notes}