#!/usr/bin/env python3
"""
竞赛数据库实时刷新模块
从 pw.org、Reedsy 等源爬取最新竞赛，合并到 competitions.json
"""

import json
import re
import sys
import os
from datetime import datetime, date
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser
from translator import auto_translate_name

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "competitions.json")

# ── 颜色 ──────────────────────────────────────────────────
def _c(text, code):
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def _bold(t): return _c(t, "1")
def _green(t): return _c(t, "32")
def _yellow(t): return _c(t, "33")
def _red(t): return _c(t, "31")
def _dim(t): return _c(t, "2")


def fetch_url(url, timeout=15):
    """用 urllib 抓取网页内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SubmissionAgent/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        print(f"  {_red('✗')} 抓取失败: {url} — {e}")
        return None


def load_db():
    with open(DB_PATH, "r") as f:
        return json.load(f)


def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def existing_names(data):
    names = set()
    for c in data["competitions"]:
        names.add(c["name"].lower().strip())
        if c.get("name_cn"):
            names.add(c["name_cn"].lower().strip())
    return names


def next_id(data):
    return max(c["id"] for c in data["competitions"]) + 1


def make_entry(id, name, name_cn, subfield, url, deadline, fee_amount, fee_currency,
               prize_details, prize_first=0, word_max=None, prestige=5, win_prob=5,
               fit_score=3, fit_advantages=None, fit_recommendation=""):
    """创建标准竞赛条目"""
    return {
        "id": id,
        "name": name,
        "name_cn": name_cn,
        "field": "literature",
        "subfield": subfield,
        "url": url,
        "submission_url": url,
        "status": "open",
        "deadline": deadline,
        "result_date": None,
        "frequency": "annual",
        "entry_fee": {"amount": fee_amount, "currency": fee_currency},
        "prize": {"first": prize_first, "currency": fee_currency or "USD", "details": prize_details},
        "publication": None,
        "word_limit": {"min": None, "max": word_max, "unit": "words"} if word_max else None,
        "language": "en",
        "nationality_restriction": None,
        "age_restriction": None,
        "experience_restriction": None,
        "theme": None,
        "simultaneous_ok": None,
        "previously_published_ok": False,
        "anonymous_review": True,
        "ai_policy": None,
        "submission_method": "online",
        "submission_platform": "submittable",
        "judge": None,
        "prestige_score": prestige,
        "style_profile": {
            "style_tags": ["open", "literary"],
            "judge_preferences": None,
            "keywords": [],
            "past_winner_traits": None
        },
        "win_probability": {
            "competition_density": 5,
            "competitor_quality": 5,
            "estimated_submissions": None,
            "shortlist_rate": None,
            "overall_score": win_prob
        },
        "chinese_creator_fit": {
            "score": fit_score,
            "advantages": fit_advantages or [],
            "disadvantages": [],
            "recommendation": fit_recommendation
        }
    }


# ── 解析器 ────────────────────────────────────────────────

def guess_subfield(text):
    """从描述文本猜测竞赛子类别"""
    t = text.lower()
    if "flash" in t:
        return "flash_fiction"
    if "poetry" in t or "poem" in t:
        return "poetry"
    if "novel" in t:
        return "novel"
    if "novella" in t:
        return "novella"
    if "screenplay" in t or "script" in t:
        return "screenplay"
    if "memoir" in t:
        return "memoir"
    if "nonfiction" in t or "non-fiction" in t or "essay" in t:
        return "nonfiction"
    if "short story" in t or "fiction" in t or "short fiction" in t:
        return "short_story"
    if "children" in t or "young adult" in t:
        return "children"
    return "multiple"


def parse_deadline_text(text):
    """解析各种格式的截止日期文本"""
    if not text:
        return None
    text = text.strip()
    # 格式: 2/28/26 或 02/28/26
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', text)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        try:
            return f"{year}-{month:02d}-{day:02d}"
        except ValueError:
            pass
    # 格式: March 31, 2026
    m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})', text, re.I)
    if m:
        months = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
                  "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
        month = months.get(m.group(1).lower(), 1)
        day = int(m.group(2))
        year = int(m.group(3))
        return f"{year}-{month:02d}-{day:02d}"
    # 格式: 2026-03-31
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m:
        return m.group(0)
    return None


def parse_fee(text):
    """从文本中提取费用"""
    if not text:
        return 0, "USD"
    text = text.strip()
    if text == "$0" or "free" in text.lower() or text == "0":
        return 0, "USD"
    m = re.search(r'\$(\d+)', text)
    if m:
        return int(m.group(1)), "USD"
    m = re.search(r'[€£](\d+)', text)
    if m:
        amount = int(m.group(1))
        currency = "EUR" if "€" in text else "GBP"
        return amount, currency
    m = re.search(r'(\d+)', text)
    if m:
        return int(m.group(1)), "USD"
    return 0, "USD"


def parse_prize(text):
    """从文本中提取奖金金额"""
    if not text:
        return 0, ""
    m = re.search(r'\$(\d[\d,]*)', text)
    if m:
        return int(m.group(1).replace(",", "")), text.strip()
    m = re.search(r'[€£](\d[\d,]*)', text)
    if m:
        return int(m.group(1).replace(",", "")), text.strip()
    return 0, text.strip()


# ── pw.org 爬取 ───────────────────────────────────────────

def crawl_pworg():
    """从 Poets & Writers (pw.org) 爬取竞赛列表"""
    print(f"\n{_bold('🔍 爬取 pw.org ...')}")
    results = []

    html = fetch_url("https://www.pw.org/grants")
    if not html:
        return results

    # pw.org HTML 结构:
    # <a href="/writing_contests/xxx" class="title">Name</a>
    # <span class="views-label-field-cash-prize">Cash Prize: </span><span class="field-content">$X</span>
    # <span class="views-label-field-entry-amount-int">Entry Fee: </span><span class="field-content">$X</span>
    # <span class="views-label-field-deadline">Application Deadline: </span><span class="field-content">M/D/YY</span>

    # 按竞赛块分割
    blocks = re.split(r'<a href="/writing_contests/', html)

    for block in blocks[1:]:
        try:
            # 名称
            name_m = re.search(r'class="title">([^<]+)</a>', block)
            if not name_m:
                continue
            name = name_m.group(1).strip()

            # URL
            slug_m = re.match(r'([^"]+)"', block)
            url = f"https://www.pw.org/writing_contests/{slug_m.group(1)}" if slug_m else ""

            # Cash Prize
            prize_m = re.search(r'Cash Prize:.*?field-content">\$?([\d,]+)', block, re.S)
            prize_amount = int(prize_m.group(1).replace(",", "")) if prize_m else 0

            # Entry Fee
            fee_m = re.search(r'Entry Fee:.*?field-content">\$?([\d,]+)', block, re.S)
            fee = int(fee_m.group(1).replace(",", "")) if fee_m else 0

            # Deadline
            dl_m = re.search(r'Deadline:.*?field-content">([^<]+)', block, re.S)
            deadline = parse_deadline_text(dl_m.group(1)) if dl_m else None

            # 描述
            desc_m = re.search(r'<p>([^<]{10,300})', block)
            desc = desc_m.group(1).strip() if desc_m else name

            subfield = guess_subfield(name + " " + desc)

            results.append({
                "name": name,
                "url": url,
                "prize_first": prize_amount,
                "prize_details": f"${prize_amount:,}" if prize_amount else "",
                "fee_amount": fee,
                "fee_currency": "USD",
                "deadline": deadline,
                "subfield": subfield,
                "description": desc[:200],
            })
        except Exception:
            continue

    print(f"  {_green('✓')} 解析到 {len(results)} 个竞赛")
    return results


# ── Reedsy 爬取 ───────────────────────────────────────────

def crawl_reedsy():
    """从 Reedsy 爬取竞赛列表"""
    print(f"\n{_bold('🔍 爬取 Reedsy ...')}")
    results = []

    html = fetch_url("https://reedsy.com/resources/writing-contests/")
    if not html:
        return results

    # Reedsy HTML 结构:
    # <h3><a href="URL">Name</a></h3>
    # <b>Top Prize:</b> ... $X
    # Entry fee: ... $X
    # Deadline: ... Date

    # 按竞赛块分割 — 每个 <h3> 开始一个新竞赛
    blocks = re.split(r'<h3[^>]*>\s*<a', html)

    for block in blocks[1:]:
        try:
            # 名称和URL
            name_m = re.search(r'href="([^"]*)"[^>]*>([^<]+)</a>', block)
            if not name_m:
                continue
            url = name_m.group(1).replace("&amp;", "&")
            name = name_m.group(2).strip()

            # 跳过 Expired
            if "(Expired)" in block or "Expired" in block[:500]:
                continue

            # Top Prize
            prize_m = re.search(r'Top Prize:.*?[\$£€]([\d,]+)', block, re.S)
            prize_amount = int(prize_m.group(1).replace(",", "")) if prize_m else 0

            # Entry fee
            fee_m = re.search(r'Entry fee.*?[\$£€](\d+)', block, re.S)
            if not fee_m:
                # Check for $0 or free
                if re.search(r'Entry fee.*?\$0', block, re.S):
                    fee = 0
                else:
                    fee = 0
            else:
                fee = int(fee_m.group(1))

            # Deadline
            dl_m = re.search(r'Deadline:.*?</[^>]+>\s*([^<]+)', block, re.S)
            deadline_text = dl_m.group(1).strip() if dl_m else ""
            deadline = parse_deadline_text(deadline_text)

            # Genres
            genre_m = re.search(r'Genres:.*?</[^>]+>\s*([^<]+)', block, re.S)
            genres = genre_m.group(1).strip() if genre_m else ""
            subfield = guess_subfield(name + " " + genres)

            results.append({
                "name": name,
                "url": url,
                "prize_first": prize_amount,
                "prize_details": f"${prize_amount:,}" if prize_amount else "",
                "fee_amount": fee,
                "fee_currency": "USD",
                "deadline": deadline,
                "subfield": subfield,
                "description": genres,
            })
        except Exception:
            continue

    print(f"  {_green('✓')} 解析到 {len(results)} 个竞赛")
    return results


# ── NewPages 爬取 ─────────────────────────────────────────

def crawl_newpages():
    """从 NewPages Big List of Writing Contests 爬取"""
    print(f"\n{_bold('🔍 爬取 NewPages ...')}")
    results = []

    html = fetch_url("https://www.newpages.com/guide-submission-opportunities/big-list-of-writing-contests/")
    if not html:
        return results

    # NewPages 结构: 每个竞赛在 <p> 标签内
    # <p><a href="URL">Publisher</a><br />Contest Name<br />Genre<br />Fee info<br />Deadline</p>
    year = date.today().year

    # 提取所有 <p> 块中包含外部链接的条目
    pattern = re.compile(
        r'<p[^>]*>'
        r'\s*(?:<strong>)?'
        r'<a[^>]*href="(https?://(?!www\.newpages)[^"]+)"[^>]*>([^<]+)</a>'
        r'\s*<br\s*/?>\s*'
        r'([^<]+?)<br\s*/?>\s*'   # contest name
        r'([^<]+?)<br\s*/?>\s*'   # genre
        r'([^<]*?)'               # fee info
        r'(?:<br\s*/?>)?\s*'
        r'(?:(?:Opens\s+\d{2}/\d{2}\s*\|\s*)?Closes\s+)?'
        r'(\d{2}/\d{2})',         # deadline MM/DD
        re.S
    )

    for m in pattern.finditer(html):
        try:
            url = m.group(1).strip()
            publisher = m.group(2).strip()
            contest_name = m.group(3).strip()
            genre = m.group(4).strip()
            fee_info = m.group(5).strip()
            deadline_mmdd = m.group(6).strip()

            # 清理 HTML 实体
            contest_name = contest_name.replace("&#8217;", "'").replace("&amp;", "&").replace("&#8211;", "–")
            publisher = publisher.replace("&#8217;", "'").replace("&amp;", "&")

            # 跳过太短的名字
            if len(contest_name) < 3:
                continue

            name = contest_name

            # 解析截止日期 (MM/DD -> YYYY-MM-DD)
            month, day = deadline_mmdd.split("/")
            month, day = int(month), int(day)
            deadline_date = date(year, month, day)
            if deadline_date < date.today():
                deadline_date = date(year + 1, month, day)
            deadline = str(deadline_date)

            # 解析费用
            is_free = "free" in fee_info.lower()
            fee_amount = 0 if is_free else 0  # 金额未知时设为0

            subfield = guess_subfield(contest_name + " " + genre)

            results.append({
                "name": name,
                "url": url,
                "prize_first": 0,
                "prize_details": "",
                "fee_amount": fee_amount,
                "fee_currency": "USD",
                "deadline": deadline,
                "subfield": subfield,
                "description": f"{genre} | {publisher}",
            })
        except Exception:
            continue

    print(f"  {_green('✓')} 解析到 {len(results)} 个竞赛")
    return results


# ── 合并逻辑 ──────────────────────────────────────────────

def merge_results(crawled, data, dry_run=False, max_add=50):
    """将爬取结果合并到数据库，返回新增数量"""
    names = existing_names(data)
    nid = next_id(data)
    added = 0
    today = date.today()
    # 只接受未来6个月内截止的竞赛
    from datetime import timedelta
    cutoff = today + timedelta(days=180)

    for item in crawled:
        if added >= max_add:
            break

        name = item["name"]
        if name.lower().strip() in names:
            continue

        # 跳过已过期
        dl = item.get("deadline")
        if dl:
            try:
                dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
                if dl_date < today:
                    continue
                if dl_date > cutoff:
                    continue  # 太远的也跳过
            except ValueError:
                pass

        # 跳过有国籍限制的（从描述推断）
        desc = item.get("description", "").lower()
        restricted = any(kw in desc for kw in [
            "resident of", "residents of", "citizen of", "citizens of",
            "african american", "african descent", "legal resident",
            "living in the", "who reside in"
        ])
        if restricted:
            print(f"  {_dim('跳过')} {name} {_dim('(可能有地域限制)')}")
            continue

        if dry_run:
            print(f"  {_yellow('+')} {name} | {item.get('deadline', '?')} | ${item.get('fee_amount', 0)} | ${item.get('prize_first', 0)}")
        else:
            comp = make_entry(
                id=nid, name=name, name_cn=auto_translate_name(name),
                subfield=item.get("subfield", "multiple"),
                url=item.get("url", ""),
                deadline=item.get("deadline"),
                fee_amount=item.get("fee_amount", 0),
                fee_currency=item.get("fee_currency", "USD"),
                prize_details=item.get("prize_details", ""),
                prize_first=item.get("prize_first", 0),
                prestige=5, win_prob=5, fit_score=3,
            )
            data["competitions"].append(comp)
            print(f"  {_green('+')} #{nid} {name}")
            nid += 1

        names.add(name.lower().strip())
        added += 1

    return added


# ── 主入口 ────────────────────────────────────────────────

def refresh(dry_run=False, sources=None):
    """执行数据库刷新"""
    print(f"\n{_bold('🔄 竞赛数据库实时刷新')}")
    print(f"{_dim(f'日期: {date.today()}')}")

    data = load_db()
    before = len(data["competitions"])

    all_crawled = []

    available_sources = {
        "pworg": ("pw.org (Poets & Writers)", crawl_pworg),
        "reedsy": ("Reedsy", crawl_reedsy),
        "newpages": ("NewPages", crawl_newpages),
    }

    if sources:
        to_crawl = {k: v for k, v in available_sources.items() if k in sources}
    else:
        to_crawl = available_sources

    for key, (label, func) in to_crawl.items():
        try:
            results = func()
            all_crawled.extend(results)
        except Exception as e:
            print(f"  {_red('✗')} {label} 爬取出错: {e}")

    if not all_crawled:
        print(f"\n{_yellow('没有爬取到新数据。')}")
        return 0

    print(f"\n{_bold('📋 合并结果:')}")
    added = merge_results(all_crawled, data, dry_run=dry_run)

    if not dry_run and added > 0:
        data["updated"] = str(date.today())
        save_db(data)

    after = len(data["competitions"]) if not dry_run else before + added
    print(f"\n{_bold('📊 刷新完成:')}")
    print(f"  爬取到: {len(all_crawled)} 条")
    print(f"  新增: {_green(str(added))} 条 {'(预览模式)' if dry_run else ''}")
    print(f"  数据库: {before} → {after} 条")

    return added


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    refresh(dry_run=dry)
