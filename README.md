# wechat-articles

钻取微信公众号文章全集的 Claude Code 技能。

微信文章不被外部搜索引擎索引，公众号历史列表需要登录态，但**专题合集页无需登录**且单篇文章 HTML 中藏有发现入口；同时微信按 IP+频率做风控（"环境异常"验证页），直接高频抓取会被拦。本技能封装实测有效的完整链路：

```
入口文章 → 提取 __biz/合集 → 合集页列全部文章 → 防风控批量抓取 → 正文提取
```

## 安装

将本仓库放入 Claude Code 技能目录（如 `~/.claude/skills/` 或 hot-skills 安装目录）即可，无第三方依赖（仅 `curl` + Python 标准库）。

## 使用

对 Claude 粘贴一个 `mp.weixin.qq.com` 文章链接并说"抓一下这个公众号"即自动触发。手动执行等效命令：

```bash
# 1. 提取公众号标识与合集
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36" \
  -H "Accept-Language: zh-CN,zh;q=0.9" \
  "https://mp.weixin.qq.com/s/<token>" -o article.html
python3 scripts/extract_album.py article.html

# 2. 抓合集页，列出全部文章（URL+标题清单）
python3 scripts/extract_album.py --album "<合集页URL>"

# 3. 批量抓正文（串行 + 8 秒间隔，断点续抓；脚本已内置 UA + Accept-Language 浏览器头）
python3 scripts/fetch_articles.py urls.txt -o wx_articles --interval 8
```

## 风控要点

| 被拦形态   | 特征                               | 处置                     |
| ---------- | ---------------------------------- | ------------------------ |
| 空壳页     | 约 17KB、无 `js_content`、title 空 | 换短链 `/s/<token>` 重试 |
| 风控验证页 | "环境异常"                         | 冷却 ≥10 分钟（IP 维度） |
| 瞬时拒绝   | 约 2KB "未知错误"页                | 补全浏览器头隔 3 秒重试  |
| 全域被拦   | 补头重试 2-3 次仍持续、短链/参数链接同拒、冷却 ≥10 分钟无效 | 冷却救不回来，切 Step 4 服务端兜底链 |

全域被拦时拿不到文章原始 HTML（无 `__biz`/`album_id`，合集页不可用），兜底链：webReader 服务端抓正文（含作者手写的上一篇/下一篇预告）→ 搜狗微信搜索 `txt-box`/`txt-info` 摘要枚举篇目（摘要常含"下一篇预告"全文）→ 搜狗 `/link` 跳转**同会话**解析出带 signature 的参数 URL → 逐篇滚雪球补齐。

铁律：串行抓取、8 秒间隔、不对同一 URL 短时间反复重试、不用 MicroMessenger UA。抓取产物仅作知识提取用途，请尊重平台内容权益，不要高频重抓。

## 许可

个人研究用途。
