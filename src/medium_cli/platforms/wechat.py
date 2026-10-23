"""微信公众号适配器 — 上游 jackwener/wechat-article-to-markdown（二进制同名，包同名）。

用法实测（2026-10）：直接传文章 URL 即输出 markdown（无 --help / 无其它子命令）。
因此只建模 `read <url>`，并把输出原样当 markdown 渲染。
"""

from __future__ import annotations

from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "wechat")

COMMANDS = {
    "read": lambda o: [o["id"]],  # o["id"] 即微信文章 URL
}
PARSERS = {}