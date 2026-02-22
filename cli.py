#!/usr/bin/env python3
"""
投稿代理 CLI — 智能竞赛匹配工具
用法:
  交互模式:  python3 cli.py
  命令行模式: python3 cli.py --type flash_fiction --words 300 --budget 20
  帮助:      python3 cli.py --help
"""

import argparse
import json
import sys
import os
from datetime import datetime, date

# 确保能导入 matcher
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matcher import recommend, format_results, load_db, DB_PATH

# ── 类型映射 ──────────────────────────────────────────────
TYPE_CHOICES = {
    "1": ("flash_fiction",          "闪小说 (Flash Fiction)"),
    "2": ("short_story",            "短篇小说 (Short Story)"),
    "3": ("poetry",                 "诗歌 (Poetry)"),
    "4": ("novel",                  "长篇小说 (Novel)"),
    "5": ("science_fiction",        "科幻/奇幻 (Sci-Fi / Fantasy)"),
    "6": ("essay",                  "散文/随笔 (Essay)"),
    "7": ("memoir",                 "回忆录 (Memoir)"),
    "8": ("nonfiction",             "非虚构 (Nonfiction)"),
    "9": ("screenplay",             "编剧/剧本 (Screenplay)"),
    "10": ("novella",               "中篇小说 (Novella)"),
    "11": ("children",              "儿童文学 (Children's)"),
}

STYLE_CHOICES = {
    "1": "literary",
    "2": "contemporary",
    "3": "experimental",
    "4": "traditional",
    "5": "nature",
    "6": "contemplative",
    "7": "humorous",
    "8": "dark",
    "9": "science_fiction",
    "10": "imaginative",
}

EXPERIENCE_CHOICES = {
    "1": ("beginner",      "新手 — 没投过或投过 1-2 次"),
    "2": ("intermediate",  "进阶 — 投过几次，可能有入围/发表"),
    "3": ("advanced",      "资深 — 多次获奖或发表经历"),
}


def color(text, code):
    """ANSI 颜色，非 TTY 时不着色"""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(text):
    return color(text, "1")


def cyan(text):
    return color(text, "36")


def green(text):
    return color(text, "32")


def yellow(text):
    return color(text, "33")


def red(text):
    return color(text, "31")


def dim(text):
    return color(text, "2")


def db_stats():
    """获取数据库实时统计"""
    comps = load_db()
    today = date.today()
    total = len(comps)
    active = 0
    expired = 0
    for c in comps:
        dl = c.get("deadline", "")
        if not dl or dl in ("weekly", "quarterly", "rolling"):
            active += 1
        else:
            try:
                dt = datetime.strptime(dl, "%Y-%m-%d").date()
                if dt >= today:
                    active += 1
                else:
                    expired += 1
            except ValueError:
                active += 1
    # 获取更新日期
    with open(DB_PATH, "r") as f:
        meta = json.load(f)
    updated = meta.get("updated", "未知")
    return total, active, expired, updated


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
        # 也接受直接输入英文类型名
        valid_types = [v[0] for v in TYPE_CHOICES.values()]
        if choice in valid_types:
            return choice
        print(red("  无效选择，请重新输入"))


def ask_words():
    print(f"\n{bold('📏 作品字数')} {dim('(英文单词数，诗歌可输入 0)')}")
    while True:
        raw = input("字数: ").strip()
        if not raw or raw == "0":
            return 0
        try:
            n = int(raw)
            if n < 0:
                raise ValueError
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
            if n < 0:
                raise ValueError
            print(f"  → {green(f'${n:.0f}')}")
            return n
        except ValueError:
            print(red("  请输入有效数字"))


def ask_styles():
    print(f"\n{bold('🎨 风格标签')} {dim('(可多选，逗号分隔，直接回车跳过)')}")
    for k, v in STYLE_CHOICES.items():
        print(f"  {cyan(k.rjust(2))}. {v}")
    raw = input(f"\n选择 [如 1,3,5]: ").strip()
    if not raw:
        return []
    tags = []
    for part in raw.replace("，", ",").split(","):
        part = part.strip()
        if part in STYLE_CHOICES:
            tags.append(STYLE_CHOICES[part])
        elif part in STYLE_CHOICES.values():
            tags.append(part)
    if tags:
        print(f"  → {green(', '.join(tags))}")
    return tags


def ask_experience():
    print(f"\n{bold('🎯 经验等级')}")
    for k, (_, label) in EXPERIENCE_CHOICES.items():
        print(f"  {cyan(k)}. {label}")
    while True:
        choice = input(f"\n选择 [1-3, 默认1]: ").strip()
        if not choice:
            choice = "1"
        if choice in EXPERIENCE_CHOICES:
            exp, label = EXPERIENCE_CHOICES[choice]
            print(f"  → {green(label)}")
            return exp
        print(red("  无效选择"))


def ask_top_n():
    print(f"\n{bold('📊 显示数量')} {dim('(推荐竞赛数，默认 5)')}")
    raw = input("数量: ").strip()
    if not raw:
        return 5
    try:
        n = int(raw)
        return max(1, min(n, 30))
    except ValueError:
        return 5


# ── 格式化输出（带颜色） ──────────────────────────────────
def format_results_color(results, work):
    """带 ANSI 颜色的格式化输出"""
    lines = []
    lines.append("")
    lines.append(bold("=" * 60))
    lines.append(bold("📝 投稿匹配报告"))
    lines.append(bold("=" * 60))
    lines.append(f"作品类型: {cyan(work.get('type', 'N/A'))}")
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

        # 分数颜色
        s = r["score"]
        if s >= 70:
            score_str = green(f"{s}分")
        elif s >= 50:
            score_str = yellow(f"{s}分")
        else:
            score_str = red(f"{s}分")

        name_display = r.get("name_cn") or r["name"]
        lines.append(f"  {bold(f'#{i}')} {bold(name_display)}  [{score_str}]")
        lines.append(f"     {dim(r['name'])}")

        # 关键信息行
        deadline_str = r.get("deadline") or "见官网"
        # 截止日期紧急度标记
        if deadline_str not in ("见官网", "weekly", "quarterly", "rolling"):
            try:
                dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                days = (dl - date.today()).days
                if days <= 7:
                    deadline_str = red(f"{deadline_str} 🔥 仅剩{days}天!")
                elif days <= 14:
                    deadline_str = yellow(f"{deadline_str} ⏰ 剩{days}天")
                elif days <= 30:
                    deadline_str = f"{deadline_str} ({days}天)"
                else:
                    deadline_str = f"{deadline_str} ({days}天)"
            except ValueError:
                pass
        lines.append(f"     📅 截止: {deadline_str}")
        lines.append(f"     🏆 奖金: {r.get('prize', 'N/A')}")

        fee = r.get("fee", {})
        if fee.get("amount"):
            fee_str = f"{fee.get('currency', '')} {fee['amount']}"
        else:
            fee_str = green("免费")
        lines.append(f"     💰 费用: {fee_str}")

        lines.append(
            f"     ⭐ 声望: {r.get('prestige', '?')}/10 | "
            f"获奖概率: {r.get('win_prob', '?')}/10"
        )
        lines.append(f"     🔗 {dim(r.get('url', ''))}")

        # 推荐理由
        if r.get("reasons"):
            reasons_str = " | ".join(r["reasons"][:4])
            lines.append(f"     {green('✅')} {reasons_str}")

        # 风险提示
        if r.get("warnings"):
            warnings_str = " | ".join(r["warnings"][:3])
            lines.append(f"     {yellow('⚠️')} {warnings_str}")

    lines.append("")
    lines.append(dim("─" * 55))
    total, active, expired, updated = db_stats()
    lines.append(dim(f"共匹配 {len(results)} 个竞赛 | 数据库: {total} 条 (活跃 {active} / 已过期 {expired})"))
    lines.append(dim(f"数据更新: {updated} | 投稿前请确认官网最新信息"))
    lines.append("")
    return "\n".join(lines)


# ── 交互模式主流程 ────────────────────────────────────────
def interactive_mode():
    print("")
    print(bold("╔══════════════════════════════════════════╗"))
    print(bold("║   📝 投稿代理 — 智能竞赛匹配工具 v1.1    ║"))
    print(bold("╚══════════════════════════════════════════╝"))
    total, active, expired, updated = db_stats()
    print(dim(f"  帮助中国创作者找到最合适的国际文学竞赛"))
    print(dim(f"  数据库: {active} 个活跃竞赛 | 更新: {updated}"))
    print(dim("  Ctrl+C 随时退出"))

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

    # 询问是否继续
    try:
        again = input(f"{dim('再来一次？[y/N] ')}").strip().lower()
        if again in ("y", "yes", "是"):
            interactive_mode()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{dim('再见！')}")


# ── 命令行模式 ────────────────────────────────────────────
def cli_mode():
    parser = argparse.ArgumentParser(
        prog="submission-agent",
        description="投稿代理 — 智能竞赛匹配工具\n帮助中国创作者找到最合适的国际文学竞赛",
        epilog="示例:\n"
               "  python3 cli.py                                    # 交互模式\n"
               "  python3 cli.py --type flash_fiction --words 300    # 命令行模式\n"
               "  python3 cli.py --type poetry --budget 0            # 只看免费诗歌竞赛\n"
               "  python3 cli.py --stats                             # 查看数据库统计",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t", "--type",
        choices=[v[0] for v in TYPE_CHOICES.values()],
        help="作品类型",
    )
    parser.add_argument(
        "-w", "--words",
        type=int, default=0,
        help="作品字数 (英文单词数)",
    )
    parser.add_argument(
        "-b", "--budget",
        type=float, default=50,
        help="投稿预算 (USD, 默认50)",
    )
    parser.add_argument(
        "-s", "--style",
        nargs="*", default=[],
        help="风格标签 (如 literary contemporary)",
    )
    parser.add_argument(
        "-e", "--experience",
        choices=["beginner", "intermediate", "advanced"],
        default="beginner",
        help="经验等级 (默认 beginner)",
    )
    parser.add_argument(
        "-n", "--top",
        type=int, default=5,
        help="显示推荐数量 (默认5)",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="进入交互模式",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式 (方便程序调用)",
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="列出所有支持的作品类型",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示数据库统计信息",
    )

    args = parser.parse_args()

    # 列出类型
    if args.list_types:
        print("\n支持的作品类型:")
        for _, (code, label) in TYPE_CHOICES.items():
            print(f"  {code:<25} {label}")
        sys.exit(0)

    # 数据库统计
    if args.stats:
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
            print(f"    {k:<25} {v}")
        print()
        sys.exit(0)

    # 交互模式
    if args.interactive or args.type is None:
        interactive_mode()
        return

    # 命令行模式
    work = {
        "type": args.type,
        "word_count": args.words,
        "style_tags": args.style,
        "max_fee_usd": args.budget,
        "experience": args.experience,
    }

    results = recommend(work, top_n=args.top)

    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_results_color(results, work))


if __name__ == "__main__":
    cli_mode()
