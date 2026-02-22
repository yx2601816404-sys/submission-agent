#!/usr/bin/env python3
"""
投稿追踪模块
记录已投稿的竞赛、状态、截止日期提醒
"""

import json
import os
import sys
from datetime import datetime, date

TRACKER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "submissions.json")


def _c(text, code):
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def _bold(t): return _c(t, "1")
def _green(t): return _c(t, "32")
def _yellow(t): return _c(t, "33")
def _red(t): return _c(t, "31")
def _cyan(t): return _c(t, "36")
def _dim(t): return _c(t, "2")

STATUS_LABELS = {
    "draft":     ("📝", "草稿"),
    "submitted": ("📤", "已投递"),
    "pending":   ("⏳", "审核中"),
    "shortlisted": ("⭐", "入围"),
    "accepted":  ("🎉", "已录用"),
    "rejected":  ("❌", "已拒"),
    "withdrawn": ("↩️", "已撤回"),
}


def load_tracker():
    if not os.path.exists(TRACKER_PATH):
        return {"submissions": []}
    with open(TRACKER_PATH, "r") as f:
        return json.load(f)


def save_tracker(data):
    with open(TRACKER_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_submission(competition_name, work_title="", deadline=None, fee=None,
                   status="draft", notes="", competition_url=""):
    """添加一条投稿记录"""
    data = load_tracker()
    sid = len(data["submissions"]) + 1

    entry = {
        "id": sid,
        "competition": competition_name,
        "competition_url": competition_url,
        "work_title": work_title,
        "status": status,
        "deadline": deadline,
        "fee_paid": fee,
        "submitted_date": str(date.today()) if status == "submitted" else None,
        "result_date": None,
        "notes": notes,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "history": [
            {"status": status, "date": str(date.today()), "note": "创建记录"}
        ],
    }

    data["submissions"].append(entry)
    save_tracker(data)
    print(f"\n{_green('✓')} 已添加投稿记录 #{sid}: {competition_name}")
    return entry


def update_status(sid, new_status, note=""):
    """更新投稿状态"""
    data = load_tracker()
    for sub in data["submissions"]:
        if sub["id"] == sid:
            old_status = sub["status"]
            sub["status"] = new_status
            sub["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            sub["history"].append({
                "status": new_status,
                "date": str(date.today()),
                "note": note or f"{old_status} → {new_status}",
            })
            if new_status == "submitted" and not sub.get("submitted_date"):
                sub["submitted_date"] = str(date.today())
            if new_status in ("accepted", "rejected"):
                sub["result_date"] = str(date.today())
            save_tracker(data)
            emoji, label = STATUS_LABELS.get(new_status, ("", new_status))
            print(f"{_green('✓')} #{sid} 状态更新: {emoji} {label}")
            return True
    print(f"{_red('未找到投稿记录')} #{sid}")
    return False


def list_submissions(status_filter=None):
    """列出投稿记录"""
    data = load_tracker()
    subs = data.get("submissions", [])

    if status_filter:
        subs = [s for s in subs if s["status"] == status_filter]

    if not subs:
        print(f"\n{_yellow('没有投稿记录。')}")
        print(f"{_dim('使用 --track 添加投稿记录。')}")
        return []

    # 按状态分组
    groups = {}
    for s in subs:
        st = s["status"]
        groups.setdefault(st, []).append(s)

    # 显示顺序
    order = ["draft", "submitted", "pending", "shortlisted", "accepted", "rejected", "withdrawn"]
    today = date.today()

    print(f"\n{_bold('📋 投稿追踪看板')}")
    print(f"{_dim('─' * 55)}")

    # 统计栏
    total = len(subs)
    active = sum(1 for s in subs if s["status"] in ("draft", "submitted", "pending", "shortlisted"))
    won = sum(1 for s in subs if s["status"] == "accepted")
    print(f"  总计: {total} | 进行中: {_cyan(str(active))} | 已录用: {_green(str(won))}")
    print()

    for st in order:
        if st not in groups:
            continue
        emoji, label = STATUS_LABELS.get(st, ("", st))
        print(f"  {_bold(f'{emoji} {label}')} ({len(groups[st])})")

        for s in groups[st]:
            sid = s["id"]
            comp = s["competition"]
            work = s.get("work_title", "")
            dl = s.get("deadline")

            # 截止日期提醒
            dl_str = ""
            if dl:
                try:
                    dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
                    days = (dl_date - today).days
                    if days < 0:
                        dl_str = _red(f" [已过期{-days}天]")
                    elif days <= 7:
                        dl_str = _red(f" [🔥 {days}天]")
                    elif days <= 14:
                        dl_str = _yellow(f" [⏰ {days}天]")
                    else:
                        dl_str = _dim(f" [{days}天]")
                except ValueError:
                    pass

            line = f"    #{sid} {comp}"
            if work:
                line += f" — {_dim(work)}"
            line += dl_str
            print(line)

            if s.get("notes"):
                print(f"       {_dim(s['notes'])}")

        print()

    return subs


def get_deadlines(days_ahead=30):
    """获取即将到期的投稿"""
    data = load_tracker()
    today = date.today()
    upcoming = []

    for s in data.get("submissions", []):
        if s["status"] not in ("draft", "submitted", "pending"):
            continue
        dl = s.get("deadline")
        if not dl:
            continue
        try:
            dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
            days = (dl_date - today).days
            if 0 <= days <= days_ahead:
                upcoming.append((days, s))
        except ValueError:
            continue

    upcoming.sort(key=lambda x: x[0])
    return upcoming


def show_reminders():
    """显示截止日期提醒"""
    upcoming = get_deadlines(30)
    if not upcoming:
        print(f"\n{_green('✓')} 未来30天内没有即将到期的投稿。")
        return

    print(f"\n{_bold('⏰ 截止日期提醒')}")
    print(f"{_dim('─' * 50)}")
    for days, s in upcoming:
        comp = s["competition"]
        if days == 0:
            print(f"  {_red('🔥 今天!')} {comp}")
        elif days <= 3:
            print(f"  {_red(f'🔥 {days}天')} {comp}")
        elif days <= 7:
            print(f"  {_yellow(f'⏰ {days}天')} {comp}")
        else:
            print(f"  {_dim(f'📅 {days}天')} {comp}")
    print()


def interactive_add(competition=None, url=None):
    """交互式添加投稿记录"""
    try:
        if not competition:
            competition = input(f"\n{_bold('竞赛名称')}: ").strip()
            if not competition:
                print(_dim("已取消。"))
                return None

        work_title = input(f"{_dim('作品标题 (可选): ')}").strip()
        deadline = input(f"{_dim('截止日期 (YYYY-MM-DD, 可选): ')}").strip() or None
        fee = input(f"{_dim('已付费用 (USD, 可选): ')}").strip()
        fee = float(fee) if fee else None

        print(f"\n{_bold('投稿状态:')}")
        for i, (key, (emoji, label)) in enumerate(STATUS_LABELS.items(), 1):
            print(f"  {_cyan(str(i))}. {emoji} {label}")
        st_choice = input(f"\n选择 [1-7, 默认1]: ").strip() or "1"
        status_keys = list(STATUS_LABELS.keys())
        try:
            status = status_keys[int(st_choice) - 1]
        except (ValueError, IndexError):
            status = "draft"

        notes = input(f"{_dim('备注 (可选): ')}").strip()

        return add_submission(
            competition_name=competition,
            work_title=work_title,
            deadline=deadline,
            fee=fee,
            status=status,
            notes=notes,
            competition_url=url or "",
        )
    except (KeyboardInterrupt, EOFError):
        print(f"\n{_dim('已取消。')}")
        return None


def interactive_update():
    """交互式更新投稿状态"""
    subs = list_submissions()
    if not subs:
        return

    try:
        sid = input(f"\n要更新哪条记录？输入编号: ").strip()
        if not sid:
            return
        sid = int(sid)

        print(f"\n{_bold('新状态:')}")
        for i, (key, (emoji, label)) in enumerate(STATUS_LABELS.items(), 1):
            print(f"  {_cyan(str(i))}. {emoji} {label}")
        st_choice = input(f"\n选择: ").strip()
        status_keys = list(STATUS_LABELS.keys())
        try:
            new_status = status_keys[int(st_choice) - 1]
        except (ValueError, IndexError):
            print(_red("无效选择。"))
            return

        note = input(f"{_dim('备注 (可选): ')}").strip()
        update_status(sid, new_status, note)
    except (ValueError, KeyboardInterrupt, EOFError):
        print(f"\n{_dim('已取消。')}")


def submission_stats():
    """投稿统计"""
    data = load_tracker()
    subs = data.get("submissions", [])
    if not subs:
        print(f"\n{_yellow('没有投稿记录。')}")
        return

    total = len(subs)
    by_status = {}
    total_fees = 0
    for s in subs:
        st = s["status"]
        by_status[st] = by_status.get(st, 0) + 1
        if s.get("fee_paid"):
            total_fees += s["fee_paid"]

    print(f"\n{_bold('📊 投稿统计')}")
    print(f"  总投稿: {total}")
    for st, count in by_status.items():
        emoji, label = STATUS_LABELS.get(st, ("", st))
        print(f"  {emoji} {label}: {count}")
    if total_fees:
        print(f"  💰 总费用: ${total_fees:.0f}")

    # 录用率
    decided = by_status.get("accepted", 0) + by_status.get("rejected", 0)
    if decided > 0:
        rate = by_status.get("accepted", 0) / decided * 100
        print(f"  📈 录用率: {rate:.0f}% ({by_status.get('accepted', 0)}/{decided})")
    print()
