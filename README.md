# 投稿代理 — 智能竞赛匹配工具

帮助中国创作者找到最合适的国际文学竞赛。输入作品信息，获得个性化推荐。

> 196 条竞赛 · 3 个数据源 · 零依赖 · 全中文界面

## 安装

```bash
git clone https://github.com/yx2601816404-sys/submission-agent.git
cd submission-agent
pip install -e .

# 或直接运行
python3 cli.py
```

安装后可用 `submission-agent` 命令代替 `python3 cli.py`。

## 快速开始

```bash
# 首次运行自动进入新手引导
submission-agent

# 命令行匹配
submission-agent match -t flash_fiction -w 300 -b 20

# 用已保存的档案匹配
submission-agent match --profile 1

# 查看截止日期日历
submission-agent calendar

# 查看竞赛详情
submission-agent show 1
submission-agent show -s moth
```

## 功能一览

| 命令 | 说明 |
|------|------|
| `match` | 智能匹配竞赛（七维评分） |
| `calendar` | 按月显示截止日期，🔥/⏰ 紧急标记 |
| `show` | 查看竞赛详情 / 按名称搜索 |
| `refresh` | 从 pw.org / Reedsy / NewPages 刷新数据库 |
| `profile` | 管理作品档案 |
| `track` | 投稿追踪（7种状态） |
| `stats` | 数据库统计 |
| `--export csv/md` | 导出匹配结果 |

### 匹配引擎

八维评分，满分 100：

- 类型匹配 (18) — 作品类型与竞赛要求
- 字数匹配 (13) — 字数是否在限制范围内
- 风格匹配 (10) — 文学风格标签交集 + 相近风格映射
- 预算匹配 (10) — 费用是否在预算内
- 获奖概率 (18) — 基于竞赛规模和竞争程度
- 声望评分 (8) — 竞赛知名度和影响力
- 适配度 (13) — 对中国创作者的友好程度
- 时间评分 (10) — 截止日期紧迫度

### 数据库

- 196 条文学竞赛，覆盖 13 个类别
- 实时过期检测，自动标记已过期竞赛
- 支持增量刷新，每次最多新增 50 条
- 自动推断竞赛评分（prestige / win_probability / fit）
- 竞赛名自动中英翻译

### 投稿追踪

7 种状态流转：草稿 → 已投 → 审核中 → 入围 → 录用 / 拒绝 / 撤回

## 作品类型

闪小说 · 短篇小说 · 诗歌 · 长篇小说 · 中篇小说 · 科幻/奇幻 · 非虚构 · 学术散文 · 回忆录 · 编剧/剧本 · 儿童文学 · 诗集 · 多类别

## 文件结构

```
cli.py              CLI 入口（子命令架构，~930行）
matcher.py          匹配引擎核心
refresher.py        实时爬取 + auto_score 评分推断
translator.py       竞赛名中英翻译
profiles.py         作品档案管理
tracker.py          投稿追踪
competitions.json   竞赛数据库（196条）
test_matcher.py     测试套件（27项，100%通过）
setup.py            打包配置
```

## 技术栈

- Python 3.8+
- 零第三方依赖（stdlib only: urllib, json, re, argparse）
- 数据存储：JSON 文件
- 爬取：urllib + regex HTML 解析

## License

MIT
