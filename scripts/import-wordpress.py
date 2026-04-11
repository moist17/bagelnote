#!/usr/bin/env python3
"""
WordPress XML → Astro Markdown 轉換腳本
"""

import xml.etree.ElementTree as ET
import html2text
import os
import re
from datetime import datetime

XML_FILE = "/Users/lizchen/Downloads/bagelnote.WordPress.2026-04-11.xml"
OUTPUT_DIR = "/Users/lizchen/Projects/bagelnote-astro/src/content/blog"

NS = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'wp': 'http://wordpress.org/export/1.2/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/'
}

def slugify(text):
    """把標題轉成適合當檔名的格式"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = text.strip('-')
    return text or "post"

def convert_html_to_markdown(html_content):
    """把 HTML 內容轉成 Markdown"""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # 不自動換行
    return h.handle(html_content).strip()

def get_categories(item):
    """取得文章分類"""
    categories = []
    for cat in item.findall('category'):
        domain = cat.get('domain', '')
        if domain == 'category':
            categories.append(cat.text)
    return categories

def get_tags(item):
    """取得文章標籤"""
    tags = []
    for cat in item.findall('category'):
        domain = cat.get('domain', '')
        if domain == 'post_tag':
            tags.append(cat.text)
    return tags

def parse_and_export():
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    channel = root.find('channel')

    posts = []
    for item in channel.findall('item'):
        post_type = item.find('wp:post_type', NS)
        status = item.find('wp:status', NS)

        if post_type is None or post_type.text != 'post':
            continue
        if status is None or status.text != 'publish':
            continue

        title = item.find('title').text or "Untitled"
        raw_date = item.find('wp:post_date', NS).text or ""
        content_html = item.find('content:encoded', NS).text or ""
        excerpt_html = item.find('excerpt:encoded', NS).text or ""
        slug = item.find('wp:post_name', NS).text or slugify(title)
        categories = get_categories(item)
        tags = get_tags(item)

        # 格式化日期
        try:
            pub_date = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S").strftime("%b %d %Y")
        except:
            pub_date = raw_date[:10]

        # 轉換內容
        content_md = convert_html_to_markdown(content_html)
        description = convert_html_to_markdown(excerpt_html).replace('\n', ' ').strip()
        if not description and content_md:
            # 沒有摘要就取前 100 字
            description = content_md[:100].replace('\n', ' ').strip() + "..."

        posts.append({
            "title": title,
            "slug": slug,
            "pub_date": pub_date,
            "description": description,
            "categories": categories,
            "tags": tags,
            "content": content_md,
        })

    # 刪除範本預設文章
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith('.md') or f.endswith('.mdx'):
            os.remove(os.path.join(OUTPUT_DIR, f))
            print(f"  刪除範本: {f}")

    # 寫入 Markdown 檔案
    for post in posts:
        filename = f"{post['slug']}.md"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # 組裝 frontmatter
        cats_str = ""
        if post["categories"]:
            cats_str = "\ncategories:\n" + "\n".join(f"  - \"{c}\"" for c in post["categories"])

        tags_str = ""
        if post["tags"]:
            tags_str = "\ntags:\n" + "\n".join(f"  - \"{t}\"" for t in post["tags"])

        md_content = f"""---
title: "{post['title'].replace('"', "'")}"
description: "{post['description'].replace('"', "'")}"
pubDate: "{post['pub_date']}"{cats_str}{tags_str}
---

{post['content']}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"  ✓ {filename}")

    print(f"\n完成！共匯入 {len(posts)} 篇文章。")

if __name__ == "__main__":
    parse_and_export()
