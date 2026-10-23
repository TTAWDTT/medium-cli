# medium-cli

聚合各平台社交媒体的统一命令行工具。

一个入口，统一操作知乎、小红书、B站、微博、豆瓣、V2EX、Twitter/X、Reddit、Telegram、Discord、微信公众号和 BOSS直聘：

```bash
$ medium-cli status                     # 哪些平台装了 / 登了
$ medium-cli hot                         # 跨平台热榜，一张表
$ medium-cli search "AI agent" --all     # 跨平台搜索
$ medium-cli feed -p zhihu -p xhs        # 只看知乎+小红书的动态
$ medium-cli read zhihu 30975…           # 读一条，统一 markdown
$ medium-cli post xhs "标题" --content … # 发布（透传上游）
$ medium-cli raw bili <any args…>        # 逃生舱：任何未建模的操作
```

## 设计

medium-cli 是**命令派发器**：各平台已有成熟的专用 CLI（见下表），medium-cli
统一它们的子命令风格（`search / hot / feed / read / post / comment / login`）
并把 `--json` 输出归一化成同一种数据模型。登录、风控、API 全部委托上游，不自研逆向。

- 每个平台 = `src/medium_cli/platforms/<key>.py` 一个模块，导出
  `COMMANDS`（统一动词 → 上游 argv）和 `PARSERS`（上游 json → Item）。
- `--print-command`：只打印将执行的命令不执行，便于调试/脚本化。
- `--all`：线程池并行跑多个平台，结果按注册表顺序汇总。

## 安装

已发布到 PyPI：

```bash
uv tool install medium-cli            # 或 pipx install medium-cli
```

> medium-cli 本身是"调度器"，不含 12 个平台的上游 CLI。装好后先补齐上游、再登录：

```bash
medium-cli install --all              # 补装缺失的上游 CLI（缺哪个装哪个）
medium-cli status                     # 哪些平台可用 / 需登录 / 未安装
medium-cli login -p xhs -p weibo      # 需要登录的平台逐个登录（二维码透传终端）
```

从最新源码安装：`uv tool install git+https://github.com/TTAWDTT/medium-cli`

## 命令一览

| 命令 | 说明 |
|---|---|
| `platforms` | 列出注册表与各平台支持的动词 |
| `status [-p …] [--json]` | 安装/登录状态（登录态为启发式探测） |
| `doctor [-p …]` | 体检 + 缺失平台的安装提示 |
| `install [-p …] [-p …] \| --all` | 安装缺失上游 CLI |
| `login [-p …] [--cookie …]` | 登录（上游二维码流程透传） |
| `search <词> [-p …] [--type …] [--max N] [--json\|--markdown]` | 跨平台搜索 |
| `hot [-p …] [--max N] [--json\|--markdown]` | 跨平台热榜 |
| `feed [-p …] [--max N] [--json\|--markdown]` | 跨平台动态/时间线 |
| `read <platform> <id\|url> [--comments]` | 读一条，输出 markdown |
| `post <platform> <标题> [--content …] [--image …]` | 发布（支持的平台） |
| `comment <platform> <id> <文本>` | 评论（支持的平台） |
| `raw <platform> <args…>` | 透传上游任意参数 |

## 平台注册表

| 平台 | 上游 | 安装 | 统一动词 |
|---|---|---|---|
| 知乎 | [BAIGUANGMEI/zhihu-cli](https://github.com/BAIGUANGMEI/zhihu-cli)（即 zhihu-cli-plus） | `uv tool install pyzhihu-cli` | login/search/hot/feed/read |
| 小红书 | [jackwener/xhs-cli](https://github.com/jackwener/xhs-cli) | `uv tool install xhs-cli` | login/search/hot/feed/read/post/comment |
| B站 | [public-clis/bilibili-cli](https://github.com/public-clis/bilibili-cli) | `uv tool install bilibili-cli` | login/search/hot/feed/read |
| 微博 | [jackwener/weibo-cli](https://github.com/jackwener/weibo-cli) | `uv tool install kabi-weibo-cli` | login/search/hot/feed/read |
| 豆瓣 | [Marvae/douban-cli](https://github.com/Marvae/douban-cli) | `npm i -g @marvae24/douban-cli` | search/hot/read（免登录） |
| V2EX | [unix/v2ex-cli](https://github.com/unix/v2ex-cli) | 上游包损坏（npm 无版本），暂仅 `raw` | — |
| Twitter/X | [public-clis/twitter-cli](https://github.com/public-clis/twitter-cli) | `uv tool install twitter-cli` | search/feed/read/post（无 login，cookies 自动） |
| Reddit | [public-clis/rdt-cli](https://github.com/public-clis/rdt-cli) | `uv tool install rdt-cli` | login/search/hot/feed/read/comment |
| Telegram | [jackwener/tg-cli](https://github.com/jackwener/tg-cli) | `uv tool install kabi-tg-cli` | search/feed |
| Discord | [jackwener/discord-cli](https://github.com/jackwener/discord-cli) | `uv tool install kabi-discord-cli` | login/search/feed |
| 公众号 | [jackwener/wechat-article-to-markdown](https://github.com/jackwener/wechat-article-to-markdown) | `uv tool install wechat-article-to-markdown` | read(URL→md) |
| BOSS直聘 | [jackwener/boss-cli](https://github.com/jackwener/boss-cli) | `uv tool install kabi-boss-cli` | login/search |

## 加平台

1. 选一个上游 CLI，`medium-cli platforms` 记下它的二进制名与安装包。
2. 新建 `src/medium_cli/platforms/<key>.py`，导出 `platform`（来自 registry）、
   `COMMANDS`、`PARSERS`，按需 `READ_MD`。复用 `adapter.make_item` / `pick` / `rows`。
3. 在 `platforms/__init__.py` 注册；跑 `medium-cli platforms` 确认动词出现。

## 开发

```bash
uv sync
uv run pytest          # parser + dispatch 单测
uv run medium-cli hot -p bili -p v2ex -p douban   # 免登录端到端
```

> 上游 CLI 为第三方工具，各自保留登录态与 cookies；`status` 的登录态是启发式探测，并非严格判定。