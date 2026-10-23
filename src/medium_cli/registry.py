"""平台注册表：每个平台的上游元数据（二进制、安装包、探测命令）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Platform:
    key: str
    name: str
    binary: str          # 上游可执行文件名（PATH 中）
    install: str         # 安装目标（包名/说明），见 installer
    repo: str            # github 仓库
    probe: tuple[str, ...] = ()  # status 探测用的轻量只读 argv；空表示该平台无需登录
    installer: str = "uv"  # uv | npm | manual；决定 install 命令怎么拼


def install_hint(p: Platform) -> str:
    if p.installer == "uv":
        return f"uv tool install {p.install}"
    if p.installer == "npm":
        return f"npm i -g {p.install}"
    return p.install


# 顺序即 medium-cli 输出顺序。install/binary 以实测上游为准（见 README 安装一节）。
PLATFORMS: tuple[Platform, ...] = (
    Platform("zhihu", "知乎", "zhihu", "pyzhihu-cli", "BAIGUANGMEI/zhihu-cli",
             ("zhihu", "feed", "-l", "1", "--json")),
    Platform("xhs", "小红书", "xhs", "xhs-cli", "jackwener/xhs-cli",
             ("xhs", "feed", "--json")),
    Platform("bili", "B站", "bili", "bilibili-cli", "public-clis/bilibili-cli",
             ("bili", "feed", "--json")),
    Platform("weibo", "微博", "weibo", "kabi-weibo-cli", "jackwener/weibo-cli",
             ("weibo", "feed", "-n", "1", "--json")),
    Platform("douban", "豆瓣", "douban", "@marvae24/douban-cli", "Marvae/douban-cli", installer="npm"),
    Platform("v2ex", "V2EX", "v2ex", "(源码构建：go install，以实测为准)", "unix/v2ex-cli", installer="manual"),
    Platform("twitter", "Twitter/X", "twitter", "twitter-cli", "public-clis/twitter-cli",
             ("twitter", "feed", "-n", "1", "--json")),
    Platform("reddit", "Reddit", "rdt", "rdt-cli", "public-clis/rdt-cli",
             ("rdt", "popular", "-n", "1", "--json")),
    Platform("telegram", "Telegram", "tg", "kabi-tg-cli", "jackwener/tg-cli",
             ("tg", "recent", "-n", "1", "--json")),
    Platform("discord", "Discord", "discord", "kabi-discord-cli", "jackwener/discord-cli",
             ("discord", "recent", "-n", "1", "--json")),
    Platform("wechat", "公众号", "wechat-article-to-markdown", "wechat-article-to-markdown", "jackwener/wechat-article-to-markdown"),
    Platform("boss", "BOSS直聘", "boss", "kabi-boss-cli", "jackwener/boss-cli",
             ("boss", "status")),
)

_BY_KEY: dict[str, Platform] = {p.key: p for p in PLATFORMS}


def get_platform(key: str) -> Platform | None:
    return _BY_KEY.get(key)


def all_platforms() -> tuple[Platform, ...]:
    return PLATFORMS


def resolve(keys: Sequence[str] | None) -> list[Platform]:
    """把 --platform 给的 key 解析成 Platform 列表；None 或空 = 全部。"""
    if keys:
        out: list[Platform] = []
        for k in keys:
            p = get_platform(k)
            if p is None:
                raise ValueError(f"未知平台: {k}（medium-cli platforms 查看全部）")
            out.append(p)
        return out
    return list(PLATFORMS)