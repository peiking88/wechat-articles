#!/usr/bin/env python3
"""从微信公众号文章/合集页 HTML 提取钻取入口。

用法:
  extract_album.py article.html                 # 提取 __biz / 合集 / 相关短链
  extract_album.py --album <合集页URL或本地文件>  # 列出合集中全部文章(按 mid 排序)

无第三方依赖，输出 JSON 到 stdout。
"""
import argparse
import html as htmllib
import json
import re
import subprocess
import sys

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def load_html(source: str) -> str:
    if source.startswith("http"):
        r = subprocess.run(["curl", "-sL", "-A", UA, source],
                           capture_output=True, text=True, timeout=60)
        return r.stdout
    return open(source, encoding="utf-8", errors="ignore").read()


def extract_from_article(h: str) -> dict:
    """单篇文章 HTML → 公众号标识 / 合集 / 相关文章短链。"""
    biz_m = re.search(r'__biz=([A-Za-z0-9=]+)', h)
    biz = biz_m.group(1) if biz_m else None
    albums = []
    for aid in sorted(set(re.findall(r'album_id=(\d+)', h))):
        albums.append({
            "album_id": aid,
            "url": (f"https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum"
                    f"&__biz={biz or ''}&album_id={aid}&count=100"),
        })
    related = sorted(set(re.findall(r'https://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+', h)))
    title_m = re.search(r'<meta property="og:title" content="([^"]*)"', h)
    author_m = re.search(r'<meta property="og:article:author" content="([^"]*)"', h)
    return {
        "biz": biz,
        "title": htmllib.unescape(title_m.group(1)) if title_m else None,
        "author": author_m.group(1) if author_m else None,
        "albums": albums,
        "related_links": related,
    }


def extract_album_items(h: str) -> list:
    """合集页 HTML → 文章清单。列表在 <li> 的 data-link/data-title 属性中，非 <a href>。"""
    items = {}
    for url, title in re.findall(r'data-link="([^"]+)"\s+data-title="([^"]+)"', h):
        url = url.replace("&amp;", "&").replace("http://", "https://")
        title = htmllib.unescape(title)
        mid = re.search(r'mid=(\d+)', url)
        items[url] = (int(mid.group(1)) if mid else 0, title)
    return [{"mid": m, "title": t, "url": u}
            for u, (m, t) in sorted(items.items(), key=lambda kv: kv[1][0])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="文章 HTML 文件 / URL")
    ap.add_argument("--album", action="store_true",
                    help="把 source 当作合集页，列出全部文章")
    args = ap.parse_args()

    h = load_html(args.source)
    if not h:
        sys.exit("ERROR: 空响应（可能被风控拦截，冷却 ~10 分钟后重试）")
    if "环境异常" in h[:4000] or "verify" in h[:4000].lower():
        sys.exit("ERROR: 命中微信风控验证页，冷却 ~10 分钟后重试")

    result = extract_album_items(h) if args.album else extract_from_article(h)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
