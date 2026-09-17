#!/usr/bin/env python3
"""微信公众号文章批量串行抓取 + 正文提取（防风控）。

用法:
  fetch_articles.py urls.txt -o wx_articles --interval 8

行为:
  - 串行 curl（短链/参数链接均可，自带 Accept-Language 浏览器头规避形态③瞬时拒绝），间隔 --interval 秒（默认 8，实测 19 篇连续成功）
  - 自动识别风控空壳页（无 js_content / "环境异常"），标 BLOCKED 继续下一篇
  - 输出 NN.txt，首行 TITLE:/URL:；失败清单写入 <outdir>/_failed.txt
  - 断点续抓: 已存在且 >2KB 的输出跳过，直接重跑本命令只补失败/缺失篇
"""
import argparse
import html as htmllib
import os
import re
import subprocess
import sys
import time

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def extract_body(h: str):
    """文章 HTML → (标题, 正文文本)；空壳/验证页返回 (None, None)。"""
    if "js_content" not in h or "环境异常" in h[:4000]:
        return None, None
    t = re.search(r'<meta property="og:title" content="([^"]*)"', h)
    title = htmllib.unescape(t.group(1)) if t else "untitled"
    m = (re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)<script', h, re.S)
         or re.search(r'<div[^>]*id="js_content"[^>]*>(.*)', h, re.S))
    if not m:
        return None, None
    body = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', m.group(1), flags=re.S)
    body = re.sub(r'</(p|div|section|h[1-6]|li|tr|blockquote)>', '\n', body)
    body = re.sub(r'<br[^>]*>', '\n', body)
    body = re.sub(r'</td>', '\t', body)
    body = re.sub(r'<[^>]+>', '', body)
    body = htmllib.unescape(body)
    body = re.sub(r'[ \t]+\n', '\n', body)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return title, body


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", help="URL 清单文件，一行一个")
    ap.add_argument("-o", "--outdir", default="wx_articles")
    ap.add_argument("--interval", type=float, default=8.0,
                    help="请求间隔秒数（默认 8，更低易触发风控）")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    urls = [u.strip() for u in open(args.urls, encoding="utf-8")
            if u.strip() and u.startswith("http")]
    failed = []
    for i, url in enumerate(urls):
        out = os.path.join(args.outdir, f"{i:02d}.txt")
        if os.path.exists(out) and os.path.getsize(out) > 2048:
            print(i, "cached, skip")
            continue
        r = subprocess.run(["curl", "-s", "-A", UA,
                            "-H", "Accept-Language: zh-CN,zh;q=0.9", url],
                           capture_output=True, text=True, timeout=90)
        title, body = extract_body(r.stdout or "")
        if not body or len(body) < 500:
            print(i, url, "BLOCKED/EMPTY — 冷却 ~10 分钟后重跑续抓")
            failed.append(url)
        else:
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"TITLE: {title}\nURL: {url}\n\n{body}")
            print(i, title[:40], len(body), "OK")
        if i != len(urls) - 1:
            time.sleep(args.interval)

    with open(os.path.join(args.outdir, "_failed.txt"), "w") as f:
        f.write("\n".join(failed))
    print(f"\ndone: {len(urls) - len(failed)}/{len(urls)} ok, "
          f"{len(failed)} failed (see _failed.txt)")


if __name__ == "__main__":
    main()
