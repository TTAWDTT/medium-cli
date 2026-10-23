"""BOSS直聘适配器 — 上游 jackwener/boss-cli（二进制 boss，包 kabi-boss-cli）。

命令面实测（2026-10）：login（扫码）、search KEYWORD (-c 城市 / -p 页 / 各筛选)、show/detail、me。
搜索输出 --json。
"""

from __future__ import annotations

from ..adapter import make_item, pick, rows
from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "boss")

COMMANDS = {
    "login": lambda o: ["login"],
    "search": lambda o: ["search", o["q"], "-p", str(o.get("page", 1)), "--json"],
}

_P = dict(title=("jobName", "title", "name"),
          url=("jobUrl", "link", "url"),
          id_keys=("securityId", "jobId", "id"),
          author=("brandName", "brand_name", "bossName", "company", "author"))


def _jobs(d: object) -> list:
    return [make_item("boss", r, kind="job", **_P)
            for r in rows(d, ("data", "results", "list", "items", "jobList"))
            if pick(r, *_P["title"])]


PARSERS = {"search": _jobs}