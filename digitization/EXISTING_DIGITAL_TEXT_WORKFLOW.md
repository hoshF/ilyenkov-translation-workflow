---
title: "已有数字文本处理流程规范"
type: "agent-guide"
---

# 已有数字文本处理流程规范

## 适用判定

以下底本使用本流程：站点 HTML、可靠电子书文本、XML、TXT 及其他已有机器可读正文的来源。

输入是选定的数字文本来源，以及该作品的影印底本（若有）。产出是经核验的 Markdown 正文、
必要图片和作品元数据。章节单元、语义块、block-id、翻译分组与批次在后续流程中建立。

正文达到 `human_verified` 后按作品类型分流：

- 书籍进入 [`BOOK_PREPROCESSING.md`](BOOK_PREPROCESSING.md)；
- 单篇文章直接进入 [`ARTICLE_TRANSLATION_WORKFLOW.md`](../translation/ARTICLE_TRANSLATION_WORKFLOW.md)。

## 状态

正文状态依次为：

```text
html_conversion_unverified
        ↓
html_conversion_human_collated
        ↓
human_verified
```

| `text_status` | 条件 |
| --- | --- |
| `html_conversion_unverified` | 已形成完整正文，尚未人工核验 |
| `html_conversion_human_collated` | 已逐单元对照来源核验，仍有疑难或尚未完成最终验收 |
| `human_verified` | 正文、注释、作品与版本、关键著录信息均已确认 |

## 第 1 步——保存来源

由任务指定本地来源目录、原文作品目录和临时目录。站点来源保存在以站点命名的本地目录中：

```text
<本地来源目录>/<站点名>/
  sources.json
  <栏目>/<原站文件名>.html          # 单篇
  <栏目>/<作品目录>/index.html      # 多单元作品的目录页
  <栏目>/<作品目录>/<原站文件名>.html
```

`<站点名>` 取自被抓取的站点，各来源用各自的名字。EPUB、FB2、XML、TXT 等本地来源保留原件，明确其位置、作品与版本；不套用站点栏目结构。

保存约定：

- 原站文件名保持不变，使作品内部的相对链接继续可用；
- 按来源站点自身的栏目组织，栏目目录名用转写 slug；
- 统一保存为 UTF-8；
- 删除站点导航、版面表格、访问统计及其他非正文元素；
- 保留正文与作品原有结构。

采集站点来源时，`sources.json` 至少记录：

```json
{
  "site": "<站点标识>",
  "source_page": "<抓取入口页>",
  "retrieved": "<抓取日期>",
  "note": "<编码、剥离范围、文件名约定等处理说明>",
  "sections": { "<栏目 slug>": "<站上栏目名>" },
  "files": [
    { "file": "<栏目>/<文件名>", "url": "<原始地址>", "title": "<标题>", "kind": "text" }
  ]
}
```

`kind` 区分 `text`（正文）与 `scan`（站上提供的影印件）。

## 第 2 步——转换为 Markdown

转换结果放在任务指定的原文作品目录。已有按栏目、语言或来源组织的目录时，沿用其组织方式。

按单元数分两种形态。

**单篇作品**——`<work-id>.md`，元数据写在 YAML frontmatter：

```yaml
title: "<原文标题>"
type: "<作品类型>"
text_status: "<当前状态>"
source_url: "<原始地址>"
```

**多单元作品**——目录 `<work-id>/`：

```text
work.json                # work_id、title、edition 或 year、source_url、text_status
index.md                 # 作品标题与各单元的链接
uNNN-<slug>.md           # 单元正文
```

`uNNN` 按作品顺序三位编号。已分配的编号保持稳定，后续调整不得仅为恢复连续顺序而重排。
`index.md` 只列标题与链接，不含正文。

转换保留标题层级、自然段、引文、列表、脚注、表格与强调。

不得静默改写、翻译、现代化拼写、校正事实或补齐缺文。

## 第 3 步——核验

正文对照选定的数字文本来源逐单元核验，检查：

- 正文、注释、图注与表格是否完整；
- 单元顺序与作品目录是否一致；
- 人名、术语、数字、日期、引文和特殊字符是否正确；
- 站点导航与非正文元素是否已删除；
- 作品与版本是否可以确定。

逐单元核验完成但仍有疑难或尚未完成最终验收时，写入 `html_conversion_human_collated`。

数字文本与影印底本在文字上冲突时，按影印底本改正该处，并把差异写入 `source-issues.json`。字段要求依 [`STRUCTURE.md`](../STRUCTURE.md)。
正文基础仍是该数字文本，个别改正不转为从 PDF 数字化正文。

最终验收检查作品身份、版本、单元完整性、正文结构、元数据和登记。全部通过后写入 `human_verified`。

## 第 4 步——同步元数据与既有索引

按 [`STRUCTURE.md`](../STRUCTURE.md) 检查作品元数据、采用的来源、正文位置与真实状态。已有来源清单或作品索引时同步更新，不另建平行登记。

最终检查：

- 所有 JSON 均可解析；
- 使用 `sources.json` 时，每个 `kind: text` 条目都有对应的转换结果或明确的不转换理由；
- 单元文件名与 `index.md` 的链接一致；
- 正文中没有站点导航、版面表格或访问统计残留；
- 作品元数据中的来源与状态符合实际；已使用的来源清单、作品索引与正文位置一致。

默认不提交 Git。只有明确要求时才提交。
