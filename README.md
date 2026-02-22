# 投稿代理 — 智能竞赛匹配工具

帮助中国创作者找到最合适的国际文学竞赛。输入作品信息，获得个性化推荐。

## 快速开始

```bash
# 交互模式（推荐）
python3 cli.py

# 命令行模式
python3 cli.py --type flash_fiction --words 300 --budget 20

# 查看帮助
python3 cli.py --help

# 列出支持的作品类型
python3 cli.py --list-types

# JSON 输出（方便程序调用）
python3 cli.py --type poetry --budget 15 --json
```

## 支持的作品类型

| 代码 | 类型 |
|------|------|
| `flash_fiction` | 闪小说 |
| `short_story` | 短篇小说 |
| `poetry` | 诗歌 |
| `novel` | 长篇小说 |
| `science_fiction` | 科幻/奇幻 |
| `essay` | 散文/随笔 |
| `memoir` | 回忆录 |
| `nonfiction` | 非虚构 |
| `screenplay` | 编剧/剧本 |
| `novella` | 中篇小说 |
| `children` | 儿童文学 |

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-t, --type` | 作品类型 | (交互选择) |
| `-w, --words` | 字数 | 0 |
| `-b, --budget` | 预算 (USD) | 50 |
| `-s, --style` | 风格标签 | [] |
| `-e, --experience` | 经验等级 | beginner |
| `-n, --top` | 推荐数量 | 5 |
| `-i, --interactive` | 强制交互模式 | - |
| `--json` | JSON 输出 | - |
| `--list-types` | 列出类型 | - |

## 匹配算法

七维评分体系（满分 100）：

- 类型匹配 (20分) — 作品类型 vs 竞赛类别
- 字数匹配 (15分) — 是否在竞赛字数限制内
- 预算匹配 (10分) — 投稿费 vs 预算
- 获奖概率 (20分) — 基于竞争密度、投稿量等
- 声望 (10分) — 竞赛知名度和含金量
- 中国创作者适配度 (15分) — 语言友好度、往届获奖者多样性
- 时间充裕度 (10分) — 距截止日期的天数

硬性过滤：已关闭/已过期/国籍限制/适配度极低/零预算时排除付费竞赛。

每个推荐附带匹配理由和风险提示，不是黑箱。

## 数据库

- 85 条文学类竞赛（2026-02-21 更新）
- 覆盖：闪小说、短篇、诗歌、长篇、科幻、散文、回忆录、编剧等
- 数据来源：竞赛官网直接爬取 + 人工验证

## 运行测试

```bash
python3 test_matcher.py
```

## 文件结构

```
cli.py              — CLI 入口（交互 + 命令行）
matcher.py          — 匹配引擎核心
competitions.json   — 竞赛数据库 (85条)
test_matcher.py     — 测试套件 (14组/26项)
README.md           — 本文件
```

## 依赖

Python 3.8+，无第三方依赖。
