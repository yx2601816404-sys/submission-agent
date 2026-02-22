#!/usr/bin/env python3
"""
投稿代理 — 匹配引擎准确率测试
10+ 测试用例，验证匹配质量和边界情况
"""

import sys
import os
import json
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matcher import recommend, match_competition, load_db

PASS = 0
FAIL = 0
WARNINGS = []


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}")
        if detail:
            print(f"     → {detail}")
            WARNINGS.append(f"{name}: {detail}")


def test_flash_fiction_beginner():
    """测试1: 零预算闪小说新手 — 应推荐免费+低门槛竞赛"""
    print("\n━━━ 测试1: 零预算闪小说新手 ━━━")
    work = {"type": "flash_fiction", "word_count": 250, "max_fee_usd": 0, "experience": "beginner"}
    results = recommend(work, top_n=10)

    check("返回至少3个结果", len(results) >= 3, f"实际返回 {len(results)}")
    # 所有结果应该是免费的
    all_free = all((r["fee"].get("amount") or 0) == 0 for r in results)
    check("全部免费竞赛", all_free, f"非免费: {[r['name'] for r in results if (r['fee'].get('amount') or 0) > 0]}")
    # 第一名应该是高概率竞赛
    check("Top1 获奖概率 ≥ 6", results[0]["win_prob"] >= 6, f"实际: {results[0]['win_prob']}")
    check("Top1 分数 ≥ 70", results[0]["score"] >= 70, f"实际: {results[0]['score']}")


def test_scifi_intermediate():
    """测试2: 科幻短篇进阶作者 — 应优先匹配科幻类竞赛"""
    print("\n━━━ 测试2: 科幻短篇进阶作者 ━━━")
    work = {"type": "science_fiction", "word_count": 3000, "max_fee_usd": 30, "experience": "intermediate"}
    results = recommend(work, top_n=5)

    check("返回至少3个结果", len(results) >= 3, f"实际返回 {len(results)}")
    # Top3 中应有科幻类竞赛
    top3_names = [r["name"] for r in results[:3]]
    has_scifi = any("parsec" in n.lower() or "wells" in n.lower() or "sci" in n.lower() for n in top3_names)
    check("Top3 含科幻类竞赛", has_scifi, f"Top3: {top3_names}")
    check("Top1 分数 ≥ 75", results[0]["score"] >= 75, f"实际: {results[0]['score']}")


def test_poetry_low_budget():
    """测试3: 诗歌作者低预算 — 应匹配诗歌类竞赛"""
    print("\n━━━ 测试3: 诗歌作者低预算 ━━━")
    work = {"type": "poetry", "word_count": 0, "max_fee_usd": 15, "experience": "beginner"}
    results = recommend(work, top_n=8)

    check("返回至少3个结果", len(results) >= 3, f"实际返回 {len(results)}")
    # 应有诗歌专门竞赛
    has_poetry = any("poet" in r["name"].lower() or "verse" in r["name"].lower() or "诗" in (r.get("name_cn") or "") for r in results[:5])
    check("Top5 含诗歌类竞赛", has_poetry, f"Top5: {[r['name'] for r in results[:5]]}")


def test_novel_high_budget():
    """测试4: 长篇小说高预算 — 应匹配高声望竞赛"""
    print("\n━━━ 测试4: 长篇小说高预算 ━━━")
    work = {"type": "novel", "word_count": 80000, "max_fee_usd": 100, "experience": "advanced"}
    results = recommend(work, top_n=5)

    check("返回至少2个结果", len(results) >= 2, f"实际返回 {len(results)}")
    if results:
        # 高预算应能匹配到高声望竞赛
        max_prestige = max(r["prestige"] for r in results[:3])
        check("Top3 最高声望 ≥ 6", max_prestige >= 6, f"最高声望: {max_prestige}")


def test_essay_academic():
    """测试5: 学术散文 — 应匹配 essay/academic 类"""
    print("\n━━━ 测试5: 学术散文 ━━━")
    work = {"type": "essay", "word_count": 5000, "max_fee_usd": 30, "experience": "intermediate"}
    results = recommend(work, top_n=5)

    check("返回至少2个结果", len(results) >= 2, f"实际返回 {len(results)}")


def test_word_count_overflow():
    """测试6: 字数严重超标 — 闪小说专项竞赛应排在后面或有警告"""
    print("\n━━━ 测试6: 字数严重超标 (闪小说10000字) ━━━")
    work = {"type": "flash_fiction", "word_count": 10000, "max_fee_usd": 50, "experience": "beginner"}
    results = recommend(work, top_n=20)

    # 检查：有字数限制的闪小说竞赛应该有字数警告或低分
    comps = load_db()
    flash_with_limit = [c for c in comps if c.get("subfield") == "flash_fiction"
                        and c.get("word_limit", {}) and c.get("word_limit", {}).get("max")]
    if flash_with_limit:
        # 至少有一些闪小说竞赛在结果中带字数警告
        all_results_warnings = [w for r in results for w in r.get("warnings", [])]
        has_word_warning = any("字数" in w for w in all_results_warnings)
        check("结果中有字数相关警告", has_word_warning,
              f"所有警告: {all_results_warnings[:5]}")
    check("返回结果", len(results) > 0, f"实际: {len(results)}")


def test_zero_budget_filter():
    """测试7: 零预算严格过滤 — 只返回免费竞赛"""
    print("\n━━━ 测试7: 零预算严格过滤 ━━━")
    work = {"type": "short_story", "word_count": 2000, "max_fee_usd": 0, "experience": "beginner"}
    results = recommend(work, top_n=20)

    all_free = all((r["fee"].get("amount") or 0) == 0 for r in results)
    check("全部免费", all_free, f"非免费: {[(r['name'], r['fee']) for r in results if (r['fee'].get('amount') or 0) > 0]}")
    check("返回至少3个免费竞赛", len(results) >= 3, f"实际: {len(results)}")


def test_deadline_filter():
    """测试8: 已过期竞赛不应出现"""
    print("\n━━━ 测试8: 已过期竞赛过滤 ━━━")
    comps = load_db()
    today = date.today()
    expired_count = 0
    for comp in comps:
        d = comp.get("deadline")
        if d and d not in ("weekly", "quarterly", "rolling"):
            try:
                from datetime import datetime
                dl = datetime.strptime(d, "%Y-%m-%d").date()
                if dl < today:
                    expired_count += 1
            except:
                pass

    work = {"type": "short_story", "word_count": 2000, "max_fee_usd": 100}
    results = recommend(work, top_n=50)

    # 检查结果中没有已过期的
    for r in results:
        d = r.get("deadline")
        if d and d not in ("weekly", "quarterly", "rolling"):
            try:
                from datetime import datetime
                dl = datetime.strptime(d, "%Y-%m-%d").date()
                if dl < today:
                    check(f"过期竞赛不应出现: {r['name']}", False, f"截止: {d}")
                    return
            except:
                pass
    check(f"无过期竞赛出现 (数据库中有{expired_count}个已过期)", True)


def test_score_range():
    """测试9: 分数范围合理性 — 所有分数应在 0-100"""
    print("\n━━━ 测试9: 分数范围合理性 ━━━")
    test_works = [
        {"type": "flash_fiction", "word_count": 100, "max_fee_usd": 50},
        {"type": "novel", "word_count": 100000, "max_fee_usd": 100},
        {"type": "poetry", "word_count": 0, "max_fee_usd": 0},
        {"type": "screenplay", "word_count": 15000, "max_fee_usd": 80},
    ]
    all_valid = True
    for w in test_works:
        results = recommend(w, top_n=30)
        for r in results:
            if r["score"] < 0 or r["score"] > 100:
                all_valid = False
                check(f"分数越界: {r['name']} = {r['score']}", False)
    check("所有分数在 0-100 范围内", all_valid)


def test_reasons_not_empty():
    """测试10: 每个推荐都有理由 — 可解释性"""
    print("\n━━━ 测试10: 推荐理由可解释性 ━━━")
    work = {"type": "short_story", "word_count": 3000, "max_fee_usd": 30, "experience": "beginner"}
    results = recommend(work, top_n=10)

    all_have_reasons = all(len(r.get("reasons", [])) > 0 for r in results)
    check("每个推荐都有理由", all_have_reasons,
          f"无理由: {[r['name'] for r in results if not r.get('reasons')]}")
    # 理由数量
    avg_reasons = sum(len(r.get("reasons", [])) for r in results) / max(len(results), 1)
    check(f"平均理由数 ≥ 2 (实际: {avg_reasons:.1f})", avg_reasons >= 2)


def test_memoir_niche():
    """测试11: 小众类型 — 回忆录"""
    print("\n━━━ 测试11: 小众类型 (回忆录) ━━━")
    work = {"type": "memoir", "word_count": 5000, "max_fee_usd": 30, "experience": "intermediate"}
    results = recommend(work, top_n=5)

    check("返回至少1个结果", len(results) >= 1, f"实际: {len(results)}")
    if results:
        check("Top1 分数 ≥ 40", results[0]["score"] >= 40, f"实际: {results[0]['score']}")


def test_children_lit():
    """测试12: 儿童文学"""
    print("\n━━━ 测试12: 儿童文学 ━━━")
    work = {"type": "children", "word_count": 1000, "max_fee_usd": 20, "experience": "beginner"}
    results = recommend(work, top_n=5)

    check("返回至少1个结果", len(results) >= 1, f"实际: {len(results)}")


def test_consistency():
    """测试13: 一致性 — 相同输入应返回相同结果"""
    print("\n━━━ 测试13: 结果一致性 ━━━")
    work = {"type": "flash_fiction", "word_count": 300, "max_fee_usd": 20}
    r1 = recommend(work, top_n=5)
    r2 = recommend(work, top_n=5)

    same_order = [a["id"] for a in r1] == [b["id"] for b in r2]
    check("相同输入 → 相同结果", same_order)
    same_scores = [a["score"] for a in r1] == [b["score"] for b in r2]
    check("相同输入 → 相同分数", same_scores)


def test_performance():
    """测试14: 性能 — 匹配应在 1 秒内完成"""
    print("\n━━━ 测试14: 性能测试 ━━━")
    import time
    work = {"type": "short_story", "word_count": 3000, "max_fee_usd": 50}

    start = time.time()
    for _ in range(100):
        recommend(work, top_n=10)
    elapsed = time.time() - start

    avg_ms = (elapsed / 100) * 1000
    check(f"100次匹配平均耗时 < 50ms (实际: {avg_ms:.1f}ms)", avg_ms < 50)
    check(f"单次匹配 < 5秒 (契约要求)", avg_ms < 5000)


# ── 运行所有测试 ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("📊 投稿代理 — 匹配引擎准确率测试报告")
    print(f"日期: {date.today()}")
    print("=" * 60)

    test_flash_fiction_beginner()
    test_scifi_intermediate()
    test_poetry_low_budget()
    test_novel_high_budget()
    test_essay_academic()
    test_word_count_overflow()
    test_zero_budget_filter()
    test_deadline_filter()
    test_score_range()
    test_reasons_not_empty()
    test_memoir_niche()
    test_children_lit()
    test_consistency()
    test_performance()

    # ── 汇总 ──
    total = PASS + FAIL
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {PASS}/{total} 通过 ({PASS/total*100:.0f}%)")
    if FAIL:
        print(f"❌ 失败: {FAIL}")
        for w in WARNINGS:
            print(f"   → {w}")
    else:
        print("✅ 全部通过!")
    print("=" * 60)

    sys.exit(0 if FAIL == 0 else 1)
