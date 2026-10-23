"""输出渲染：rich 表格 / JSON / Markdown。"""

from __future__ import annotations

import json
from typing import Iterable, Sequence

from rich.console import Console
from rich.table import Table

from .schema import Item

console = Console()


def render_items(
    items: Sequence[Item],
    fmt: str = "table",
    *,
    single: bool = False,
    c: Console = console,
) -> str | None:
    """渲染统一 Item 列表。fmt: table | json | markdown。返回首行(title)供 CLI 使用。"""
    if fmt == "json":
        c.print(json.dumps([i.to_dict() for i in items], ensure_ascii=False, indent=2))
        return None
    if fmt == "markdown":
        for i in items:
            tag = i.platform if not single else ""
            link = f"[{i.title}]({i.url})" if i.url else i.title
            c.print(f"- {link} `{tag}`".strip())
        return None
    _table(items, single=single, c=c)
    return None


def _table(items: Iterable[Item], *, single: bool, c: Console) -> None:
    t = Table(show_header=True, header_style="bold magenta")
    if not single:
        t.add_column("平台", no_wrap=True)
    t.add_column("类型")
    t.add_column("标题")
    if single:
        t.add_column("作者")
        t.add_column("时间")
    else:
        t.add_column("链接", style="dim")
    for i in items:
        row = []
        if not single:
            row.append(i.platform)
        row.append(i.kind)
        row.append(i.title)
        if single:
            row.append(i.author)
            row.append(i.created)
        else:
            row.append(i.url or "")
        t.add_row(*row)
    c.print(t)


def render_text(text: str, *, fmt: str = "markdown", c: Console = console) -> None:
    """渲染 read 返回的正文（上游原生 markdown / 文本）。不转义，保持原样。"""
    text = text.rstrip("\n")
    if not text:
        c.print("[dim](空内容)[/dim]")
        return
    c.print(text)


def print_error(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")