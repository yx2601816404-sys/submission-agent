#!/usr/bin/env python3
"""
作品档案管理模块
保存/加载/列出用户的作品信息，避免重复输入
"""

import json
import os
import sys
from datetime import datetime

PROFILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles.json")


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


def load_profiles():
    if not os.path.exists(PROFILES_PATH):
        return {"profiles": []}
    with open(PROFILES_PATH, "r") as f:
        return json.load(f)


def save_profiles(data):
    with open(PROFILES_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_profiles():
    """列出所有已保存的作品档案"""
    data = load_profiles()
    profiles = data.get("profiles", [])
    if not profiles:
        print(f"\n{_yellow('还没有保存任何作品档案。')}")
        print(f"{_dim('使用 --save-profile 保存一个作品档案。')}")
        return []

    print(f"\n{_bold('📚 已保存的作品档案')}")
    print(f"{_dim('─' * 50)}")
    for i, p in enumerate(profiles, 1):
        title = p.get("title", "未命名")
        ptype = p.get("type", "?")
        words = p.get("word_count", 0)
        budget = p.get("max_fee_usd", 50)
        created = p.get("created", "")
        styles = ", ".join(p.get("style_tags", []))

        print(f"  {_cyan(str(i))}. {_bold(title)}")
        print(f"     类型: {ptype} | 字数: {words} | 预算: ${budget}")
        if styles:
            print(f"     风格: {styles}")
        if p.get("theme"):
            print(f"     主题: {p['theme']}")
        if p.get("language"):
            print(f"     语言: {p['language']}")
        print(f"     {_dim(f'创建: {created}')}")
        print()

    return profiles


def get_profile(index):
    """获取指定索引的作品档案（1-based）"""
    data = load_profiles()
    profiles = data.get("profiles", [])
    if not profiles:
        return None
    if index < 1 or index > len(profiles):
        return None
    return profiles[index - 1]


def get_profile_by_title(title):
    """按标题查找作品档案"""
    data = load_profiles()
    for p in data.get("profiles", []):
        if p.get("title", "").lower() == title.lower():
            return p
    return None


def save_profile(work, title=None):
    """保存作品档案"""
    data = load_profiles()

    profile = {
        "title": title or f"作品_{len(data['profiles']) + 1}",
        "type": work.get("type", ""),
        "word_count": work.get("word_count", 0),
        "style_tags": work.get("style_tags", []),
        "max_fee_usd": work.get("max_fee_usd", 50),
        "experience": work.get("experience", "beginner"),
        "theme": work.get("theme", ""),
        "language": work.get("language", "zh"),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # 检查是否已存在同名档案
    for i, p in enumerate(data["profiles"]):
        if p.get("title", "").lower() == profile["title"].lower():
            data["profiles"][i] = profile
            save_profiles(data)
            print(f"\n{_green('✓')} 已更新作品档案: {_bold(profile['title'])}")
            return profile

    data["profiles"].append(profile)
    save_profiles(data)
    print(f"\n{_green('✓')} 已保存作品档案: {_bold(profile['title'])}")
    return profile


def delete_profile(index):
    """删除指定索引的作品档案（1-based）"""
    data = load_profiles()
    profiles = data.get("profiles", [])
    if index < 1 or index > len(profiles):
        print(f"{_red('无效的档案编号。')}")
        return False
    removed = profiles.pop(index - 1)
    save_profiles(data)
    print(f"{_green('✓')} 已删除: {removed.get('title', '未命名')}")
    return True


def profile_to_work(profile):
    """将档案转换为匹配引擎需要的 work 字典"""
    return {
        "type": profile.get("type", ""),
        "word_count": profile.get("word_count", 0),
        "style_tags": profile.get("style_tags", []),
        "max_fee_usd": profile.get("max_fee_usd", 50),
        "experience": profile.get("experience", "beginner"),
    }


def interactive_save(work):
    """交互式保存作品档案"""
    try:
        save_it = input(f"\n{_dim('保存为作品档案？[y/N] ')}").strip().lower()
        if save_it not in ("y", "yes", "是"):
            return None
        title = input(f"{_dim('档案名称: ')}").strip()
        if not title:
            title = None

        # 额外信息
        theme = input(f"{_dim('作品主题 (可选): ')}").strip()
        lang = input(f"{_dim('原文语言 [zh/en, 默认zh]: ')}").strip() or "zh"

        work["theme"] = theme
        work["language"] = lang
        return save_profile(work, title)
    except (KeyboardInterrupt, EOFError):
        return None


def interactive_load():
    """交互式加载作品档案"""
    profiles = list_profiles()
    if not profiles:
        return None

    try:
        choice = input(f"选择档案编号 (或回车跳过): ").strip()
        if not choice:
            return None
        idx = int(choice)
        p = get_profile(idx)
        if p:
            print(f"\n{_green('✓')} 已加载: {_bold(p.get('title', '未命名'))}")
            return profile_to_work(p)
        else:
            print(f"{_red('无效编号。')}")
            return None
    except (ValueError, KeyboardInterrupt, EOFError):
        return None
