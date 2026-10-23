"""V2EX 适配器 — 上游 unix/v2ex-cli（老项目，可能需源码构建）。探测后填充。"""

from __future__ import annotations

from ..registry import all_platforms

platform = next(p for p in all_platforms() if p.key == "v2ex")

COMMANDS = {}  # 探测上游后补充
PARSERS = {}
READ_MD = False