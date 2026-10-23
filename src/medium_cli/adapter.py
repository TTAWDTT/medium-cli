"""调用上游 CLI 的公共基础设施：找二进制、跑子进程、容错解析 JSON、归一化为 Item."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Callable, Sequence

from .schema import Item

TIMEOUT = 60

_NPM_BINS: list[str] | None = None


class PlatformError(RuntimeError):
    """执行上游 CLI 失败，包装成可读信息抛出。"""


def _npm_bin_dirs() -> list[str]:
    """npm 全局 bin 目录可能不在 PATH（macOS 很常见），medium-cli 自行纳入查找。"""
    global _NPM_BINS
    if _NPM_BINS is None:
        _NPM_BINS = []
        try:
            proc = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True, timeout=8)
            if proc.returncode == 0:
                prefix = proc.stdout.strip()
                _NPM_BINS = [os.path.join(prefix, "bin"), prefix]
        except Exception:
            pass
    return _NPM_BINS


def find_binary(name: str) -> str | None:
    p = shutil.which(name)
    if p:
        return p
    for d in _npm_bin_dirs():
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def run(
    argv: Sequence[str],
    *,
    timeout: float = TIMEOUT,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """执行命令。capture=True 时吞掉输出返回；否则继承 tty（用于登录/交互）。"""
    kwargs: dict[str, Any] = {}
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return subprocess.run(list(argv), timeout=timeout, **kwargs)
    except FileNotFoundError:
        raise PlatformError(f"未找到可执行文件: {argv[0] if argv else '?'}") from None
    except subprocess.TimeoutExpired:
        raise PlatformError(f"上游 {argv[0] if argv else '?'} 执行超时 (> {timeout}s)") from None


def try_json(text: str) -> Any | None:
    """容错解析：上游可能先打日志再输出 JSON，尽力截取 {..} 或 [..] 部分。"""
    if not text:
        return None
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = stripped.find(start_char)
        end = stripped.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def rows(
    data: Any,
    keys: Sequence[str] = ("items", "data", "results", "list", "records", "rows"),
) -> list[dict[str, Any]]:
    """从上游 --json 载荷里取出行列表。支持 {items:[...]}、裸数组、单对象。"""
    if data is None:
        return []
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
        return [data] if data else []
    return []


def pick(row: Mapping[str, Any], *names: str, default: str = "") -> str:
    """按字段名优先级取值（很多平台的字段名不同，但语义相同）。"""
    for n in names:
        if n in row:
            v = row[n]
            if v is not None and not (isinstance(v, str) and not v.strip()):
                return str(v)
    return default


def make_item(
    platform: str,
    row: Mapping[str, Any],
    *,
    kind: str = "post",
    title: Sequence[str] = ("title", "name", "text", "content"),
    url: Sequence[str] = ("url", "link", "permalink", "note_url"),
    id_keys: Sequence[str] = ("id", "note_id", "post_id", "reply_id"),
    author: Sequence[str] = ("author", "user", "user_name", "nickname", "author_name", "owner"),
    created: Sequence[str] = ("created", "created_at", "publish_time", "timestamp", "date"),
) -> Item:
    extra = {
        k: v
        for k, v in row.items()
        if isinstance(v, (str, int, float, bool)) or v is None
    }
    # 抽取嵌套的作者对象里最常见的名字字段
    author_val = ""
    for a in author:
        v = row.get(a)
        if isinstance(v, dict):
            author_val = pick(v, "name", "user_name", "nickname", "screen_name")
        elif isinstance(v, (str, int, float)) and v is not None:
            author_val = str(v)
        if author_val:
            break
    return Item(
        platform=platform,
        kind=kind,
        title=pick(row, *title),
        url=pick(row, *url),
        id=pick(row, *id_keys),
        author=author_val,
        created=pick(row, *created),
        extra=extra,
    )


# 常用行提取器：有的上游把答案/正文等放在嵌套 key 下
def nested_rows(data: Any, container: str, keys: Sequence[str] = ()) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(container), dict):
        return rows(data[container], keys)
    return rows(data, keys)


CommandBuilder = Callable[[dict[str, Any]], list[str] | None]
Parser = Callable[[Any], list[Item] | None]