---
name: wechat-articles
description: >
  Use when user pastes an mp.weixin.qq.com link and wants that 公众号's full archive: extract
  __biz/album_id, list the 合集, batch-fetch past IP rate-limits, extract text. Even if they
  just say 抓一下这个公众号. Do NOT use for one article URL or Toutiao/微博 feeds.
user-invocable: true
---

# wechat-articles

钻取微信公众号文章全集。微信文章不被外部搜索引擎索引，公众号历史列表需要登录态，但**专题合集页无需登录**且单篇文章 HTML 中藏有发现入口；同时微信按 IP+频率做风控（"环境异常"验证页），直接高频抓取会被拦。本技能封装 2026-09-08 实测有效的完整链路：入口发现 → 合集列表 → 绕风控批量抓取 → 正文提取。

## Prerequisites

- `curl`、`python3`（标准库即可，脚本无第三方依赖）

## Steps

### 1. 抓入口文章，提取公众号标识与合集

先 curl 拿文章 HTML（短链 `/s/<token>` 形式最耐受风控；参数链接被拦时空壳页特征：约 17KB、无 `js_content`、title 为空），再跑提取脚本：

```bash
curl -s -A "<桌面 Chrome UA>" -H "Accept-Language: zh-CN,zh;q=0.9" "https://mp.weixin.qq.com/s/<token>" -o article.html
python3 scripts/extract_album.py article.html
```

输出 JSON：`biz`（公众号唯一标识，即 `__biz` 参数值）、`album_id`（合集，专题连载公众号几乎都有）、合集页 URL、页面内相关文章短链（合集不全时的补齐线索）。无合集时退路：用相关文章短链滚雪球（每篇文章页通常链接 1-2 篇同号文章），或让用户提供链接列表。

被拦形态共三种，处置不同：① 约 17KB 空壳页（无 `js_content`、title 空，参数链接常见）→ 换短链重试；② "环境异常"验证页 → 风控，走 Step 4 冷却；③ 约 2KB "未知错误，请稍后再试"页 → 瞬时拒绝非风控，补全 `Accept-Language` 等浏览器头隔 3 秒重试即过，无需冷却（2026-09-08 实测）。

### 2. 抓合集页，列出全部文章

合集页无需登录，直接 curl。文章列表不在 `<a href>` 里，而在 `<li>` 的 `data-link`/`data-title` 属性中——`extract_album.py --album <合集URL>` 会解析并输出 URL+标题清单（按 mid 排序）。合集可能不全（实测缺篇），与 Step 1 的相关短链、用户提供的链接合并去重。

### 3. 批量抓取正文（防风控）

把最终 URL 清单写入 `urls.txt`（一行一个，短链或参数链接均可），串行抓取：

```bash
python3 scripts/fetch_articles.py urls.txt -o wx_articles --interval 8
```

关键参数与理由：

- `--interval 8`：8 秒间隔实测 19 篇连续成功；更快会触发风控
- 脚本自动检测空壳页/验证页（无 `js_content` 或含"环境异常"），标记 BLOCKED 并继续下一篇，不浪费冷却时间
- 输出按 urls.txt 序号命名（`00.txt`、`01.txt`…），首行 `TITLE:`/`URL:` 便于后续溯源与断点续抓

### 4. 处理风控拦截（若发生）

被拦时的处置顺序（按代价递增）：

1. **冷却等待 ≥10 分钟**再重试被拦的 URL（风控按 IP，实测冷却后恢复）——脚本失败清单保存在 `wx_articles/_failed.txt`，直接重跑即断点续抓
2. 换 URL 形式重试：短链 ↔ 参数链接互换
3. Playwright + 桌面 UA headless（本机 IP 已被拦时通常同样被拦——风控是 IP 维度，浏览器指纹救不了，仅在有代理出口时值得）
4. webReader 等服务端抓取工具（服务端 IP 独立计费，但同样可能被拦）

避免：MicroMessenger UA（更易 302 到验证页）、并发抓取、对同一 URL 短时间反复重试。

## Verification

- `urls.txt` 中每个 URL 对应输出文件非空且含 `TITLE:` 行；`_failed.txt` 为空或已知原因
- 输出文件数 == urls.txt 去重后条数；抽一篇，其文件首行 `TITLE: <og:title>` 与合集页 `data-title` 一致
- 合集数量 vs 实际抓到数量差异在报告中标明（合集缺篇属正常）

## Notes

- 正文提取原理：`og:title` meta 取标题；`id="js_content"` div 取正文，去 style/script → 块级标签转行 → 剥标签 → html.unescape → 压缩空行
- 每篇正文约 6-40KB；19 篇 + 8s 间隔约 3 分钟
- 相关经验可类比其他 JS 渲染+风控站点（如头条，样板 `tdx-cpp/scripts/market-analysis.py` 的 `_fetch_blogger_posts`）：先 curl 试探 → 被拦再真实浏览器 → 仍被拦则冷却
- 抓取产物仅作知识提取用途，尊重平台内容权益，不要高频重抓
