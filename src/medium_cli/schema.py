"""统一数据模型：上游各平台 CLI 的 --json 输出都归一化成 Item."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass
class Item:
    platform: str
    title: str
    url: str = ""
    kind: str = "post"  # post | video | question | article | book | movie | topic | ...
    id: str = ""
    author: str = ""
    created: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_extra: bool = True) -> dict[str, Any]:
        d = asdict(self)
        if not include_extra or not self.extra:
            d.pop("extra", None)
        return d


def items_to_dicts(items: list[Item]) -> list[dict[str, Any]]:
    return [i.to_dict() for i in items]