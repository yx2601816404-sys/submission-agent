#!/usr/bin/env python3
"""
投稿代理 CLI — 智能竞赛匹配工具 v2.1
用法:
  交互模式:    python3 cli.py
  命令行匹配:  python3 cli.py match --type flash_fiction --words 300
  刷新数据库:  python3 cli.py refresh [--dry-run]
  作品档案:    python3 cli.py profile [list|save|delete|match]
  投稿追踪:    python3 cli.py track [list|add|update|remind|stats]
  数据库统计:  python3 cli.py stats
  帮助:        python3 cli.py --help
"""

import argparse
import json
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matcher import recommend, load_db, DB_PATH
from profiles import (load_profiles, save_profile, list_profiles, get_profile,
                      profile_to_work, interactive_save, interactive_load, delete_profile)
from tracker import (list_submissions, interactive_add, interactive_update,
                     show_reminders, submission_stats, add_submission, update_status)
from refresher import refresh as do_refresh

# ── 子类别中文名 ──────────────────────────────────────────
SUBFIELD_CN = {
    "flash_fiction": "闪小说",
    "short_story": "短篇小说",
    "poetry": "诗歌",
    "novel": "长篇小说",
    "science_fiction_fantasy": "科幻/奇幻",
    "essay_academic": "学术散文",
    "memoir": "回忆录",
    "nonfiction": "非虚构",
    "screenplay": "编剧/剧本",
    "novella": "中篇小说",
    "children": "儿童文学",
    "multiple": "多类别",
    "poetry_collection": "诗集",
}

# ── 类型映射 ──────────────────────────────────────────────
TYPE_CHOICES = {
    "1": ("flash_fiction",     "闪小说 (Flash Fiction)"),
    "2": ("short_story",       "短篇小说 (Short Story)"),
    "3": ("poetry",            "诗歌 (Poetry)"),
    "4": ("novel",             "长篇小说 (Novel)"),
    "5": ("science_fiction",   "科幻/奇幻 (Sci-Fi / Fantasy)"),
    "6": ("essay",             "散文/随笔 (Essay)"),
    "7": ("memoir",            "回忆录 (Memoir)"),
    "8": ("nonfiction",        "非虚构 (Nonfiction)"),
    "9": ("screenplay",        "编剧/剧本 (Screenplay)"),
    "10": ("novella",          "中篇小说 (Novella)"),
    "11": ("children",         "儿童文学 (Children's)"),
}

STYLE_CHOICES = {
    "1": "literary", "2": "contemporary", "3": "experimental",
    "4": "traditional", "5": "nature", "6": "contemplative",
    "7": "humorous", "8": "dark", "9": "science_fiction", "10": "imaginative",
}

EXPERIENCE_CHOICES = {
    "1": ("beginner",      "新手 — 没投过或投过 1-2 次"),
    "2": ("intermediate",  "进阶 — 投过几次，可能有入围/发表"),
    "3": ("advanced",      "资深 — 多次获奖或发表经历"),
}

# ── 颜色 ──────────────────────────────────────────────────
def color(text, code):
    if not sys.stdout.isatty(): return text
    return f"\033[{code}m{text}\033[0m"

def bold(t):   return color(t, "1")
def cyan(t):   return color(t, "36")
def green(t):  return color(t, "32")
def yellow(t): return color(t, "33")
def red(t):    return color(t, "31")
def dim(t):    return color(t, "2")

# ── 数据库统计 ────────────────────────────────────────────
def db_stats():
    comps = load_db()
    today = date.today()
    total = len(comps)
    active = expired = 0
    for c in comps:
        dl = c.get("deadline", "")
        if not dl or dl in ("weekly", "quarterly", "rolling"):
            active += 1
        else:
            try:
                dt = datetime.strptime(dl, "%Y-%m-%d").date()
                (active if dt >= today else expired).__class__  # trick
                if dt >= today: active += 1
                else: expired += 1
            except ValueError:
                active += 1
    with open(DB_PATH, "r") as f:
        meta = json.load(f)
    return total, active, expired, meta.get("updated", "未知")

# ── 交互式输入 ────────────────────────────────────────────
def ask_type():
    print(f"\n{bold('📚 作品类型')}")
    for k, (_, label) in TYPE_CHOICES.items():
        print(f"  {cyan(k.rjust(2))}. {label}")
    while True:
        choice = input(f"\n请选择 [1-{len(TYPE_CHOICES)}]: ").strip()
        if choice in TYPE_CHOICES:
            t, label = TYPE_CHOICES[choice]
            print(f"  → {green(label)}")
            return t
        valid = [v[0] for v in TYPE_CHOICES.values()]
        if choice in valid: return choice
        print(red("  无效选择，请重新输入"))

def ask_words():
    print(f"\n{bold('📏 作品字数')} {dim('(英文单词数，诗歌可输入 0)')}")
    while True:
        raw = input("字数: ").strip()
        if not raw or raw == "0": return 0
        try:
            n = int(raw)
            if n < 0: raise ValueError
            print(f"  → {green(f'{n} words')}")
            return n
        except ValueError:
            print(red("  请输入有效数字"))

def ask_budget():
    print(f"\n{bold('💰 投稿预算')} {dim('(美元，0 = 只看免费竞赛)')}")
    while True:
        raw = input("预算 (USD): ").strip()
        if not raw:
            print(f"  → {green('$50 (默认)')}")
            return 50
        try:
            n = float(raw)
            if n < 0: raise ValueError
            print(f"  → {green(f'${n:.0f}')}")
            return n
        except ValueError:
            print(red("  请输入有效数字"))

def ask_styles():
    print(f"\n{bold('🎨 风格标签')} {dim('(可多选，逗号分隔，直接回车跳过)')}")
    for k, v in STYLE_CHOICES.items():
        print(f"  {cyan(k.rjust(2))}. {v}")
    raw = input(f"\n选择 [如 1,3,5]: ").strip()
    if not raw: return []
    tags = []
    for part in raw.replace("，", ",").split(","):
        part = part.strip()
        if part in STYLE_CHOICES: tags.append(STYLE_CHOICES[part])
        elif part in STYLE_CHOICES.values(): tags.append(part)
    if tags: print(f"  → {green(', '.join(tags))}")
    return tags

def ask_experience():
    print(f"\n{bold('🎯 经验等级')}")
    for k, (_, label) in EXPERIENCE_CHOICES.items():
        print(f"  {cyan(k)}. {label}")
    while True:
        choice = input(f"\n选择 [1-3, 默认1]: ").strip() or "1"
        if choice in EXPERIENCE_CHOICES:
            exp, label = EXPERIENCE_CHOICES[choice]
            print(f"  → {green(label)}")
            return exp
        print(red("  无效选择"))

def ask_top_n():
    print(f"\n{bold('📊 显示数量')} {dim('(推荐竞赛数，默认 5)')}")
    raw = input("数量: ").strip()
    if not raw: return 5
    try: return max(1, min(int(raw), 30))
    except ValueError: return 5

# ── 格式化输出 ────────────────────────────────────────────
def format_results_color(results, work):
    lines = []
    lines.append("")
    lines.append(bold("=" * 60))
    lines.append(bold("📝 投稿匹配报告"))
    lines.append(bold("=" * 60))
    lines.append(f"作品类型: {cyan(SUBFIELD_CN.get(work.get('type', ''), work.get('type', 'N/A')))}")
    if work.get("word_count"):
        lines.append(f"字数: {cyan(str(work['word_count']))}")
    if work.get("style_tags"):
        lines.append(f"风格: {cyan(', '.join(work['style_tags']))}")
    lines.append(f"预算: {cyan('$' + str(work.get('max_fee_usd', 50)))}")
    lines.append(bold("=" * 60))

    if not results:
        lines.append("")
        lines.append(yellow("  😔 没有找到匹配的竞赛。"))
        lines.append(dim("  试试放宽条件？比如增加预算或换个类型。"))
        lines.append("")
        return "\n".join(lines)

    for i, r in enumerate(results, 1):
        lines.append("")
        lines.append(dim("─" * 55))
        s = r["score"]
        score_str = green(f"{s}分") if s >= 70 else yellow(f"{s}分") if s >= 50 else red(f"{s}分")
        name_display = r.get("name_cn") or r["name"]
        lines.append(f"  {bold(f'#{i}')} {bold(name_display)}  [{score_str}]")
        lines.append(f"     {dim(r['name'])}")

        deadline_str = r.get("deadline") or "见官网"
        if deadline_str not in ("见官网", "weekly", "quarterly", "rolling"):
            try:
                dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                days = (dl - date.today()).days
                if days <= 7:
                    deadline_str = red(f"{deadline_str} 🔥 仅剩{days}天!")
                elif days <= 14:
                    deadline_str = yellow(f"{deadline_str} ⏰ 剩{days}天")
                else:
                    deadline_str = f"{deadline_str} ({days}天)"
            except ValueError: pass
        lines.append(f"     📅 截止: {deadline_str}")
        lines.append(f"     🏆 奖金: {r.get('prize', 'N/A')}")

        fee = r.get("fee", {})
        fee_str = f"{fee.get('currency', '')} {fee['amount']}" if fee.get("amount") else green("免费")
        lines.append(f"     💰 费用: {fee_str}")
        lines.append(f"     ⭐ 声望: {r.get('prestige', '?')}/10 | 获奖概率: {r.get('win_prob', '?')}/10")
        lines.append(f"     🔗 {dim(r.get('url', ''))}")

        if r.get("reasons"):
            lines.append(f"     {green('✅')} {' | '.join(r['reasons'][:4])}")
        if r.get("warnings"):
            lines.append(f"     {yellow('⚠️')} {' | '.join(r['warnings'][:3])}")

    lines.append("")
    lines.append(dim("─" * 55))
    total, active, expired, updated = db_stats()
    lines.append(dim(f"共匹配 {len(results)} 个竞赛 | 数据库: {total} 条 (活跃 {active} / 已过期 {expired})"))
    lines.append(dim(f"数据更新: {updated} | 投稿前请确认官网最新信息"))
    lines.append("")
    return "\n".join(lines)

# ── 导出功能 ──────────────────────────────────────────────
def export_csv(results, work, filepath=None):
    """导出匹配结果为 CSV"""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["排名", "竞赛名(中)", "竞赛名(英)", "分数", "截止日期",
                      "奖金", "费用", "声望", "获奖概率", "链接", "推荐理由"])

    for i, r in enumerate(results, 1):
        name_cn = r.get("name_cn") or ""
        fee = r.get("fee", {})
        fee_str = f"{fee.get('currency','')} {fee.get('amount','')}" if fee.get("amount") else "免费"
        reasons = " | ".join(r.get("reasons", [])[:3])
        writer.writerow([
            i, name_cn, r["name"], r["score"], r.get("deadline", ""),
            r.get("prize", ""), fee_str, r.get("prestige", ""),
            r.get("win_prob", ""), r.get("url", ""), reasons
        ])

    content = output.getvalue()
    if filepath:
        with open(filepath, "w", encoding="utf-8-sig") as f:
            f.write(content)
        print(f"{green('✓')} 已导出到 {filepath}")
    else:
        fp = f"match-results-{date.today()}.csv"
        with open(fp, "w", encoding="utf-8-sig") as f:
            f.write(content)
        print(f"{green('✓')} 已导出到 {fp}")
    return content


def export_markdown(results, work, filepath=None):
    """导出匹配结果为 Markdown"""
    lines = []
    type_cn = SUBFIELD_CN.get(work.get("type", ""), work.get("type", ""))
    lines.append(f"# 投稿匹配报告")
    lines.append(f"")
    lines.append(f"- 作品类型: {type_cn}")
    if work.get("word_count"):
        lines.append(f"- 字数: {work['word_count']}")
    lines.append(f"- 预算: ${work.get('max_fee_usd', 50)}")
    lines.append(f"- 生成日期: {date.today()}")
    lines.append(f"")
    lines.append(f"| # | 竞赛 | 分数 | 截止 | 奖金 | 费用 | 链接 |")
    lines.append(f"|---|------|------|------|------|------|------|")

    for i, r in enumerate(results, 1):
        name = r.get("name_cn") or r["name"]
        fee = r.get("fee", {})
        fee_str = f"{fee.get('currency','')} {fee.get('amount','')}" if fee.get("amount") else "免费"
        dl = r.get("deadline", "")
        lines.append(f"| {i} | {name} | {r['score']} | {dl} | {r.get('prize','')} | {fee_str} | [链接]({r.get('url','')}) |")

    lines.append(f"")
    lines.append(f"---")
    total, active, _, updated = db_stats()
    lines.append(f"数据库: {total} 条 (活跃 {active}) | 更新: {updated}")

    content = "\n".join(lines)
    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{green('✓')} 已导出到 {filepath}")
    else:
        fp = f"match-results-{date.today()}.md"
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{green('✓')} 已导出到 {fp}")
    return content


# ── 新手引导 ──────────────────────────────────────────────
def is_first_run():
    """检查是否第一次运行"""
    return not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles.json"))


def onboarding():
    """第一次使用的新手引导"""
    print("")
    print(bold("╔══════════════════════════════════════════════╗"))
    print(bold("║  👋 欢迎使用投稿代理 — 智能竞赛匹配工具      ║"))
    print(bold("╚══════════════════════════════════════════════╝"))
    print()
    print("  这个工具帮你找到最适合的国际文学竞赛。")
    print("  只需告诉我你的作品信息，我来推荐。")
    print()
    total, active, _, _ = db_stats()
    print(f"  📊 数据库中有 {green(str(active))} 个活跃竞赛等你探索")
    print()
    print(dim("  三步上手:"))
    print(f"  {cyan('1.')} 告诉我你的作品类型和字数")
    print(f"  {cyan('2.')} 设定预算（0 = 只看免费竞赛）")
    print(f"  {cyan('3.')} 获得个性化推荐，保存档案下次直接用")
    print()

    try:
        ready = input(f"  准备好了吗？{dim('[回车开始]')} ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{dim('下次见！')}")
        sys.exit(0)

    # 走正常的交互流程
    try:
        work_type = ask_type()
        word_count = ask_words()
        budget = ask_budget()
        style_tags = ask_styles()
        experience = ask_experience()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{dim('已退出。')}")
        sys.exit(0)

    work = {
        "type": work_type,
        "word_count": word_count,
        "style_tags": style_tags,
        "max_fee_usd": budget,
        "experience": experience,
    }

    print(f"\n{dim('正在匹配...')}")
    results = recommend(work, top_n=5)
    print(format_results_color(results, work))

    # 引导保存档案
    print(bold("💡 小贴士：保存为档案后，下次用 match --profile 1 一键匹配"))
    interactive_save(work)

    # 引导追踪
    if results:
        print(f"\n{bold('💡 小贴士：看到心仪的竞赛？用 track add 记录投稿进度')}")
        track = input(f"{dim('要追踪某个竞赛吗？输入编号 (或回车跳过): ')}").strip()
        if track:
            try:
                idx = int(track) - 1
                if 0 <= idx < len(results):
                    r = results[idx]
                    interactive_add(
                        competition=r.get("name_cn") or r["name"],
                        url=r.get("url", ""),
                    )
            except (ValueError, IndexError):
                pass

    print(f"\n{bold('🎉 设置完成！')}")
    print(f"  常用命令:")
    print(f"  {cyan('python3 cli.py')}                  交互匹配")
    print(f"  {cyan('python3 cli.py match --profile 1')} 用档案匹配")
    print(f"  {cyan('python3 cli.py refresh')}           刷新数据库")
    print(f"  {cyan('python3 cli.py track list')}        查看投稿")
    print(f"  {cyan('python3 cli.py --help')}            完整帮助")
    print()


# ── 交互模式 ──────────────────────────────────────────────
def interactive_mode():
    print("")
    print(bold("╔══════════════════════════════════════════╗"))
    print(bold("║   📝 投稿代理 — 智能竞赛匹配工具 v2.1    ║"))
    print(bold("╚══════════════════════════════════════════╝"))
    total, active, _, updated = db_stats()
    print(dim(f"  帮助中国创作者找到最合适的国际文学竞赛"))
    print(dim(f"  数据库: {active} 个活跃竞赛 | 更新: {updated}"))
    print(dim("  Ctrl+C 随时退出"))

    # 检查是否有已保存的档案
    pdata = load_profiles()
    if pdata.get("profiles"):
        count = len(pdata["profiles"])
        print(f"\n{dim(f'发现 {count} 个已保存的作品档案')}")
        use_profile = input(f"{dim('使用已保存的档案？[y/N] ')}").strip().lower()
        if use_profile in ("y", "yes", "是"):
            work = interactive_load()
            if work:
                top_n = ask_top_n()
                print(f"\n{dim('正在匹配...')}")
                results = recommend(work, top_n=top_n)
                print(format_results_color(results, work))
                _post_match(results, work)
                return

    try:
        work_type = ask_type()
        word_count = ask_words()
        budget = ask_budget()
        style_tags = ask_styles()
        experience = ask_experience()
        top_n = ask_top_n()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{dim('已退出。')}")
        sys.exit(0)

    work = {
        "type": work_type,
        "word_count": word_count,
        "style_tags": style_tags,
        "max_fee_usd": budget,
        "experience": experience,
    }

    print(f"\n{dim('正在匹配...')}")
    results = recommend(work, top_n=top_n)
    print(format_results_color(results, work))

    # 匹配后操作
    _post_match(results, work)


def _post_match(results, work):
    """匹配完成后的操作：保存档案、添加追踪"""
    try:
        # 保存档案
        interactive_save(work)

        # 添加投稿追踪
        if results:
            track = input(f"\n{dim('要追踪某个竞赛的投稿吗？输入编号 (或回车跳过): ')}").strip()
            if track:
                try:
                    idx = int(track) - 1
                    if 0 <= idx < len(results):
                        r = results[idx]
                        interactive_add(
                            competition=r.get("name_cn") or r["name"],
                            url=r.get("url", ""),
                        )
                except (ValueError, IndexError):
                    pass

        # 再来一次
        again = input(f"\n{dim('再来一次？[y/N] ')}").strip().lower()
        if again in ("y", "yes", "是"):
            interactive_mode()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{dim('再见！')}")

# ── 命令行入口 ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="submission-agent",
        description="投稿代理 — 智能竞赛匹配工具 v2.1\n帮助中国创作者找到最合适的国际文学竞赛",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "子命令:\n"
            "  match     匹配竞赛 (默认)\n"
            "  refresh   从网络刷新竞赛数据库\n"
            "  profile   管理作品档案\n"
            "  track     投稿追踪\n"
            "  stats     数据库统计\n"
            "  calendar  截止日期日历\n"
            "  show      查看竞赛详情\n"
            "\n示例:\n"
            "  python3 cli.py                                    # 交互模式\n"
            "  python3 cli.py match -t flash_fiction -w 300       # 命令行匹配\n"
            "  python3 cli.py match --profile 1                  # 用档案匹配\n"
            "  python3 cli.py match --export csv                 # 导出为 CSV\n"
            "  python3 cli.py calendar -m 2 --free               # 未来2月免费竞赛\n"
            "  python3 cli.py show 1                             # 查看竞赛 #1\n"
            "  python3 cli.py show -s poetry                     # 搜索竞赛\n"
            "  python3 cli.py refresh                            # 刷新数据库\n"
            "  python3 cli.py profile list                       # 列出档案\n"
            "  python3 cli.py track list                         # 查看投稿\n"
            "  python3 cli.py stats                              # 数据库统计"
        ),
    )

    sub = parser.add_subparsers(dest="command")

    # ── match ──
    p_match = sub.add_parser("match", help="匹配竞赛")
    p_match.add_argument("-t", "--type", choices=[v[0] for v in TYPE_CHOICES.values()], help="作品类型")
    p_match.add_argument("-w", "--words", type=int, default=0, help="字数")
    p_match.add_argument("-b", "--budget", type=float, default=50, help="预算 (USD)")
    p_match.add_argument("-s", "--style", nargs="*", default=[], help="风格标签")
    p_match.add_argument("-e", "--experience", choices=["beginner","intermediate","advanced"], default="beginner")
    p_match.add_argument("-n", "--top", type=int, default=5, help="推荐数量")
    p_match.add_argument("--profile", type=int, help="使用已保存的档案编号")
    p_match.add_argument("--json", action="store_true", help="JSON 输出")
    p_match.add_argument("--export", choices=["csv", "md", "markdown"], help="导出格式 (csv/md)")

    # ── refresh ──
    p_refresh = sub.add_parser("refresh", help="刷新竞赛数据库")
    p_refresh.add_argument("--dry-run", action="store_true", help="预览模式，不写入")
    p_refresh.add_argument("--source", nargs="*", help="指定数据源 (pworg, reedsy)")

    # ── profile ──
    p_profile = sub.add_parser("profile", help="管理作品档案")
    p_profile.add_argument("action", nargs="?", default="list", choices=["list", "save", "delete", "match"])
    p_profile.add_argument("--id", type=int, help="档案编号")
    p_profile.add_argument("-t", "--type", dest="ptype", help="作品类型")
    p_profile.add_argument("-w", "--words", type=int, default=0, help="字数")
    p_profile.add_argument("-b", "--budget", type=float, default=50, help="预算")
    p_profile.add_argument("--title", help="档案名称")

    # ── track ──
    p_track = sub.add_parser("track", help="投稿追踪")
    p_track.add_argument("action", nargs="?", default="list", choices=["list", "add", "update", "remind", "stats"])
    p_track.add_argument("--id", type=int, help="投稿记录编号")
    p_track.add_argument("--status", help="筛选状态")
    p_track.add_argument("--competition", help="竞赛名称")

    # ── stats ──
    sub.add_parser("stats", help="数据库统计")

    # ── calendar ──
    p_cal = sub.add_parser("calendar", help="截止日期日历")
    p_cal.add_argument("-m", "--months", type=int, default=3, help="显示未来几个月 (默认3)")
    p_cal.add_argument("-t", "--type", dest="cal_type", help="按类型筛选")
    p_cal.add_argument("--free", action="store_true", help="只显示免费竞赛")

    # ── show ──
    p_show = sub.add_parser("show", help="查看竞赛详情")
    p_show.add_argument("contest_id", nargs="?", type=int, help="竞赛编号")
    p_show.add_argument("-s", "--search", help="按名称搜索")

    # ── 兼容旧参数 ──
    parser.add_argument("-t", "--type", choices=[v[0] for v in TYPE_CHOICES.values()], help="作品类型 (兼容旧版)")
    parser.add_argument("-w", "--words", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("-b", "--budget", type=float, default=50, help=argparse.SUPPRESS)
    parser.add_argument("-s", "--style", nargs="*", default=[], help=argparse.SUPPRESS)
    parser.add_argument("-e", "--experience", choices=["beginner","intermediate","advanced"], default="beginner", help=argparse.SUPPRESS)
    parser.add_argument("-n", "--top", type=int, default=5, help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--list-types", action="store_true", help="列出作品类型")
    parser.add_argument("--stats", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--refresh", action="store_true", help="刷新数据库 (兼容旧版)")
    parser.add_argument("-i", "--interactive", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # ── 兼容旧版 flags ──
    if args.list_types:
        print("\n支持的作品类型:")
        for _, (code, label) in TYPE_CHOICES.items():
            print(f"  {code:<25} {label}")
        sys.exit(0)

    if args.stats and not args.command:
        args.command = "stats"

    if args.refresh and not args.command:
        args.command = "refresh"

    # ── 路由 ──
    cmd = args.command

    if cmd == "refresh":
        do_refresh(dry_run=getattr(args, "dry_run", False),
                   sources=getattr(args, "source", None))

    elif cmd == "stats":
        cmd_stats()

    elif cmd == "profile":
        cmd_profile(args)

    elif cmd == "track":
        cmd_track(args)

    elif cmd == "match":
        cmd_match(args)

    elif cmd == "calendar":
        cmd_calendar(args)

    elif cmd == "show":
        cmd_show(args)

    elif args.type:
        # 兼容旧版: python3 cli.py -t flash_fiction -w 300
        work = {
            "type": args.type,
            "word_count": args.words,
            "style_tags": args.style,
            "max_fee_usd": args.budget,
            "experience": args.experience,
        }
        results = recommend(work, top_n=args.top)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(format_results_color(results, work))

    else:
        # 默认：第一次运行走引导，否则交互模式
        if is_first_run():
            onboarding()
        else:
            interactive_mode()


def cmd_stats():
    total, active, expired, updated = db_stats()
    comps = load_db()
    sf = {}
    for c in comps:
        s = c.get("subfield", "?")
        sf[s] = sf.get(s, 0) + 1
    free = sum(1 for c in comps if not (c.get("entry_fee", {}).get("amount") or 0))
    print(f"\n{bold('📊 竞赛数据库统计')}")
    print(f"  总条目: {total} | 活跃: {green(str(active))} | 已过期: {red(str(expired))}")
    print(f"  免费竞赛: {free}")
    print(f"  更新日期: {updated}")
    print(f"\n  {bold('类别分布:')}")
    for k, v in sorted(sf.items(), key=lambda x: -x[1]):
        label = SUBFIELD_CN.get(k, k)
        print(f"    {label:<15} {v}")
    print()


def cmd_match(args):
    # 从档案加载
    if args.profile:
        p = get_profile(args.profile)
        if not p:
            print(red(f"未找到档案 #{args.profile}"))
            sys.exit(1)
        work = profile_to_work(p)
        print(f"{green('✓')} 使用档案: {bold(p.get('title', '未命名'))}")
    elif args.type:
        work = {
            "type": args.type,
            "word_count": args.words,
            "style_tags": args.style,
            "max_fee_usd": args.budget,
            "experience": args.experience,
        }
    else:
        interactive_mode()
        return

    results = recommend(work, top_n=args.top)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif getattr(args, "export", None):
        fmt = args.export
        if fmt == "csv":
            export_csv(results, work)
        elif fmt in ("md", "markdown"):
            export_markdown(results, work)
        # 同时也打印到终端
        print(format_results_color(results, work))
    else:
        print(format_results_color(results, work))


def cmd_profile(args):
    action = args.action or "list"
    if action == "list":
        list_profiles()
    elif action == "save":
        if not args.ptype:
            print(red("需要指定 --type"))
            sys.exit(1)
        work = {
            "type": args.ptype,
            "word_count": args.words,
            "max_fee_usd": args.budget,
            "style_tags": [],
            "experience": "beginner",
        }
        save_profile(work, title=args.title)
    elif action == "delete":
        if not args.id:
            print(red("需要指定 --id"))
            sys.exit(1)
        delete_profile(args.id)
    elif action == "match":
        if not args.id:
            print(red("需要指定 --id"))
            sys.exit(1)
        p = get_profile(args.id)
        if not p:
            print(red(f"未找到档案 #{args.id}"))
            sys.exit(1)
        work = profile_to_work(p)
        results = recommend(work, top_n=5)
        print(format_results_color(results, work))


def cmd_track(args):
    action = args.action or "list"
    if action == "list":
        list_submissions(status_filter=args.status)
    elif action == "add":
        interactive_add(competition=args.competition)
    elif action == "update":
        if args.id and args.status:
            update_status(args.id, args.status)
        else:
            interactive_update()
    elif action == "remind":
        show_reminders()
    elif action == "stats":
        submission_stats()


def cmd_calendar(args):
    """截止日期日历视图"""
    from datetime import timedelta
    comps = load_db()
    today = date.today()
    months = args.months
    cutoff = today + timedelta(days=months * 30)

    # 收集活跃竞赛
    entries = []
    for c in comps:
        dl = c.get("deadline", "")
        if not dl or dl in ("weekly", "quarterly", "rolling"):
            continue
        if c.get("status") in ("closed", "expired"):
            continue
        try:
            dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
        except ValueError:
            continue
        if dl_date < today or dl_date > cutoff:
            continue

        # 类型筛选
        if args.cal_type:
            sf = c.get("subfield", "")
            if args.cal_type not in sf and args.cal_type not in c.get("field", ""):
                continue

        # 免费筛选
        if args.free:
            fee = c.get("entry_fee", {}).get("amount") or 0
            if fee > 0:
                continue

        entries.append((dl_date, c))

    entries.sort(key=lambda x: x[0])

    if not entries:
        print(f"\n{yellow('未来 {months} 个月内没有匹配的竞赛。')}")
        return

    print(f"\n{bold('📅 竞赛截止日期日历')}")
    print(f"{dim(f'{today} → {cutoff} ({months}个月)')}")
    print()

    current_month = None
    for dl_date, c in entries:
        month_key = dl_date.strftime("%Y年%m月")
        if month_key != current_month:
            current_month = month_key
            print(f"  {bold(month_key)}")
            print(f"  {'─' * 50}")

        days = (dl_date - today).days
        name = c.get("name_cn") or c["name"]
        fee = c.get("entry_fee", {}).get("amount") or 0
        prize = c.get("prize", {}).get("first", 0) or 0
        sf = SUBFIELD_CN.get(c.get("subfield", ""), c.get("subfield", ""))

        # 日期颜色
        if days <= 7:
            date_str = red(f"{dl_date.strftime('%m/%d')} 🔥")
        elif days <= 14:
            date_str = yellow(f"{dl_date.strftime('%m/%d')} ⏰")
        else:
            date_str = dl_date.strftime("%m/%d")

        # 费用标记
        fee_tag = green("免费") if fee == 0 else f"${fee}"

        line = f"    {date_str}  {name[:30]:<30}  {dim(sf):<8}  {fee_tag}"
        if prize:
            line += f"  {dim(f'奖${prize:,}')}"
        print(line)

    print(f"\n{dim(f'共 {len(entries)} 个竞赛')}")
    print()


def cmd_show(args):
    """查看竞赛详情"""
    comps = load_db()

    comp = None
    if args.contest_id:
        for c in comps:
            if c["id"] == args.contest_id:
                comp = c
                break
        if not comp:
            print(red(f"未找到竞赛 #{args.contest_id}"))
            sys.exit(1)
    elif getattr(args, "search", None):
        query = args.search.lower()
        matches = []
        for c in comps:
            if query in c["name"].lower() or query in (c.get("name_cn") or "").lower():
                matches.append(c)
        if not matches:
            print(red(f"未找到包含 \"{args.search}\" 的竞赛"))
            sys.exit(1)
        if len(matches) == 1:
            comp = matches[0]
        else:
            print(f"\n找到 {len(matches)} 个匹配:")
            for c in matches[:10]:
                name = c.get("name_cn") or c["name"]
                cid = c["id"]
                print(f"  {cyan(f'#{cid}')} {name}")
            print(f"\n{dim('用 show <编号> 查看详情')}")
            return
    else:
        print(red("请指定竞赛编号或搜索关键词"))
        print(dim("  用法: cli.py show 1  或  cli.py show -s poetry"))
        sys.exit(1)

    # 显示详情
    name_cn = comp.get("name_cn") or ""
    name_en = comp["name"]
    today = date.today()

    print(f"\n{bold('═' * 55)}")
    if name_cn:
        print(f"  {bold(name_cn)}")
    print(f"  {bold(name_en)}")
    cid = comp["id"]
    print(f"  {dim(f'#{cid}')}")
    print(f"{bold('═' * 55)}")

    # 基本信息
    sf = SUBFIELD_CN.get(comp.get("subfield", ""), comp.get("subfield", ""))
    print(f"\n  📚 类别: {sf}")

    # 截止日期
    dl = comp.get("deadline", "")
    if dl and dl not in ("weekly", "quarterly", "rolling"):
        try:
            dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
            days = (dl_date - today).days
            if days < 0:
                dl_str = red(f"{dl} (已过期 {-days} 天)")
            elif days <= 7:
                dl_str = red(f"{dl} 🔥 仅剩 {days} 天!")
            elif days <= 14:
                dl_str = yellow(f"{dl} ⏰ 剩 {days} 天")
            else:
                dl_str = f"{dl} ({days} 天)"
        except ValueError:
            dl_str = dl
    else:
        dl_str = dl or "见官网"
    print(f"  📅 截止: {dl_str}")

    # 奖金
    prize = comp.get("prize", {})
    if prize.get("details"):
        print(f"  🏆 奖金: {prize['details']}")
    elif prize.get("first"):
        print(f"  🏆 奖金: ${prize['first']:,}")

    # 费用
    fee = comp.get("entry_fee", {})
    fee_amount = fee.get("amount") or 0
    if fee_amount:
        fee_str = f"{fee.get('currency', 'USD')} {fee_amount}"
        if fee.get("note"):
            fee_str += f" ({fee['note']})"
    else:
        fee_str = green("免费")
    print(f"  💰 费用: {fee_str}")

    # 性价比 (ROI)
    prize_first = prize.get("first", 0) or 0
    if fee_amount > 0 and prize_first > 0:
        roi = prize_first / fee_amount
        if roi >= 100:
            roi_str = green(f"{roi:.0f}x (极高)")
        elif roi >= 50:
            roi_str = f"{roi:.0f}x (高)"
        elif roi >= 20:
            roi_str = f"{roi:.0f}x (中)"
        else:
            roi_str = dim(f"{roi:.0f}x (低)")
        print(f"  📈 性价比: {roi_str}")

    # 字数限制
    wl = comp.get("word_limit")
    if wl and wl.get("max"):
        wl_str = f"最多 {wl['max']} {wl.get('unit', 'words')}"
        if wl.get("min"):
            wl_str = f"{wl['min']}-{wl['max']} {wl.get('unit', 'words')}"
        if wl.get("note"):
            wl_str += f" ({wl['note']})"
        print(f"  📏 字数: {wl_str}")

    # 评分
    prestige = comp.get("prestige_score", 0)
    win_prob = comp.get("win_probability", {}).get("overall_score", 0)
    print(f"  ⭐ 声望: {prestige}/10 | 获奖概率: {win_prob}/10")

    # 中国创作者适配
    fit = comp.get("chinese_creator_fit", {})
    if fit:
        fit_score = fit.get("score", 3)
        print(f"  🇨🇳 适配度: {fit_score}/5")
        if fit.get("advantages"):
            print(f"     优势: {', '.join(fit['advantages'])}")
        if fit.get("recommendation"):
            print(f"     建议: {fit['recommendation']}")

    # 风格标签
    style_tags = comp.get("style_profile", {}).get("style_tags", [])
    if style_tags:
        style_cn = {
            "literary": "文学性", "experimental": "实验性", "contemporary": "当代",
            "science_fiction": "科幻", "fantasy": "奇幻", "nature": "自然",
            "contemplative": "沉思", "personal": "个人", "narrative": "叙事",
            "open": "开放", "innovative": "创新", "humorous": "幽默",
            "dark": "暗黑", "traditional": "传统", "political": "政治",
            "accessible": "易读", "inclusive": "包容", "diverse": "多元",
            "emotional_tension": "情感张力", "international": "国际",
            "flash": "闪小说", "everyday_poetics": "日常诗意",
        }
        tags_str = ", ".join(style_cn.get(t, t) for t in style_tags)
        print(f"  🎨 风格: {tags_str}")

    # 链接
    print(f"\n  🔗 官网: {comp.get('url', '')}")
    if comp.get("submission_url") and comp["submission_url"] != comp.get("url"):
        print(f"  📤 投稿: {comp['submission_url']}")

    # 其他信息
    extras = []
    if comp.get("judge"):
        extras.append(f"评委: {comp['judge']}")
    if comp.get("publication"):
        extras.append(f"发表: {comp['publication']}")
    if comp.get("theme"):
        extras.append(f"主题: {comp['theme']}")
    if comp.get("anonymous_review"):
        extras.append("匿名评审")
    if comp.get("previously_published_ok"):
        extras.append("接受已发表作品")
    if comp.get("simultaneous_ok"):
        extras.append("允许同时投稿")

    if extras:
        print(f"\n  {dim(' | '.join(extras))}")

    print()


if __name__ == "__main__":
    main()
