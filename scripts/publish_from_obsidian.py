#!/usr/bin/env python3
"""
從 Obsidian 保存庫發布長文（blog）或短文（notes）到部落格。

用法：
    python scripts/publish_from_obsidian.py <Obsidian 筆記檔名>

會依照筆記放在 Obsidian 裡的 blog/ 或 note/ 資料夾，自動判斷要發布成長文還是短文
（放在別的地方才會另外問你）。只會「複製」筆記內容到部落格專案裡，不會更動或刪除
Obsidian 裡的原始檔案。複製完之後，還需要自己 git add / commit / push 才會真正上線。
"""

import os
import re
import sys
from datetime import date, datetime

VAULT_DIR = "/Users/lizchen/Library/Mobile Documents/iCloud~md~obsidian/Documents/lizchen/BagelNotes"
VAULT_BLOG_DIR = os.path.join(VAULT_DIR, "blog")
VAULT_NOTE_DIR = os.path.join(VAULT_DIR, "note")

BLOG_DIR = "/Users/lizchen/Projects/bagelnote-astro/src/content/blog"
NOTES_DIR = "/Users/lizchen/Projects/bagelnote-astro/src/content/notes"


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "post"


def strip_frontmatter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def kind_for_path(path):
    """依照筆記所在資料夾自動判斷 blog / note，找不到就回傳 None。"""
    parent = os.path.dirname(path)
    if parent == VAULT_BLOG_DIR:
        return "blog"
    if parent == VAULT_NOTE_DIR:
        return "note"
    return None


def find_file(filename):
    if not filename.endswith(".md"):
        filename += ".md"

    if os.path.isabs(filename) and os.path.exists(filename):
        return filename

    # 優先找 blog/ 和 note/ 這兩個發布用資料夾
    for folder in (VAULT_BLOG_DIR, VAULT_NOTE_DIR):
        candidate = os.path.join(folder, filename)
        if os.path.exists(candidate):
            return candidate

    # 找不到的話，在整個保存庫裡搜尋檔名
    target = filename.lower()
    for root, _, files in os.walk(VAULT_DIR):
        for f in files:
            if f.lower() == target:
                return os.path.join(root, f)
    return None


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/publish_from_obsidian.py <Obsidian 筆記檔名>")
        sys.exit(1)

    path = find_file(sys.argv[1])
    if not path:
        print(f"在 {VAULT_DIR} 裡找不到檔案：{sys.argv[1]}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        body = strip_frontmatter(f.read())

    print(f"讀到筆記：{path}")
    print("---")
    preview = body if len(body) <= 300 else body[:300] + "..."
    print(preview)
    print("---")

    kind = kind_for_path(path)
    if kind:
        print(f"偵測到這篇放在 Obsidian 的「{kind}」資料夾，會發布成{'長文' if kind == 'blog' else '短文'}。")
    else:
        kind = input("這篇不在 blog/ 或 note/ 資料夾裡，請輸入要發布成 blog 還是 note：").strip().lower()
        while kind not in ("blog", "note"):
            kind = input("請輸入 blog 或 note：").strip().lower()

    today = date.today().isoformat()

    if kind == "note":
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        out_path = os.path.join(NOTES_DIR, f"{timestamp}.md")
        frontmatter = f"---\npubDate: {today}\n---\n\n{body}\n"
    else:
        default_title = os.path.splitext(os.path.basename(path))[0]
        title = input(f"文章標題（直接按 Enter 使用「{default_title}」）：").strip() or default_title
        description = ""
        while not description:
            description = input("一句話描述這篇文章（會顯示在列表和搜尋結果）：").strip()
        slug = slugify(title)
        out_path = os.path.join(BLOG_DIR, f"{slug}.md")
        frontmatter = (
            f'---\ntitle: "{title}"\ndescription: "{description}"\n'
            f"pubDate: {today}\n---\n\n{body}\n"
        )

    if os.path.exists(out_path):
        confirm = input(f"{out_path} 已經存在，要覆蓋嗎？(y/N)：").strip().lower()
        if confirm != "y":
            print("已取消，沒有寫入任何檔案。")
            return

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)

    print(f"已寫入：{out_path}")
    print("接下來執行 git add、git commit、git push，網站才會真的更新。")


if __name__ == "__main__":
    main()
