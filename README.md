# 投稿代理 — 智能竞赛匹配工具 v2.0

帮助中国创作者找到最合适的国际文学竞赛。输入作品信息，获得个性化推荐。

## 快速开始

```bash
# 交互模式（推荐）
python3 cli.py

# 命令行匹配
python3 cli.py match -t flash_fiction -w 300 -b 20

# 用已保存的档案匹配
python3 cli.py match --profile 1

# 刷新数据库（从网络拉取最新竞赛）
python3 cli.py refresh
python3 cli.py refresh --dry-run    # 预览模式

# 作品档案管理
python3 cli.py profile list
python3 cli.py profile save -t poetry -b 15 --title "我的诗"
python3 cli.py profile match --id 1

# 投稿追踪
python3 cli.py track list           # 查看所有投稿
python3 cli.py track add            # 添加投稿记录
python3 cli.py track update         # 更新状态
python3 cli.py track remind         # 截止日期提醒
python3 cli.py track stats          # 投稿统计

# 数据库统计
python3 cli.py stats

# 帮助
python3 cli.py --help
```

## 功能

- 智能匹配：七维评分（类型/字数/预算/获奖概率/声望/适配度/时间）
- 实时刷新：从 pw.org、Reedsy 等源爬取最新竞赛
- 作品档案：保存作品信息，下次匹配不用重复输入
- 投稿追踪：记录投稿状态（草稿→已投→审核→入围→录用/拒绝）
- 截止提醒：自动标记即将到期的竞赛和投稿
- 中文界面：全中文交互和输出

## 数据库

- 146 条文学类竞赛（实时刷新可扩充）
- 覆盖：闪小说、短篇、诗歌、长篇、科幻、散文、回忆录、编剧等
- 数据来源：竞赛官网 + pw.org + Reedsy + NewPages + InterCompetition

## 文件结构

```
cli.py              — CLI 入口（子命令架构）
matcher.py          — 匹配引擎核心
refresher.py        — 实时爬取模块
profiles.py         — 作品档案管理
tracker.py          — 投稿追踪
competitions.json   — 竞赛数据库
test_matcher.py     — 测试套件 (14组/27项)
README.md           — 本文件
```

## 依赖

Python 3.8+，无第三方依赖。
