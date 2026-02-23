#!/usr/bin/env python3
"""
投稿代理 — 智能匹配引擎 v1.0
输入：作品信息（类型、字数、风格、预算、经验等级）
输出：排序后的竞赛推荐列表 + 匹配分数 + 推荐理由
"""

import json
import sys
from datetime import datetime, date
from typing import Optional

DB_PATH = "/home/lyall/.openclaw/workspace/agents-workspace/submission-agent/competitions.json"

def load_db():
    with open(DB_PATH, 'r') as f:
        return json.load(f)["competitions"]

def parse_deadline(d):
    """解析截止日期，处理特殊值"""
    if not d or d in ("weekly", "quarterly", "rolling"):
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except:
        return None

def match_competition(comp, work):
    """
    计算单个竞赛与作品的匹配分数（0-100）
    返回 (score, reasons, warnings)
    """
    score = 0
    reasons = []
    warnings = []
    
    # === 硬性过滤（不通过直接返回0） ===
    
    # 1. 状态过滤
    status = comp.get("status", "")
    if status in ("closed", "expired"):
        return 0, [], ["竞赛已关闭"]
    
    # 2. 国籍限制
    nat = comp.get("nationality_restriction")
    if nat and "中国" not in str(nat) and "无" not in str(nat):
        return 0, [], [f"国籍限制: {nat}"]
    
    # 3. 中国创作者适配度为1的直接排除
    fit = comp.get("chinese_creator_fit", {})
    if fit.get("score", 3) <= 1:
        return 0, [], ["不适合中国创作者"]
    
    # 4. 截止日期检查
    deadline = parse_deadline(comp.get("deadline"))
    today = date.today()
    if deadline and deadline < today:
        return 0, [], ["已过截止日期"]
    
    # === 软性评分 ===
    
    # 维度1: 类型匹配 (0-18分)
    work_type = work.get("type", "")
    comp_subfield = comp.get("subfield", "")
    type_map = {
        "flash_fiction": ["flash_fiction", "multiple"],
        "short_story": ["short_story", "multiple"],
        "poetry": ["poetry", "multiple", "poetry_collection"],
        "novel": ["novel", "multiple"],
        "essay": ["essay_academic", "nonfiction", "multiple"],
        "memoir": ["memoir", "nonfiction", "multiple"],
        "science_fiction": ["science_fiction_fantasy", "short_story", "multiple"],
        "screenplay": ["screenplay", "multiple"],
    }
    matching_types = type_map.get(work_type, [work_type])
    if comp_subfield in matching_types:
        score += 18
        reasons.append(f"类型匹配: {comp_subfield}")
    elif comp_subfield == "multiple":
        score += 13
        reasons.append("多类别竞赛，可投")
    else:
        score += 0
        warnings.append(f"类型不匹配: 作品={work_type}, 竞赛={comp_subfield}")
    
    # 维度2: 字数匹配 (0-13分)
    work_words = work.get("word_count", 0)
    wl = comp.get("word_limit", {})
    if wl and work_words > 0:
        wl_max = wl.get("max")
        wl_min = wl.get("min")
        unit = wl.get("unit", "words")
        
        if unit == "words" and wl_max:
            if work_words <= wl_max:
                ratio = work_words / wl_max if wl_max > 0 else 0
                if ratio >= 0.5:
                    score += 13
                    reasons.append(f"字数合适: {work_words}/{wl_max}字")
                else:
                    score += 8
                    reasons.append(f"字数偏短: {work_words}/{wl_max}字")
            else:
                over = work_words - wl_max
                if over <= 500:
                    score += 4
                    warnings.append(f"字数略超: {work_words}/{wl_max}字，需删减{over}字")
                else:
                    score += 0
                    warnings.append(f"字数严重超出: {work_words}/{wl_max}字")
        elif unit == "lines":
            score += 8
    else:
        score += 7
    
    # 维度3: 预算匹配 (0-10分)
    budget = work.get("max_fee_usd", 50)  # 默认$50预算
    fee = comp.get("entry_fee", {})
    fee_amount = fee.get("amount", 0) or 0
    fee_currency = fee.get("currency", "USD")
    
    # 粗略汇率转换
    fx = {"USD": 1, "EUR": 1.1, "GBP": 1.27, "CAD": 0.74, "CHF": 1.13, "AUD": 0.65}
    fee_usd = fee_amount * fx.get(fee_currency, 1)
    
    # 零预算硬性过滤：只看免费竞赛
    if budget == 0 and fee_usd > 0:
        return 0, [], ["超出预算（仅看免费竞赛）"]
    
    if fee_usd == 0:
        score += 10
        reasons.append("免费投稿 🎉")
    elif fee_usd <= budget:
        score += 8
        reasons.append(f"费用在预算内: ~${fee_usd:.0f}")
    elif fee_usd <= budget * 1.5:
        score += 4
        warnings.append(f"费用略超预算: ~${fee_usd:.0f}")
    else:
        score += 0
        warnings.append(f"费用超出预算: ~${fee_usd:.0f}")
    
    # 维度4: 获奖概率 (0-18分)
    wp = comp.get("win_probability", {})
    wp_score = wp.get("overall_score", 5)
    score += int(wp_score * 1.8)  # 0-18分
    if wp_score >= 6:
        reasons.append(f"获奖概率较高 ({wp_score}/10)")
    elif wp_score <= 3:
        warnings.append(f"获奖概率较低 ({wp_score}/10)")
    
    # 维度5: 声望 (0-8分)
    prestige = comp.get("prestige_score", 5)
    score += min(8, int(prestige * 0.8))  # 0-8分
    if prestige >= 8:
        reasons.append(f"高声望竞赛 ({prestige}/10)")
    
    # 维度6: 中国创作者适配度 (0-13分)
    fit_score = fit.get("score", 3)
    score += min(13, int(fit_score * 2.6))  # 0-13分
    if fit.get("advantages"):
        reasons.extend(fit["advantages"][:2])  # 最多取2个优势
    if fit.get("recommendation"):
        reasons.append(fit["recommendation"])
    
    # 维度7: 时间充裕度 (0-10分)
    if deadline:
        days_left = (deadline - today).days
        if days_left >= 60:
            score += 10
            reasons.append(f"时间充裕: 还有{days_left}天")
        elif days_left >= 30:
            score += 7
            reasons.append(f"时间适中: 还有{days_left}天")
        elif days_left >= 14:
            score += 4
            warnings.append(f"时间紧张: 仅剩{days_left}天")
        elif days_left >= 3:
            score += 1
            warnings.append(f"即将截止: 仅剩{days_left}天!")
    elif comp.get("deadline") in ("weekly", "quarterly"):
        score += 8
        reasons.append("滚动截止，随时可投")
    else:
        score += 5
    
    # 维度8: 风格匹配 (0-10分)
    work_styles = set(work.get("style_tags", []))
    comp_styles = set(comp.get("style_profile", {}).get("style_tags", []))
    
    if work_styles and comp_styles:
        # 直接交集
        overlap = work_styles & comp_styles
        # 相关风格映射（扩展匹配）
        style_affinity = {
            "literary": {"contemporary", "experimental", "emotional_tension", "narrative"},
            "experimental": {"literary", "innovative", "avant_garde"},
            "contemporary": {"literary", "urban", "modern"},
            "science_fiction": {"fantasy", "imaginative", "speculative"},
            "fantasy": {"science_fiction", "imaginative", "speculative", "mythological"},
            "nature": {"contemplative", "pastoral", "environmental"},
            "contemplative": {"nature", "philosophical", "meditative"},
            "personal": {"narrative", "memoir", "confessional"},
            "narrative": {"personal", "storytelling", "literary"},
            "political": {"social_justice", "activist", "protest"},
            "humorous": {"satirical", "witty", "comedic"},
            "dark": {"gothic", "noir", "horror"},
            "traditional": {"formal", "classical", "traditional_narrative"},
            "open": set(),  # "open" matches everything loosely
        }
        
        # Check affinity matches
        affinity_matches = set()
        for ws in work_styles:
            related = style_affinity.get(ws, set())
            affinity_matches |= (related & comp_styles)
        
        # "open" style in competition = accepts all styles
        comp_is_open = "open" in comp_styles
        
        if overlap:
            match_count = len(overlap)
            pts = min(10, 6 + match_count * 2)
            score += pts
            style_cn = {
                "literary": "文学性", "experimental": "实验性", "contemporary": "当代",
                "science_fiction": "科幻", "fantasy": "奇幻", "nature": "自然",
                "contemplative": "沉思", "personal": "个人", "narrative": "叙事",
                "open": "开放", "innovative": "创新", "humorous": "幽默",
                "dark": "暗黑", "traditional": "传统", "political": "政治",
            }
            matched_names = [style_cn.get(s, s) for s in list(overlap)[:2]]
            reasons.append(f"风格匹配: {'/'.join(matched_names)}")
        elif affinity_matches:
            score += 5
            reasons.append("风格相近")
        elif comp_is_open:
            score += 4
            reasons.append("竞赛风格开放")
        else:
            score += 1
            warnings.append("风格不太匹配")
    elif comp_styles and "open" in comp_styles:
        score += 4  # 竞赛开放，作品没标风格
    else:
        score += 5  # 无风格信息，给中间分
    
    return min(score, 100), reasons, warnings


def recommend(work, top_n=10):
    """为作品推荐最佳竞赛"""
    comps = load_db()
    results = []
    
    for comp in comps:
        score, reasons, warnings = match_competition(comp, work)
        if score > 0:
            results.append({
                "id": comp.get("id"),
                "name": comp.get("name"),
                "name_cn": comp.get("name_cn"),
                "score": score,
                "deadline": comp.get("deadline"),
                "prize": comp.get("prize", {}).get("details", ""),
                "fee": comp.get("entry_fee", {}),
                "prestige": comp.get("prestige_score"),
                "url": comp.get("url"),
                "reasons": reasons,
                "warnings": warnings,
                "win_prob": comp.get("win_probability", {}).get("overall_score", 0),
            })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def format_results(results, work):
    """格式化输出推荐结果"""
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"📝 投稿匹配报告")
    lines.append(f"{'='*60}")
    lines.append(f"作品类型: {work.get('type', 'N/A')}")
    lines.append(f"字数: {work.get('word_count', 'N/A')}")
    lines.append(f"风格: {', '.join(work.get('style_tags', []))}")
    lines.append(f"预算: ${work.get('max_fee_usd', 50)}")
    lines.append(f"{'='*60}\n")
    
    for i, r in enumerate(results, 1):
        lines.append(f"{'─'*50}")
        lines.append(f"#{i} {r['name_cn'] or r['name']}  [匹配度: {r['score']}分]")
        lines.append(f"   📅 截止: {r['deadline'] or '见官网'}")
        lines.append(f"   🏆 奖金: {r['prize']}")
        fee = r.get('fee', {})
        fee_str = f"{fee.get('currency', '')} {fee.get('amount', 0)}" if fee.get('amount') else "免费"
        lines.append(f"   💰 费用: {fee_str}")
        lines.append(f"   ⭐ 声望: {r['prestige']}/10 | 获奖概率: {r['win_prob']}/10")
        lines.append(f"   🔗 {r['url']}")
        
        if r['reasons']:
            lines.append(f"   ✅ {' | '.join(r['reasons'][:4])}")
        if r['warnings']:
            lines.append(f"   ⚠️ {' | '.join(r['warnings'][:3])}")
        lines.append("")
    
    return "\n".join(lines)


# === 测试用例 ===
if __name__ == "__main__":
    # 测试场景1: 中国闪小说作者，300字，预算$20
    work1 = {
        "type": "flash_fiction",
        "word_count": 280,
        "style_tags": ["literary", "contemporary"],
        "max_fee_usd": 20,
        "experience": "beginner",
    }
    
    print("\n🔍 测试场景1: 闪小说作者 (280字, 预算$20)")
    results1 = recommend(work1, top_n=8)
    print(format_results(results1, work1))
    
    # 测试场景2: 中国科幻短篇作者，3000字，预算$30
    work2 = {
        "type": "science_fiction",
        "word_count": 3000,
        "style_tags": ["science_fiction", "imaginative"],
        "max_fee_usd": 30,
        "experience": "intermediate",
    }
    
    print("\n🔍 测试场景2: 科幻短篇作者 (3000字, 预算$30)")
    results2 = recommend(work2, top_n=8)
    print(format_results(results2, work2))
    
    # 测试场景3: 中国诗人，预算$15
    work3 = {
        "type": "poetry",
        "word_count": 0,
        "style_tags": ["nature", "contemplative"],
        "max_fee_usd": 15,
        "experience": "beginner",
    }
    
    print("\n🔍 测试场景3: 诗人 (预算$15)")
    results3 = recommend(work3, top_n=8)
    print(format_results(results3, work3))
