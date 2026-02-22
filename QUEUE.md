# 任务队列

## 待办
- 数据质量：部分 NewPages 爬取的竞赛缺少奖金信息（prize_first=0），可以二次爬取竞赛官网补全

## 进行中
- 导出功能：支持导出匹配结果为 CSV/Markdown

## 阻塞

## 完成
- 匹配引擎优化：auto_score 自动推断 prestige/win_prob/fit，76条竞赛更新
- 打包分发：setup.py + entry_points，pip install 后 submission-agent 命令直接可用
- 用户引导流程：首次运行自动 onboarding，三步引导+常用命令速查
- 中文界面完善：translator.py 关键词翻译器，196条全部有中文名
- 实时爬取源扩展：新增 NewPages 解析器，3 个源，数据库 196 条
- v2.0：实时爬取 + 作品档案 + 投稿追踪（27/27测试通过）
