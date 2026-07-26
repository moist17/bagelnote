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

支援的 frontmatter 欄位：
    title, description, pubDate, heroImage, categories, tags, updatedDate
"""

import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date

VAULT_DIR = "/Users/lizchen/Library/Mobile Documents/iCloud~md~obsidian/Documents/lizchen/BagelNotes"
VAULT_BLOG_DIR = os.path.join(VAULT_DIR, "blog")
VAULT_NOTE_DIR = os.path.join(VAULT_DIR, "note")
VAULT_ATTACHMENTS_DIR = os.path.join(VAULT_DIR, "_attachments", "blog")

REPO_DIR = "/Users/lizchen/Projects/bagelnote-astro"
BLOG_DIR = os.path.join(REPO_DIR, "src/content/blog")
NOTES_DIR = os.path.join(REPO_DIR, "src/content/notes")
ASSETS_DIR = os.path.join(REPO_DIR, "src/assets/blog")


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "post"


def parse_frontmatter_raw(text):
    """回傳 (raw frontmatter string, 內文)。"""
    if not text.startswith("---"):
        return "", text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text.strip()
    return parts[1], parts[2].strip()


def parse_frontmatter(text):
    """回傳 (frontmatter dict, 內文)。支援 list 欄位（categories, tags）。"""
    raw_fm, body = parse_frontmatter_raw(text)
    if not raw_fm:
        return {}, body

    fields = {}
    current_key = None
    current_list = None

    for line in raw_fm.splitlines():
        # list item
        if line.strip().startswith("- ") and current_key and current_list is not None:
            current_list.append(line.strip()[2:].strip().strip('"').strip("'"))
            continue

        if ":" in line and not line.startswith(" "):
            # 儲存前一個 list
            if current_key and current_list is not None:
                fields[current_key] = current_list
                current_list = None
                current_key = None

            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if value == "":
                # 可能是 list
                current_key = key
                current_list = []
            else:
                fields[key] = value

    # 最後一個 list
    if current_key and current_list is not None:
        fields[current_key] = current_list

    return fields, body


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


def git_publish(out_paths, commit_message):
    for p in out_paths:
        run_git("add", p)
    # 檢查是否有任何變更
    status_lines = []
    for p in out_paths:
        s = run_git("status", "--porcelain", p)
        if s.strip():
            status_lines.append(s)
    if not status_lines:
        print("內容跟上次發布的一樣，沒有變更可以提交。")
        return
    run_git("commit", "-m", commit_message)
    run_git("push")
    print("已發布上線。")


def resolve_hero_image(slug, hero_image_value):
    """
    將 Obsidian 裡的 heroImage 路徑轉換成 repo 需要的路徑。
    Obsidian 存的是檔名（例如 image.png），
    repo 需要的是 ../../assets/blog/<slug>/<filename>
    """
    if not hero_image_value:
        return None
    filename = os.path.basename(hero_image_value)
    return f"../../assets/blog/{slug}/{filename}"


def copy_image(slug, filename):
    """
    把 Obsidian _attachments/blog/<slug>/<filename> 複製到 repo assets/blog/<slug>/<filename>。
    回傳目的地路徑，找不到來源則回傳 None。
    """
    src = os.path.join(VAULT_ATTACHMENTS_DIR, slug, filename)
    dst_dir = os.path.join(ASSETS_DIR, slug)
    dst = os.path.join(dst_dir, filename)

    if not os.path.exists(src):
        print(f"找不到圖片：{src}，略過圖片複製。")
        return None

    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def copy_hero_image(slug, hero_image_value):
    """
    把 Obsidian _attachments/blog/<slug>/ 裡的圖片複製到 repo assets/blog/<slug>/。
    回傳是否成功。
    """
    if not hero_image_value:
        return False
    filename = os.path.basename(hero_image_value)
    return copy_image(slug, filename) is not None


def copy_inline_images(slug, body):
    """
    掃描內文裡所有 ![...](路徑) 的圖片，把檔案從 Obsidian _attachments 複製到 repo assets，
    並把內文路徑統一轉換成 ../../assets/blog/<slug>/<filename>。
    回傳 (新內文, 成功複製的圖片路徑清單)。
    """
    copied_paths = []
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

    def replace_img(match):
        alt = match.group(1)
        path = match.group(2)
        filename = os.path.basename(path)
        repo_path = f"../../assets/blog/{slug}/{filename}"
        dst = copy_image(slug, filename)
        if dst:
            copied_paths.append(dst)
        return f"![{alt}]({repo_path})"

    new_body = img_pattern.sub(replace_img, body)
    return new_body, copied_paths


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
        pub_date = fields.get("pubDate", today)

    out_paths = [out_path]

    # 處理內文圖片（blog 和 note 都適用）
    body, inline_img_paths = copy_inline_images(slug, body)
    out_paths.extend(inline_img_paths)

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

        # heroImage
        hero_image = fields.get("heroImage", "")
        if hero_image:
            repo_hero = resolve_hero_image(slug, hero_image)
            lines.append(f'heroImage: "{repo_hero}"')
            img_copied = copy_hero_image(slug, hero_image)
            if img_copied:
                img_asset_path = os.path.join(ASSETS_DIR, slug, os.path.basename(hero_image))
                out_paths.append(img_asset_path)

        # categories
        categories = fields.get("categories", [])
        if isinstance(categories, list) and categories:
            lines.append("categories:")
            for cat in categories:
                lines.append(f'  - "{cat}"')
        elif isinstance(categories, str) and categories:
            lines.append(f"categories:\n  - \"{categories}\"")

        # tags
        tags = fields.get("tags", [])
        if isinstance(tags, list) and tags:
            lines.append("tags:")
            for tag in tags:
                lines.append(f'  - "{tag}"')
        elif isinstance(tags, str) and tags:
            lines.append(f"tags:\n  - \"{tags}\"")

        frontmatter = "---\n" + "\n".join(lines) + f"\n---\n\n{body}\n"
        action_word = "更新" if is_update else "發布"
        commit_message = f"{action_word} blog: {title}"

    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)

    print(f"已寫入：{out_path}")
    git_publish(out_paths, commit_message)


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

    filename = args[0].replace("\\", "")
    source_path = find_file(filename)
    if not source_path:
        print(f"在 {VAULT_DIR} 裡找不到檔案：{filename}")
        sys.exit(1)

    if not delete_mode:
        time.sleep(1)

    if delete_mode:
        do_delete(source_path)
    else:
        do_publish(source_path)


if __name__ == "__main__":
    main()
