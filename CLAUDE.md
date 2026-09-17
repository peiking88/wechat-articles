# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库定位

Claude Code 技能（skill）仓库：钻取微信公众号文章全集。SKILL.md 是给 Claude 的操作指南（触发条件、步骤、风控处置），`scripts/` 下两个脚本是实际执行者。修改行为时 SKILL.md 与脚本必须保持一致——SKILL.md 中的参数（如 `--interval 8`）和被拦形态都有实测依据，不是猜测值。

发布地址：github.com/peiking88/wechat-articles（2026-09-17 由 wechat-article-drill 更名而来，旧地址自动重定向）

## 常用命令

无 build/lint/test。脚本仅用 Python 标准库（硬约束，勿引入第三方依赖），运行即验证：

```bash
# 从单篇文章 HTML 提取公众号标识与合集（输出 JSON）
python3 scripts/extract_album.py article.html

# 解析合集页，列出全部文章（本地文件或 URL 均可，按 mid 升序=由旧到新）
python3 scripts/extract_album.py --album album.html

# 批量抓正文：串行 + 8 秒间隔，断点续抓（重跑同命令只补失败/缺失篇）
python3 scripts/fetch_articles.py urls.txt -o wx_articles --interval 8
```

端到端验证标准见 SKILL.md 的 Verification 段（输出文件数 == urls.txt 去重条数、首行 TITLE 与合集页 data-title 一致、_failed.txt 为空或已知原因）。

## 架构：三段管线

```
入口文章 URL --curl--> article.html --extract_album.py--> {biz, album_id}
    --> 合集页 URL --curl--> album.html --extract_album.py --album--> 文章清单
    --> urls.txt --fetch_articles.py--> wx_articles/NN.txt（TITLE:/URL: 头 + 正文）
```

- `extract_album.py` 双模式：文章模式提取 `__biz`/`album_id`/相关短链（正则，无 HTML parser）；`--album` 模式解析合集页。合集页文章列表藏在 `<li>` 的 `data-link`/`data-title` 属性中，不在 `<a href>` 里——这是解析的正确锚点。
- `fetch_articles.py`：串行 curl，`NN.txt` 按 urls.txt 序号命名（断点续抓依据：文件存在且 >2KB 即跳过），失败写入 `_failed.txt`。
- 正文提取链（`extract_body`）：`og:title` 取标题 → `id="js_content"` div → 去 style/script → 块级标签转行 → 剥标签 → unescape → 压缩空行。正文 <500 字符视为空壳/被拦。

## 微信风控知识（本仓库的核心领域知识）

被拦形态三种，处置不同（2026-09 实测）：

1. **约 17KB 空壳页**（无 `js_content`、title 空）——参数链接常见，换短链 `/s/<token>` 重试
2. **"环境异常"验证页**——真风控，按 IP 维度，冷却 ≥10 分钟；浏览器指纹救不了，仅换出口 IP 有效
3. **约 2KB "未知错误"页**——瞬时拒绝非风控，补全 `Accept-Language: zh-CN,zh;q=0.9` 等浏览器头隔 3 秒重试即过

铁律：串行抓取、8 秒间隔、不对同一 URL 短时间反复重试、不用 MicroMessenger UA（更易 302 到验证页）。抓取产物仅作知识提取用途，不要高频重抓。

## 自动生成的文件（勿手改）

- `.grade.json`、`.skill-forge/`、`scripts/.claude/skills/skill_registry.json`——skill-forge 工具维护的元数据
