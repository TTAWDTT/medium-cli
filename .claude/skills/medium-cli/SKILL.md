---
name: medium-cli
description: Use medium-cli for unified terminal operations across 12 social/content platforms — 知乎(zhihu), 小红书(xhs), B站(bili), 微博(weibo), 豆瓣(douban), V2EX, Twitter/X, Reddit, Telegram, Discord, 微信公众号(wechat), BOSS直聘(boss): search, hot/trending, feeds, reading content, posting and commenting from one command. Invoke whenever the user wants to browse/search/read/post on these sites or aggregate several at once.
author: Zhen Luo
version: "0.1.0"
tags:
  - medium-cli
  - social-media
  - cli
  - zhihu
  - xiaohongshu
  - xhs
  - bilibili
  - weibo
  - douban
  - twitter
  - reddit
  - telegram
  - discord
  - boss
---

# medium-cli Skill

一个入口操作 12 个平台的统一 CLI。它是"调度器"：每个平台包装各自的上游 CLI，统一成
`search / hot / feed / read / post / comment / login` 等动词，并把上游 `--json`
归一化成同一份数据模型。优先用它，不要自己去调各平台私有 API。

```bash
uv tool install medium-cli                    # 装调度器本身（已发布 PyPI）
medium-cli install --all                      # 补装 12 个上游 CLI（缺哪个装哪个）
medium-cli status                             # 哪些平台 可用/需登录/未安装
medium-cli login -p xhs -p weibo              # 交互登录（二维码透传终端，需用户完成）
```

## Agent 默认行为

1. **要机器可读输出**一律加 `--json`（结构见下）；给人看的用默认表格或 `--markdown`。
2. 缺省会在"所有已装且支持该动词"的平台并行执行；用 `--platform/-p` 限定（可重复）省时间。
3. 结果数量控制：`--max N`（默认 20，medium-cli 按平台逐平台截断）。
4. `--print-command` 只打印将要执行的上游命令、不执行——调试或确认前的安全预览。
5. `login / post / comment / raw` 是交互透传：**不要静默自动执行**；需要登录的平台先
   `medium-cli status` 判定，再提示用户 `medium-cli login -p <key>` 由用户完成扫码。
6. 需登录平台的输出会失败并带明确原因（如 `Session expired — please re-login with: xhs login`），
   把它转述给用户，不要重试。

## 统一 JSON 结构（--json）

每条结果长这样（`kind` 常见值：`question / video / hot / tweet / post / note / job / chat / media`）：

```json
{
  "platform": "douban",
  "title": "三体",
  "url": "https://movie.douban.com/subject/26647087/",
  "kind": "tv",
  "id": "26647087",
  "author": "",
  "created": "",
  "extra": { "rating": "8.7", "year": "2023", "...": "平台专属字段原样保留" }
}
```

## 命令参考

| 命令 | 说明 |
|---|---|
| `medium-cli platforms` | 平台注册表 + 每个平台支持的动词 |
| `medium-cli status [-p …] [--json]` | 安装/登录状态（登录态为启发式探测） |
| `medium-cli doctor [-p …]` | 体检 + 缺失上游的安装命令 |
| `medium-cli install [-p …\|--all]` | 补装缺失的上游 CLI |
| `medium-cli login [-p …] [--cookie …]` | 登录（上游二维码透传） |
| `medium-cli search <词> [-p …] [--type T] [--max N] [--page N] [--json\|--markdown]` | 跨平台搜索 |
| `medium-cli hot [-p …] [--max N] [--category C] [--json\|--markdown]` | 跨平台热榜 |
| `medium-cli feed [-p …] [--max N] [--json\|--markdown]` | 跨平台动态/时间线 |
| `medium-cli read <平台> <id\|url> [--comments]` | 读一条内容，上游渲染原样透传 |
| `medium-cli post <平台> <标题> [--content …] [--image …]` | 发布（仅支持的平台） |
| `medium-cli comment <平台> <id> <文本>` | 评论 |
| `medium-cli raw <平台> <参数…>` | 逃生舱：未建模动词直接透传上游 |

## 平台要点（实测校准过）

- **zhihu**：无 `read` 子命令，内容读取映射上游 `answer`；搜索 `--type general|people|topic`。
- **xhs**：`post` 上游必填 `--body` 与 `--images`；需登录。
- **bili**：`search` 上游默认 user 类型，搜视频加 `--type video`；hot/feed 免登录。
- **weibo**：`hot` 免登录；`search/feed` 需登录；`read` = 详情 detail。
- **douban**：npm 包（不在 PATH，medium-cli 自行查找），全程免登录；`search` 是影视，`--type book` 查图书。
- **twitter**：无 `login` 命令（浏览器 cookies 自动提取）；`read` 用上游 `tweet`。
- **reddit**：`popular/search` 需登录态（`rdt login` 提取浏览器 cookies）。
- **telegram / discord**：本地缓存优先，常用前先上游 `sync`；无会话时 `recent` 返回空缓存而非报错。
- **wechat**：只有 `read`，参数是微信文章 URL，输出 markdown。
- **boss**：需登录（扫码）；`search` 职位。
- **v2ex**：上游包损坏，暂仅 `raw`。

## 错误与恢复

| 现象 | 处理 |
|---|---|
| `未安装 / 未找到可执行文件: <bin>` | `medium-cli install -p <key>`（或 `--all` 全装） |
| `Session expired / 未登录` 或登录平台 `rc!=0` | `medium-cli login -p <key>`，用户扫码 |
| `不支持 <verb>` | 用 `medium-cli raw <key> <上游参数>` 透传未建模能力 |
| `未知平台: xxx` | `medium-cli platforms` 看正确的 key |

## 常见工作流

1. **汇总热榜**：`medium-cli hot --max 5`（免费登录平台缺省全跑，需登录的会在末尾报错）。
2. **搜索 → 读详情**：`medium-cli search "rust" -p bili --type video --max 3 --json`
   → 取 `id`（如 `BV1xxx`）→ `medium-cli read bili BV1xxx`。
3. **公众号文章转 markdown**：`medium-cli read wechat https://mp.weixin.qq.com/s/xxx`。
4. **发帖前预览**：`medium-cli post xhs "标题" --content "正文" --image a.jpg --print-command`。
5. **快速体检**：`medium-cli status --json`，逐平台读 `state`（未安装/可用/需登录/异常）。