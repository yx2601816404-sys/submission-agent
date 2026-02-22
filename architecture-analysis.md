# 投稿代理 — 系统架构分析

> 2026-02-21 | 基于实际爬取经验和产品需求的技术评估

## 你说得对，这不是小工程

把"帮中国创作者投稿国际竞赛"拆开来看，至少有这些子系统：

```
┌─────────────────────────────────────────────────────────┐
│                    投稿代理系统                            │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ 竞赛数据库 │ 匹配引擎  │ 翻译引擎  │ 投稿执行  │ 用户系统      │
│          │          │          │          │              │
│ 爬虫+更新  │ 作品分析   │ AI翻译    │ 表单填写   │ 账号管理      │
│ 结构化存储  │ 多维评分   │ 人工审校   │ 文件上传   │ 支付系统      │
│ 风格标签   │ 推荐排序   │ 格式适配   │ 支付代付   │ 通知系统      │
│ 过期清理   │ 预算规划   │ Bio撰写   │ 确认截图   │ 投稿追踪      │
└──────────┴──────────┴──────────┴──────────┴──────────────┘
```

## 复杂度评估

### 1. 竞赛数据库（当前在做）
- **难度**: ⭐⭐⭐
- **现状**: 51条结构化数据，87.5%爬取成功率
- **痛点**: 
  - 每个竞赛的投稿平台不同（Submittable/官网/FilmFreeway/Festhome）
  - 风格偏好需要读往届获奖作品才能判断（不是结构化数据）
  - 截止日期每年变，需要持续更新
- **解决方案**: markdown → SQLite → PostgreSQL 逐步升级

### 2. 支付系统 💰
- **难度**: ⭐⭐⭐⭐⭐（最难）
- **问题**:
  - 竞赛投稿费支付方式五花八门：PayPal、信用卡（Visa/MC/Amex）、Stripe、支付宝（Red Dot支持！）
  - 中国用户大多没有国际信用卡/PayPal
  - 代付涉及资金合规问题
- **方案选项**:
  - A. 用户自己付（提供教程）→ 体验差但合规
  - B. 代付（我们垫付+收手续费）→ 体验好但有资金风险和合规问题
  - C. 虚拟信用卡服务（如 Wise/Payoneer）→ 折中方案
- **MVP建议**: Phase 0-1 先做方案A，教用户办 Wise 虚拟卡；Phase 2 再考虑代付

### 3. 投稿执行（代投）🤖
- **难度**: ⭐⭐⭐⭐
- **问题**:
  - 每个平台的投稿表单不同
  - Submittable 需要注册账号（用谁的？）
  - 有些平台需要上传文件、填写Bio、选择类别
  - 确认邮件发到哪个邮箱？
- **方案**:
  - 用户提供自己的平台账号 → 我们远程操作（安全隐患）
  - 我们用统一代理账号 → 违反大多数平台TOS
  - 用户自己操作，我们提供逐步指导 → 最安全但体验差
- **MVP建议**: Phase 0-1 做"投稿指导"而非"代投"——生成完整的投稿包（翻译好的稿件+Bio+Cover Letter+格式化文件+逐步操作截图指南），用户自己提交

### 4. 通知系统 📧
- **难度**: ⭐⭐
- **需求**:
  - 截止日期提醒（30/14/7/3/1天）
  - 新竞赛推荐
  - 投稿状态更新
  - 结果公布通知
- **方案**: 微信服务号模板消息 / 邮件 / 小红书私信
- **MVP建议**: Phase 0 用微信群手动通知；Phase 1 接微信服务号

### 5. 数据库选型 🗄️
- **当前**: Markdown 文件（competitions-db-v2.md）
- **Phase 1**: SQLite（单文件，零运维）
- **Phase 2**: PostgreSQL + 全文搜索
- **数据模型**:

```sql
-- 核心表
competitions (
  id, name, field, subfield, url, 
  deadline, result_date, status,
  entry_fee_amount, entry_fee_currency,
  prize_amount, prize_currency, prize_description,
  word_limit_min, word_limit_max,
  language_required, nationality_restriction,
  submission_platform, -- submittable/filmfreeway/website/email
  simultaneous_ok, previously_published_ok,
  anonymous_review, ai_policy,
  prestige_score, -- 1-10
  last_verified, next_check_date
)

-- 风格偏好（关键差异化数据）
competition_style (
  competition_id,
  style_tags, -- literary/commercial/experimental/traditional
  theme_preferences, -- 主题偏好
  past_winner_analysis, -- AI分析往届获奖作品的风格总结
  judge_preferences, -- 评委偏好分析
  tips_for_chinese_creators -- 对中国创作者的特别建议
)

-- 用户作品
user_works (
  id, user_id, title, field, 
  word_count, language, style_tags,
  synopsis, themes
)

-- 投稿记录
submissions (
  id, user_id, work_id, competition_id,
  status, -- draft/prepared/submitted/confirmed/result
  submitted_at, confirmation_screenshot,
  result, result_notified_at
)
```

## 重新评估 MVP 策略

基于以上分析，我建议调整 MVP 定义：

### Phase 0 真正的 MVP（2周）
**不做代投，做"投稿包"服务**

1. 用户告诉我们：作品类型 + 字数 + 风格 + 预算
2. 我们返回：匹配的竞赛列表（从数据库中筛选）
3. 用户选择竞赛后，我们提供：
   - ✅ 翻译好的稿件（AI翻译+润色）
   - ✅ 英文Bio
   - ✅ Cover Letter（如需要）
   - ✅ 格式化好的文件（符合竞赛要求）
   - ✅ 逐步投稿指南（带截图）
   - ❌ 不代替用户提交（避免账号/支付/合规问题）

**这样一来：**
- 不需要支付系统（用户自己付投稿费）
- 不需要代理账号（用户自己注册）
- 不需要通知邮箱（确认邮件发到用户自己邮箱）
- 核心价值依然存在：信息差+语言壁垒+格式适配

### Phase 1 再加代投（如果验证成功）
- 针对高频用户提供"全托管"服务
- 用户授权我们使用他们的账号
- 建立正式的服务协议和授权流程

## 当前数据库的风格标签计划

我已经从往届获奖者数据中提取了一些风格信号，比如：

**Desperate Literature Prize 风格画像：**
- 偏好：文学性强、实验性、国际视角、情感张力
- 往届获奖者：多为MFA毕业生、有出版经历的新锐作家
- 评委：Ottessa Moshfegh（2025）、Megan McDowell（2024）、Tiffany Tsao（2023）
- 评委评语关键词："tender and haunting"、"economy of words"、"narrative voice"、"music and rhythm"
- 对中国创作者建议：适合有英语写作能力的文学创作者，风格偏向当代文学小说

**IPA 摄影奖风格画像：**
- 11个专业类别 + 11个非专业类别
- 偏好：技术精湛、叙事性强、视觉冲击力
- 对中国创作者建议：摄影类无语言壁垒，直接投稿即可；Fine Art 和 Nature 类别中国摄影师有优势

这种风格分析需要逐个竞赛做，工作量不小但价值很高——这是我们的核心壁垒。

---

*结论：先把数据库做扎实（结构化+风格标签），MVP 做"投稿包"而非"代投"，避开支付/账号/合规的坑。*
