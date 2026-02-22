#!/usr/bin/env python3
"""
竞赛名称中文翻译模块
基于关键词规则自动生成中文名，无需外部 API
"""

import re

# 常见竞赛术语翻译
TERM_MAP = {
    # 竞赛类型
    "prize": "奖",
    "award": "奖",
    "awards": "奖",
    "contest": "竞赛",
    "competition": "竞赛",
    "fellowship": "奖学金",
    "fellowships": "奖学金",
    "grant": "资助",
    "grants": "资助",
    "residency": "驻留",
    "scholarship": "奖学金",
    # 文学类型
    "poetry": "诗歌",
    "poem": "诗歌",
    "fiction": "小说",
    "short fiction": "短篇小说",
    "flash fiction": "闪小说",
    "short story": "短篇小说",
    "novel": "长篇小说",
    "novella": "中篇小说",
    "nonfiction": "非虚构",
    "non-fiction": "非虚构",
    "creative nonfiction": "创意非虚构",
    "essay": "散文",
    "memoir": "回忆录",
    "screenplay": "剧本",
    "script": "剧本",
    "chapbook": "小册子",
    "book": "图书",
    "literary": "文学",
    "writing": "写作",
    # 修饰词
    "first": "首部",
    "new": "新",
    "emerging": "新锐",
    "international": "国际",
    "annual": "年度",
    "humor": "幽默",
    "humour": "幽默",
    "flash": "闪",
    "short": "短篇",
    "open": "公开",
    "free": "免费",
    "winter": "冬季",
    "spring": "春季",
    "summer": "夏季",
    "fall": "秋季",
    "autumn": "秋季",
}

# 知名竞赛/机构的专有翻译
PROPER_NAMES = {
    "reedsy": "Reedsy",
    "submittable": "Submittable",
    "pushcart": "Pushcart",
    "pulitzer": "普利策",
    "booker": "布克",
    "hugo": "雨果",
    "nebula": "星云",
    "o. henry": "欧·亨利",
}


def auto_translate_name(english_name):
    """
    自动生成竞赛中文名
    策略：保留专有名词 + 翻译通用术语
    例: "Bellingham Review Literary Awards" → "Bellingham Review 文学奖"
    """
    if not english_name:
        return ""

    name = english_name.strip()

    # 清理 HTML 实体
    name = name.replace("&amp;", "&").replace("&#8217;", "'").replace("&#8211;", "–")

    # 先检查是否有专有翻译
    name_lower = name.lower()
    for eng, cn in PROPER_NAMES.items():
        if eng in name_lower:
            name = re.sub(re.escape(eng), cn, name, flags=re.I)

    # 分词处理
    words = name.split()
    result_parts = []
    i = 0
    translated_something = False

    while i < len(words):
        word = words[i]
        word_lower = word.lower().rstrip(".,;:'\"")

        # 尝试匹配多词短语（如 "flash fiction", "short story"）
        matched_phrase = False
        for phrase_len in (3, 2):
            if i + phrase_len <= len(words):
                phrase = " ".join(w.lower().rstrip(".,;:'\"") for w in words[i:i+phrase_len])
                if phrase in TERM_MAP:
                    result_parts.append(TERM_MAP[phrase])
                    i += phrase_len
                    matched_phrase = True
                    translated_something = True
                    break
        if matched_phrase:
            continue

        # 单词匹配
        if word_lower in TERM_MAP:
            result_parts.append(TERM_MAP[word_lower])
            translated_something = True
        elif word_lower in ("the", "a", "an", "of", "for", "in", "and", "&", "by", "to", "with"):
            # 跳过冠词/介词（中文不需要）
            pass
        elif re.match(r'^\d{4}$', word):
            # 年份保留
            result_parts.append(word)
        else:
            # 保留专有名词原文
            result_parts.append(word)
        i += 1

    if not translated_something:
        # 如果什么都没翻译，返回空（保持原文显示）
        return ""

    return " ".join(result_parts)


def batch_translate(competitions):
    """批量为没有中文名的竞赛生成中文名"""
    count = 0
    for comp in competitions:
        if not comp.get("name_cn"):
            cn = auto_translate_name(comp["name"])
            if cn and cn != comp["name"]:
                comp["name_cn"] = cn
                count += 1
    return count


if __name__ == "__main__":
    # 测试
    test_names = [
        "Bellingham Review Literary Awards",
        "James Jones First Novel Fellowship",
        "Ploughshares Emerging Writers' Contest",
        "WOW! Winter 2026 Flash Fiction Contest",
        "The Moth Short Story Prize",
        "Kenyon Review Short Fiction Contest",
        "Robinson Jeffers Tor House Poetry Prize",
        "Fairy Tale Review Prize",
        "Quarterly West Novella Prize",
        "Caine Prize for African Writing",
        "Ruth Lilly and Dorothy Sargent Rosenberg Poetry Fellowships",
        "Fiction & Poetry Contest",
        "CBC Nonfiction Prize",
        "Montana Prizes for Fiction and Creative Nonfiction",
        "Hurt & Healing Prize",
    ]

    for name in test_names:
        cn = auto_translate_name(name)
        print(f"  {name}")
        print(f"  → {cn}")
        print()
