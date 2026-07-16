#!/usr/bin/env python3
"""
從 Obsidian 保存庫發布長文（blog）或短文（notes）到部落格，或是刪除已發布的文章。

用法：
    python scripts/publish_from_obsidian.py <Obsidian 筆記檔名>            # 發布/更新
    python scripts/publish_from_obsidian.py <Obsidian 筆記檔名> --delete   # 刪除

會依照筆記放在 Obsidian 裡的 blog/ 或 note/ 資料夾，自動判斷要發布成長文還是短文。
輸出檔名是根據 Obsidian 筆記檔名（而不是標題）產生，所以編輯筆記後重新執行這支腳本，
會直接更新同一篇文章，而不是多產生一篇。

完全自動：複製/刪除完成後會自動執行 git add、commit、push，不會再詢問確認。
腳本不會更動或刪除 Obsidian 裡的原始檔案。

長文（blog）需要在筆記最上面的 frontmatter 填 title / description，例如：

    ---
    title: 文章標題
    description: 一句話描述
    ---

    文章內容...

沒有填 description 的話，為了不推出不完整的文章上線，腳本會中止並印出錯誤訊息。
"""

import os
import re
import subprocess
import sys
from datetime import date

VAULT_DIR = "/Users/lizchen/Library/Mobile Documents/iCloud~md~obsidian/Documents/lizchen/BagelNotes"
VAULT_BLOG_DIR = os.path.join(VAULT_DIR, "blog")
VAULT_NOTE_DIR = os.path.join(VAULT_DIR, "note")

REPO_DIR = "/Users/lizchen/Projects/bagelnote-astro"
BLOG_DIR = os.path.join(REPO_DIR, "src/content/blog")
NOTES_DIR = os.path.join(REPO_DIR, "src/content/notes")


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "post"


def parse_frontmatter(text):
    """回傳 (frontmatter dict, 內文)。frontmatter 只支援簡單的 key: value 一行一個。"""
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    raw_fm, body = parts[1], parts[2]
    fields = {}
    for line in raw_fm.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        fields[key.strip()] = value
    return fields, body.strip()


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

    for folder in (VAULT_BLOG_DIR, VAULT_NOTE_DIR):
        candidate = os.path.join(folder, filename)
        if os.path.exists(candidate):
            return candidate

    target = filename.lower()
    for root, _, files in os.walk(VAULT_DIR):
        for f in files:
            if f.lower() == target:
                return os.path.join(root, f)
    return None


def run_git(*args):
    result = subprocess.run(
        ["git", *args], cwd=REPO_DIR, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"git {' '.join(args)} 失敗：\n{result.stderr}")
        sys.exit(1)
    return result.stdout


def git_publish(out_path, commit_message):
    run_git("add", out_path)
    status = run_git("status", "--porcelain", out_path)
    if not status.strip():
        print("內容跟上次發布的一樣，沒有變更可以提交。")
        return
    run_git("commit", "-m", commit_message)
    run_git("push")
    print("已發布上線。")


def do_publish(source_path):
    kind = kind_for_path(source_path)
    if not kind:
        print(
            f"這篇筆記不在 blog/ 或 note/ 資料夾裡，無法自動判斷要發布成長文還是短文。\n"
            f"請把筆記移到 {VAULT_BLOG_DIR} 或 {VAULT_NOTE_DIR} 底下再試一次。"
        )
        sys.exit(1)

    with open(source_path, encoding="utf-8") as f:
        fields, body = parse_frontmatter(f.read())

    slug = slugify(os.path.splitext(os.path.basename(source_path))[0])
    out_dir = BLOG_DIR if kind == "blog" else NOTES_DIR
    out_path = os.path.join(out_dir, f"{slug}.md")

    is_update = os.path.exists(out_path)
    today = date.today().isoformat()

    if is_update:
        with open(out_path, encoding="utf-8") as f:
            existing_fields, _ = parse_frontmatter(f.read())
        pub_date = existing_fields.get("pubDate", today)
    else:
        pub_date = today

    if kind == "note":
        frontmatter = f"---\npubDate: {pub_date}\n---\n\n{body}\n"
        action_word = "更新" if is_update else "發布"
        commit_message = f"{action_word} note: {slug}"
    else:
        title = fields.get("title") or os.path.splitext(os.path.basename(source_path))[0]
        description = fields.get("description", "")
        if not description:
            print(
                "這篇長文的 frontmatter 沒有填 description（一句話描述），"
                "為了避免發布不完整的文章，已中止，沒有寫入或上線任何內容。\n"
                "請在筆記最上面加上：\n\n---\ntitle: ...\ndescription: ...\n---"
            )
            sys.exit(1)

        lines = [f'title: "{title}"', f'description: "{description}"', f"pubDate: {pub_date}"]
        if is_update:
            lines.append(f"updatedDate: {today}")
        frontmatter = "---\n" + "\n".join(lines) + f"\n---\n\n{body}\n"
        action_word = "更新" if is_update else "發布"
        commit_message = f"{action_word} blog: {title}"

    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)

    print(f"已寫入：{out_path}")
    git_publish(out_path, commit_message)


def do_delete(source_path):
    kind = kind_for_path(source_path)
    slug = slugify(os.path.splitext(os.path.basename(source_path))[0])

    candidates = []
    if kind == "blog":
        candidates = [os.path.join(BLOG_DIR, f"{slug}.md")]
    elif kind == "note":
        candidates = [os.path.join(NOTES_DIR, f"{slug}.md")]
    else:
        candidates = [
            os.path.join(BLOG_DIR, f"{slug}.md"),
            os.path.join(NOTES_DIR, f"{slug}.md"),
        ]

    out_path = next((c for c in candidates if os.path.exists(c)), None)
    if not out_path:
        print(
            f"找不到對應的已發布文章（找過：{', '.join(candidates)}），"
            "可能還沒發布過，或是檔名跟 Obsidian 筆記對不上。"
        )
        sys.exit(1)

    run_git("rm", out_path)
    run_git("commit", "-m", f"Delete {os.path.relpath(out_path, REPO_DIR)}")
    run_git("push")
    print(f"已刪除並下線：{out_path}")


def main():
    args = [a for a in sys.argv[1:] if a != "--delete"]
    delete_mode = "--delete" in sys.argv[1:]

    if len(args) < 1:
        print("用法：python scripts/publish_from_obsidian.py <Obsidian 筆記檔名> [--delete]")
        sys.exit(1)

    source_path = find_file(args[0])
    if not source_path:
        print(f"在 {VAULT_DIR} 裡找不到檔案：{args[0]}")
        sys.exit(1)

    if delete_mode:
        do_delete(source_path)
    else:
        do_publish(source_path)


if __name__ == "__main__":
    main()
