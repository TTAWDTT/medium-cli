"""medium-cli 统一命令入口.

对外命令面：
  platforms / status / doctor / install / login
  search / hot / feed / read / post / comment / raw
所有命令都委托上游 CLI；--print-command 只打印将执行的命令，不执行（便于测试）。
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import typer
from rich.table import Table

from . import __version__, platforms as _platforms
from .adapter import PlatformError, find_binary, run, try_json
from .output import console, print_error, render_items, render_text
from .registry import Platform, all_platforms, get_platform, install_hint, resolve


def _mod(p: Platform):
    return getattr(_platforms, "ADAPTERS", {}).get(p.key)


def _fmt(json_fmt: bool, markdown: bool) -> str:
    if json_fmt:
        return "json"
    if markdown:
        return "markdown"
    return "table"


def _resolve(keys: Optional[List[str]]) -> list[Platform]:
    try:
        return resolve(keys)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(code=2) from None


def _collect(ps, verb, opt, *, timeout, print_cmd):
    """并行执行上游；返回 (ok_results, cmdlines, errors).

    ok_results: list[(Platform, CompletedProcess)]
    """
    cmdlines: list[str] = []
    errors: list[str] = []
    results: list = []

    def builder_of(p: Platform):
        m = _mod(p)
        return m and (getattr(m, "COMMANDS", {}) or {}).get(verb)

    if print_cmd:
        for p in ps:
            b = builder_of(p)
            if not b:
                errors.append(f"{p.name}: 不支持 {verb}")
                continue
            cmdlines.append("$ " + " ".join([p.binary, *b(opt)]))
        return results, cmdlines, errors

    def one(p: Platform):
        b = builder_of(p)
        if not b:
            return ("skip", f"{p.name}: 不支持 {verb}")
        binary = find_binary(p.binary)
        if binary is None:
            return ("error", f"{p.name}: 未安装（{install_hint(p)}）")
        try:
            proc = run([binary, *b(opt)], timeout=timeout)
        except PlatformError as e:
            return ("error", f"{p.name}: {e}")
        if proc.returncode != 0:
            return ("error", f"{p.name}: {_friendly_status(proc.stderr or proc.stdout or '', proc.returncode)}")
        return ("ok", (p, proc))

    with ThreadPoolExecutor(max_workers=min(len(ps) or 1, 8)) as ex:
        for kind, payload in ex.map(one, ps):
            if kind == "ok":
                results.append(payload)
            else:
                errors.append(payload)
    return results, cmdlines, errors


def _emit(verb, ps, opt, *, timeout, fmt, single=False, print_cmd=False, quiet=False):
    """跑 verb → 解析归一化 → 按 fmt 渲染。errors 非空时退出码 1。"""
    results, cmdlines, errors = _collect(ps, verb, opt, timeout=timeout, print_cmd=print_cmd)
    if print_cmd:
        for c in cmdlines:
            print(c)
        for e in errors:
            print_error(e)
        return
    if not results:
        for e in errors:
            print_error(e)
        if not errors:
            print_error("没有平台支持该操作")
        raise typer.Exit(code=1)

    items = []
    for p, proc in results:
        m = _mod(p)
        parser = (getattr(m, "PARSERS", {}) or {}).get(verb)
        if parser is None:
            errors.append(f"{p.name}: 缺 {verb} 的 parser")
            continue
        data = try_json(proc.stdout)
        if data is None:
            errors.append(f"{p.name}: 输出不是 JSON（可用 raw 透传）")
            continue
        parsed = parser(data)
        if not parsed:
            parsed = []
        items.extend(parsed)

    cap = opt.get("max")
    if cap:
        counts: dict[str, int] = {}
        capped: list = []
        for it in items:
            n = counts.get(it.platform, 0)
            if n < cap:
                capped.append(it)
                counts[it.platform] = n + 1
        items = capped

    if items or fmt == "json":
        render_items(items, fmt, single=single)
    elif not errors:
        console.print("[yellow](无结果)[/yellow]")
    for e in errors:
        print_error(e)
    if errors:
        raise typer.Exit(code=1)


app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="medium-cli — 聚合知乎/小红书/B站/微博/豆瓣/V2EX/X/Reddit/TG/Discord/公众号/BOSS 的统一命令行工具",
)


def _version_callback(value: bool):
    if value:
        console.print(f"medium-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True)):
    """聚合各平台社交媒体的统一命令行工具."""


# --------------------------------------------------------------------------- 管理命令

@app.command()
def platforms():
    """列出平台注册表与每个平台支持的统一动词。"""
    t = Table(header_style="bold magenta")
    for col in ("平台", "key", "二进制", "安装包", "github", "统一动词"):
        t.add_column(col)
    for p in all_platforms():
        m = _mod(p)
        verbs = ", ".join(getattr(m, "COMMANDS", {}) or {}) if m else "(未适配)"
        t.add_row(p.name, p.key, p.binary, p.install, p.repo, verbs)
    console.print(t)


def _friendly_status(tail_text: str, rc: int) -> str:
    """从探测失败输出里抽一句人话（优先 error.message，其次第一行非空）。"""
    data = try_json(tail_text)
    if isinstance(data, dict):
        err = data.get("error") if isinstance(data.get("error"), dict) else data
        msg = err.get("message") or data.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()[:80]
    lines = [ln.strip() for ln in tail_text.strip().splitlines() if ln.strip()]
    return (lines[0][:80] if lines else f"退出码 {rc}")


def _status_one(p: Platform) -> dict:
    if find_binary(p.binary) is None:
        return {"key": p.key, "name": p.name, "state": "未安装", "detail": install_hint(p)}
    if not p.probe:
        return {"key": p.key, "name": p.name, "state": "已安装", "detail": "公开访问/无需登录态"}
    try:
        proc = run(list(p.probe), timeout=8.0)
    except PlatformError as e:
        return {"key": p.key, "name": p.name, "state": "探测失败", "detail": str(e)}
    if proc.returncode == 0:
        return {"key": p.key, "name": p.name, "state": "可用", "detail": "探测通过"}
    return {
        "key": p.key,
        "name": p.name,
        "state": "需登录/异常",
        "detail": _friendly_status(proc.stderr or proc.stdout or "", proc.returncode),
    }


def _status_table(keys: Optional[List[str]]) -> list[dict]:
    ps = all_platforms() if not keys else _resolve(keys)
    return [_status_one(p) for p in ps]


@app.command()
def status(
    keys: List[str] = typer.Option(None, "--platform", "-p", help="只查指定平台，可多个"),
    as_json: bool = typer.Option(False, "--json"),
):
    """各平台安装与登录状态（登录态为启发式探测）。"""
    rows = _status_table(keys)
    if as_json:
        console.print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    t = Table(header_style="bold magenta")
    t.add_column("平台")
    t.add_column("状态")
    t.add_column("说明")
    for r in rows:
        t.add_row(r["name"], r["state"], r["detail"])
    console.print(t)


@app.command()
def doctor(
    keys: List[str] = typer.Option(None, "--platform", "-p"),
    as_json: bool = typer.Option(False, "--json"),
):
    """体检：未安装的会给出一条可复制的安装命令。"""
    rows = _status_table(keys)
    if as_json:
        console.print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    t = Table(header_style="bold magenta")
    t.add_column("平台")
    t.add_column("状态")
    t.add_column("处理")
    for r in rows:
        handle = r["detail"]
        t.add_row(r["name"], r["state"], handle)
    console.print(t)
    bad = [r for r in rows if r["state"] == "未安装"]
    if bad:
        console.print("\n[bold]一键安装：[/bold] medium-cli install "
                      + " ".join(f"--platform {p['key']}" for p in bad))


@app.command()
def install(
    keys: List[str] = typer.Option(None, "--platform", "-p", help="只装指定平台，可多个"),
    all: bool = typer.Option(False, "--all", help="安装全部缺失平台"),
):
    """安装缺失的上游 CLI（uv tool install <包>）。"""
    which = None if (all or not keys) else keys
    ps = all_platforms() if which is None else _resolve(which)
    missing = [p for p in ps if find_binary(p.binary) is None]
    if not missing:
        console.print("[green]✓[/green] 所选平台都已安装")
        return
    console.print("将安装：")
    for p in missing:
        console.print(f"  {p.name}  →  {install_hint(p)}")
    if not typer.confirm("确认安装 ?", default=True):
        raise typer.Exit(code=1)
    for p in missing:
        console.print(f"[bold]{p.name}[/bold]: {install_hint(p)}")
        if p.installer == "manual":
            console.print(f"[yellow]手动安装[/yellow] {p.install}")
            continue
        argv = ["uv", "tool", "install", p.install] if p.installer == "uv" else ["npm", "install", "-g", p.install]
        run(argv, capture=False, timeout=600)


@app.command()
def login(
    keys: List[str] = typer.Option(None, "--platform", "-p", help="登录的平台，可多个"),
    cookie: Optional[str] = typer.Option(None, "--cookie", help="直接粘贴 cookie 登录"),
    print_cmd: bool = typer.Option(False, "--print-command"),
):
    """登录各平台（转发上游 login，二维码流程透传终端）。"""
    ps = all_platforms() if not keys else _resolve(keys)
    for p in ps:
        m = _mod(p)
        b = (getattr(m, "COMMANDS", {}) or {}).get("login")
        if m is None or b is None:
            console.print(f"{p.name}: [dim]无需登录，跳过[/dim]")
            continue
        binary = find_binary(p.binary)
        if binary is None:
            print_error(f"{p.name}: 未安装（{install_hint(p)}）")
            continue
        argv = [binary, *b({})]
        if cookie:
            argv += ["--cookie", cookie]
        if print_cmd:
            print("$ " + " ".join(argv))
            continue
        console.print(f"== {p.name} ==")
        run(argv, capture=False)


# --------------------------------------------------------------------------- 统一动词

@app.command()
def search(
    query: str = typer.Argument(..., help="搜索关键词"),
    keys: List[str] = typer.Option(None, "--platform", "-p", help="限定平台，可多个；缺省全部"),
    search_type: Optional[str] = typer.Option(None, "--type", help="站内搜索类型（视平台而定）"),
    max_results: int = typer.Option(20, "--max", "--max-results", help="每平台最多条数"),
    page: int = typer.Option(1, "--page", help="页码"),
    as_json: bool = typer.Option(False, "--json"),
    as_markdown: bool = typer.Option(False, "--markdown", "-m"),
    print_cmd: bool = typer.Option(False, "--print-command"),
    timeout: float = typer.Option(60.0, "--timeout"),
):
    """跨平台搜索。"""
    ps = _resolve(keys)
    _emit("search", ps, {"q": query, "type": search_type, "max": max_results, "page": page},
          timeout=timeout, fmt=_fmt(as_json, as_markdown), print_cmd=print_cmd)


@app.command()
def hot(
    keys: List[str] = typer.Option(None, "--platform", "-p", help="限定平台，可多个；缺省全部"),
    max_results: int = typer.Option(20, "--max", "--max-results"),
    category: Optional[str] = typer.Option(None, "--category", help="热点分类（xhs 等视平台而定）"),
    as_json: bool = typer.Option(False, "--json"),
    as_markdown: bool = typer.Option(False, "--markdown", "-m"),
    print_cmd: bool = typer.Option(False, "--print-command"),
    timeout: float = typer.Option(60.0, "--timeout"),
):
    """跨平台热榜。"""
    ps = _resolve(keys)
    _emit("hot", ps, {"max": max_results, "category": category}, timeout=timeout,
          fmt=_fmt(as_json, as_markdown), print_cmd=print_cmd)


@app.command()
def feed(
    keys: List[str] = typer.Option(None, "--platform", "-p", help="限定平台，可多个；缺省全部"),
    max_results: int = typer.Option(20, "--max", "--max-results"),
    as_json: bool = typer.Option(False, "--json"),
    as_markdown: bool = typer.Option(False, "--markdown", "-m"),
    print_cmd: bool = typer.Option(False, "--print-command"),
    timeout: float = typer.Option(60.0, "--timeout"),
):
    """跨平台信息流 / 时间线。"""
    ps = _resolve(keys)
    _emit("feed", ps, {"max": max_results}, timeout=timeout,
          fmt=_fmt(as_json, as_markdown), print_cmd=print_cmd)


@app.command()
def read(
    platform: str = typer.Argument(..., help="平台 key"),
    ref: str = typer.Argument(..., help="id 或 URL"),
    comments: bool = typer.Option(False, "--comments", help="附带评论"),
    print_cmd: bool = typer.Option(False, "--print-command"),
    timeout: float = typer.Option(60.0, "--timeout"),
):
    """读取一条内容，输出 markdown（上游直接输出文本时原样透传）。"""
    p = get_platform(platform)
    if p is None:
        print_error(f"未知平台: {platform}")
        raise typer.Exit(code=2)
    m = _mod(p)
    b = m and (getattr(m, "COMMANDS", {}) or {}).get("read")
    if m is None or b is None:
        print_error(f"{p.name}: 不支持 read（可用 medium-cli raw {platform} … 透传）")
        raise typer.Exit(code=1)
    binary = find_binary(p.binary)
    if binary is None:
        print_error(f"{p.name}: 未安装（{install_hint(p)}）")
        raise typer.Exit(code=1)
    argv = [binary, *b({"id": ref, "comments": comments})]
    if print_cmd:
        print("$ " + " ".join(argv))
        return
    proc = run(argv, timeout=timeout)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        print_error(tail[-1][:160] if tail else f"退出码 {proc.returncode}")
        raise typer.Exit(code=1)
    # 内容读取统一把上游渲染结果当 markdown/文本原样透传（JSON 分项对"读一条"没意义）
    render_text(proc.stdout)


@app.command()
def post(
    platform: str = typer.Argument(..., help="平台 key"),
    title: str = typer.Argument(..., help="标题"),
    content: Optional[str] = typer.Option(None, "--content", help="正文"),
    image: List[str] = typer.Option(None, "--image", help="图片路径，可多个"),
    print_cmd: bool = typer.Option(False, "--print-command"),
):
    """发布内容（透传上游 post）。"""
    p = get_platform(platform)
    if p is None:
        print_error(f"未知平台: {platform}")
        raise typer.Exit(code=2)
    m = _mod(p)
    b = m and (getattr(m, "COMMANDS", {}) or {}).get("post")
    if m is None or b is None:
        print_error(f"{p.name}: 不支持 post")
        raise typer.Exit(code=1)
    binary = find_binary(p.binary)
    if binary is None:
        print_error(f"{p.name}: 未安装（{install_hint(p)}）")
        raise typer.Exit(code=1)
    argv = [binary, *b({"title": title, "content": content, "images": image})]
    if print_cmd:
        print("$ " + " ".join(argv))
        return
    run(argv, capture=False)


@app.command()
def comment(
    platform: str = typer.Argument(..., help="平台 key"),
    ref: str = typer.Argument(..., help="目标 id"),
    text: str = typer.Argument(..., help="评论内容"),
    print_cmd: bool = typer.Option(False, "--print-command"),
):
    """评论（透传上游 comment）。"""
    p = get_platform(platform)
    if p is None:
        print_error(f"未知平台: {platform}")
        raise typer.Exit(code=2)
    m = _mod(p)
    b = m and (getattr(m, "COMMANDS", {}) or {}).get("comment")
    if m is None or b is None:
        print_error(f"{p.name}: 不支持 comment")
        raise typer.Exit(code=1)
    binary = find_binary(p.binary)
    if binary is None:
        print_error(f"{p.name}: 未安装（{install_hint(p)}）")
        raise typer.Exit(code=1)
    argv = [binary, *b({"id": ref, "text": text})]
    if print_cmd:
        print("$ " + " ".join(argv))
        return
    run(argv, capture=False)


@app.command()
def raw(
    platform: str = typer.Argument(..., help="平台 key"),
    args: List[str] = typer.Argument(None, help="透传给上游的参数"),
):
    """逃生舱：未建模的动词直接透传上游 CLI，完全交互。"""
    p = get_platform(platform)
    if p is None:
        print_error(f"未知平台: {platform}")
        raise typer.Exit(code=2)
    binary = find_binary(p.binary)
    if binary is None:
        print_error(f"{p.name}: 未安装（{install_hint(p)}）")
        raise typer.Exit(code=1)
    argv = [binary, *(args or [])]
    print("$ " + " ".join(argv))
    run(argv, capture=False)


if __name__ == "__main__":
    app()