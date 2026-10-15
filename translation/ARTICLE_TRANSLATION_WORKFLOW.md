---
title: "单篇文章翻译流程规范"
type: "agent-guide"
---

# 单篇文章翻译流程规范

## 职责与边界

单篇文章通常在数字化核验完成后，按文章原有的自然结构直接完成翻译、审校与定稿。

Owner 明确授权时，可以先翻译尚未完成数字化核验的底本。将数字化原文的实际状态、未决核验风险和授权范围记入 handoff 的原文疑点；不得把翻译完成记作原文验收或公开许可。先行翻译授权不自动包含 Finalization，进入定稿前须有 Owner 对该阶段的明确授权。

已有译文可以由 Owner 指定所用原文与译文、校阅范围、当前阶段和完成条件后进入对应校阅步骤。只执行指定任务，沿用现有工件，不补造此前的翻译、审校、裁决或 Git 历史。

单篇文章不进入 [`BOOK_PREPROCESSING.md`](../digitization/BOOK_PREPROCESSING.md) 或 [`TRANSLATION_PREPROCESSING.md`](../digitization/TRANSLATION_PREPROCESSING.md)，不建立单元、分组、批次、书籍状态文件，也不专门建立 block-id。底本已有 block-id 时保持不变。

书籍翻译依 [`TRANSLATION_WORKFLOW.md`](TRANSLATION_WORKFLOW.md)。

流程：

```text
Operator 翻译与交接
→ Reviewer 盲审
→ Reviewer 明审
→ Owner 裁决
→ Reviewer Finalization
```

默认不建立审校分支、不要求提交。Owner 明确要求提交时，依项目 `AGENTS.md`。

---

## 0. 基本规则

### 执行单位

每次处理一篇完整文章。

除下述正文范围取舍和角色规范规定的单篇文章 Markdown 结构规范化外，原文与译文按自然段和结构元素保持对应，不因纯排版换行拆分段落。

### 译文正文范围

译文正文不保留文章署名（含原文译者署名）、作者简介、资助说明，以及作为出版附属信息独立列出的版权年份、出版日期、收稿或修订日期。

正文、引文、注释和参考文献中的人物姓名与时间信息照常保留。作品与出版信息按 [`STRUCTURE.md`](../STRUCTURE.md) 保存在现有元数据中。

上述省略不视为漏译。结构对应只核对保留的内容；被整体省略的块不保留 block-id，不留空块，保留块不重编编号。

修订、审校、定稿及同步数字化原文时，保留 Owner 已确认的人工删减，不为逐项对应原文而补回。

### 角色

| 角色     | 职责                                   |
| -------- | -------------------------------------- |
| Operator | 翻译、自查、handoff                    |
| Reviewer | 盲审、明审、术语候选处理、Finalization |
| Owner    | 裁决译法、原文疑点与术语，决定最终文本 |

Reviewer 必须由未参与本次 Operator 翻译的独立 Agent 或会话承担。

每个角色完成当前步骤后停止，不自行进入下一角色。

### 工件

```text
<译文作品目录>/
  <作品>.md
  work.json
  handoff.md
```

- `<作品>.md`：最终译文正文。
- `work.json`：作品与底本信息。
- `handoff.md`：本次翻译流程的唯一交接文件，流程结束后保留。

单篇文章不建立 `index.json`、`status.json`、reports、comments、source-issues 或 review-notes。

流程结束后保留 handoff 中当时的交接和裁决。Owner 交办后续处理时，在同一文件追加本次范围、必要问题和处理结果，不覆盖旧裁决，也不把原有 Finalization 作为本次任务已经完成的依据。

---

## 1. Operator 翻译与交接

### 读取

- 本文件；
- [`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md)；
- [`PUNCTUATION.md`](PUNCTUATION.md)；
- [`GLOSSARY_RULES.md`](../glossary/GLOSSARY_RULES.md)；
- 相关 glossary 条目；
- `work.json`；
- 全文原文。

### 翻译

1. 按正文范围完成全文译文。
2. 按翻译、标点和现行术语权威自查。
3. 核对保留的段落、标题、引文、脚注及其他结构对应。
4. 不直接修改 glossary；新增或修改建议写入 handoff。

### 原文疑点

原文、OCR 或底本疑点写入 handoff，记录：

- 位置；
- 问题；
- 可确认的候选文字或依据；
- 当前译文采用的处理。

不影响可靠翻译的疑点，记录后继续。

无法可靠判断且影响翻译的内容，不猜补，交 Owner 裁决后停止。

### Handoff

翻译完成后建立或更新 `handoff.md` 的 `Operator 交接`：

- 译法疑问；
- 原文 / OCR / 底本疑点；
- glossary 新增或修改建议。

只记录后续角色仍需处理的信息。

完成后交 Reviewer，并停止。

---

## 2. Reviewer 盲审

### 读取

第一轮审阅只读取：

- 本文件；
- [`REVIEW_STYLE.md`](REVIEW_STYLE.md)；
- [`PUNCTUATION.md`](PUNCTUATION.md)；
- [`GLOSSARY_RULES.md`](../glossary/GLOSSARY_RULES.md)；
- 相关 glossary 条目；
- 全文原文；
- 当前译文。

盲审完成前不读取 `handoff.md`。

### 审阅

1. 对全文进行一次独立审阅。
2. 直接修改能够可靠判断的问题。
3. 按准确性、语言自然度、术语一致性审查译文。
4. 保留无法确定的问题，留待明审处理。

本流程不要求 `rv:` 注释，也不记录普通审校修改历史。

全文盲审完成后，进入明审。

---

## 3. Reviewer 明审

### 读取

读取 `handoff.md`，处理：

- Operator 交接的问题；
- 盲审阶段暂留的问题；
- 与上述问题直接相关的必要上下文。

明审不是第二次全文审校。

### 处理

能够确定的问题直接修改译文。

涉及 glossary 时：

- 可以新增或修改 `provisional` 条目；
- 不直接改写已有 `approved` 权威；
- 对 `approved` 条目的实质变更作为建议交 Owner。

原文、OCR 或底本疑点记录核对依据和结论。

### 写入 handoff

在 `Reviewer 处理` 中记录：

- Operator 问题的处理结果；
- 实际 glossary 变更；
- 新增待裁决问题。

待裁决问题至少包含：

- 编号；
- 位置；
- 必要原文；
- 当前译文；
- 可选方案；
- 简要理由。

普通审校修改不逐项记录。

完成后交 Owner，并停止。

---

## 4. Owner 裁决

Owner 查看最终译文、`handoff.md` 和需要裁决的问题。

Owner 决定：

- 译文采用何种处理；
- 原文疑点采用何种读法或是否保留未决；
- glossary 建议批准、调整、保留为候选或撤回。

Owner 直接修改译文，并在 `Owner 裁决` 中记录最终结论。

术语裁决应明确：

- 词条；
- 最终译法；
- 状态；
- 必要的撤回或调整。

不记录完整对话或普通修改历史。

完成后停止，由 Reviewer Finalization。

---

## 5. Reviewer Finalization

Reviewer 读取 Owner 已修改的译文和最终 handoff。

先行翻译未核验底本的任务，须确认 Owner 已明确授权当前 Finalization 阶段；未获授权时停止，不宣告流程完成。

检查：

1. Owner 裁决已落实到译文。
2. 明确的术语裁决已落实到 glossary。
3. 正文范围符合基本规则，保留的标题、段落、引文、脚注和其他结构对应正确，Owner 已确认的人工删减未被补回。
4. 摘要分段与引言标题符合角色规范。
5. 参考文献及其引证符合角色规范。
6. 译文中没有流程性残留。

Finalization 只处理明确裁决和机械一致性，不重新进行全文审校。

若发现 Owner 裁决未落实或正文与记录冲突，列出位置交 Owner，不自行重新裁决。

检查通过后，在 handoff 末尾记录 Finalization 结果并停止。

Finalization 结果只表示本次授权范围内的定稿检查完成，不改变数字化原文的核验状态，也不自动表示译文最终质量验收、成书排版完成或取得公开许可。

---

## 6. Handoff

`handoff.md` 使用以下结构：

```markdown
# 翻译交接

## Operator 交接

### 译法疑问

### 原文疑点

### 术语建议

## Reviewer 处理

### 交接问题处理

### 术语变更

### 待裁决问题

## Owner 裁决

## Finalization
```

问题使用连续编号：

```text
H-001
H-002
...
```

每项记录：

- 类别；
- 位置；
- 必要原文和当前处理；
- 问题或建议；
- 必要理由。

Reviewer 和 Owner 处理已有问题时沿用原编号，不重复建立同一问题。

位置使用文章自身的自然结构定位，例如：

- 小节标题；
- 段首短引；
- 引文开头；
- 脚注号。

---

## 7. 术语权限

术语归属、字段、状态和权威依 [`GLOSSARY_RULES.md`](../glossary/GLOSSARY_RULES.md)。

- Operator 使用现行权威，只提出建议。
- Reviewer 可以处理 `provisional` 条目。
- `approved` 条目的实质变更必须由 Owner 裁决。
- Owner 决定最终译法和状态。
- Finalization 只落实明确裁决。
- 本流程只处理当前文章涉及的词条，不回改其他译文或执行跨作品术语扫描。

---

## 8. 完成条件

一篇文章只有同时满足以下条件才算完成：

- Operator 已完成全文翻译和自查；
- 正文范围符合基本规则，保留的段落和结构对应正确，Owner 已确认的人工删减未被补回；
- Reviewer 已完成一次独立盲审；
- handoff 已在盲审后完成明审处理；
- 原文疑点、译法疑问和术语问题已有处理结果或 Owner 明确决定；
- Owner 裁决已落实到最终译文；
- glossary 状态与 Owner 裁决一致；
- Reviewer Finalization 已通过；
- 摘要分段与引言标题符合角色规范；
- 参考文献及其引证符合角色规范；
- 译文中没有流程性残留。

满足以上条件后，本次单篇文章翻译流程结束。
