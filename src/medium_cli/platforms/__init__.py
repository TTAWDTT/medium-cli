"""平台适配器注册表：模块导出 COMMANDS/PARSERS，在此统一收集成 ADAPTERS.

cli 通过 ADAPTERS[key] 找到模块；没适配的平台在 verbs 命令里报"不支持"，raw 可透传。
"""

from ..registry import PLATFORMS  # noqa: F401 确保注册表先加载
from . import (
    bilibili,
    boss,
    discord,
    douban,
    reddit,
    telegram,
    twitter,
    v2ex,
    wechat,
    weibo,
    xhs,
    zhihu,
)

ADAPTERS: dict[str, object] = {
    "zhihu": zhihu,
    "xhs": xhs,
    "bili": bilibili,
    "twitter": twitter,
    "weibo": weibo,
    "douban": douban,
    "v2ex": v2ex,
    "reddit": reddit,
    "telegram": telegram,
    "discord": discord,
    "wechat": wechat,
    "boss": boss,
}