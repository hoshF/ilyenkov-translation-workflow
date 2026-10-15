---
title: "翻译流程规范"
type: "agent-guide"
---

# 翻译流程规范

## 职责与边界

本文件只执行 [`TRANSLATION_PREPROCESSING.md`](../digitization/TRANSLATION_PREPROCESSING.md) 已建立的书籍批次，以既有 `index.json` 和 `status.json` 为任务结构。

本流程不创建或重构单元、分组、批次、`index.json` 或 `status.json`。单篇文章执行 [`ARTICLE_TRANSLATION_WORKFLOW.md`](ARTICLE_TRANSLATION_WORKFLOW.md)。

Owner 明确要求执行完整书籍翻译流程时，授权包括本流程规定的分支、提交和合并。仅交办调查、检查、部分翻译或规范修订，以及读取本文件，均不构成该授权；这些任务的 Git 操作依项目 `AGENTS.md`。没有相应授权时，不自行执行分支、提交或合并，不虚填 commit 绑定，也不宣告批次完成。

Owner 明确授权时，可以先翻译尚未完成数字化核验的底本。将数字化原文的实际状态、未决核验风险和授权范围记入 `source-issues.json`，handoff 引用对应 issue，不重复登记同一问题；不得把翻译完成记作原文验收或公开许可。先行翻译授权不自动包含 Finalization，进入定稿前须有 Owner 对该阶段的明确授权。

已有译文的指定范围校阅依 [`REVIEW_STYLE.md`](REVIEW_STYLE.md) 的「已有译文校阅入口」，不反向建立本流程的批次或提交历史。

Operator、Reviewer 开始各自工作前必须完整阅读本文档。

本流程以**批次（batch）**为执行单位，只处理当前未完成批次。

全书所有批次均达到 `translated` 后，本流程结束。后续全书统稿依 `CONSOLIDATION.md`。

---

## 0. 核心规则

### 执行单位

- **分组（group）**：按内容性质、体例和翻译上下文组织的一组单元，定义在 `index.json`。
- **批次（batch）**：翻译流程的实际执行单位，定义在 `status.json`。
- **单元（unit）**：按作品目录划分的章节或内容单元。

翻译、审校、Owner 裁决和提交均以批次为单位。

### 稳定数据

`index.json` 定义稳定的翻译任务结构。

进入翻译流程后不得因普通翻译或审校工作修改 `index.json`。

`status.json` 只保存：

- 批次状态；
- `operator_commit`；
- `reviewer_commit`。

### 已完成批次

正常批次流程不得修改已经 `translated` 的批次译文。

后续工作发现已完成批次存在问题时，按「问题分流」处理，不直接回改。

### 角色停止

每个角色只执行自己当前步骤。

完成规定的提交或裁决后必须停止，不自行进入下一角色步骤。

---

## 1. 角色

| 角色     | 职责                                                       | 承担者 |
| -------- | ---------------------------------------------------------- | ------ |
| Operator | 翻译、术语符合性自查、handoff、closeout、后续上下文同步    | Agent  |
| Reviewer | 盲审、明审、reports、术语建议、Finalization                | Agent  |
| Owner    | 审核 Reviewer 修改与建议、裁决疑难、决定最终译文与术语权威 | 人     |

Owner 的最终裁决高于 Operator 和 Reviewer 的建议。

Reviewer 对 glossary 的新增或修改，在 Owner 裁决前不视为最终权威；具体权限与状态依 `glossary/GLOSSARY_RULES.md`。

---

## 2. 工件

### 全书共用

| 文件                 | 用途                                               |
| -------------------- | -------------------------------------------------- |
| `index.json`         | 分组和 unit 结构                                   |
| `status.json`        | 批次、状态与 commit 绑定                           |
| `comments.md`        | 后续未翻译批次仍需知道的作品级上下文               |
| `source-issues.json` | 原文、OCR 或底本问题                               |
| `review-notes.json`  | 已完成批次中发现、留待统稿处理的具体译文或体例问题 |
| `glossary/`          | 跨作品术语权威                                     |

### 每批次

```text
<batch_id>-handoff.md
<batch_id>-reports.md
```

`handoff`：

> Operator → Reviewer

只保存当前批次翻译后仍需 Reviewer 知道的信息。

`reports`：

> Reviewer → Owner → Operator

保存明审意见、术语变更及 Owner 最终裁决。

流程结束后保留 handoff 与 reports 中当时的交接和裁决，不随当前 glossary 或译文变化改写历史。后续必要结论按问题分流追加到现有工件；不得覆盖已经闭环的裁决或 review-note，也不重复记录 Git 已保存的普通修改历史。

### 相关规范

| 规范                         | 用途                         |
| ---------------------------- | ---------------------------- |
| `TRANSLATION_STYLE.md`       | Operator 翻译规则            |
| `REVIEW_STYLE.md`            | Reviewer 审校规则            |
| `PUNCTUATION.md`             | 标点和字体样式转换           |
| `REVIEW_NOTES.md`            | review-note 的登记范围和格式 |
| `glossary/GLOSSARY_RULES.md` | glossary 的归属、状态和权限  |

---

## 3. 分支、提交与状态

### 正常提交序列

一个批次正常产生七个提交：

```text
translation
→ handoff
→ blind-review
→ open-review
→ finalize
→ merge
→ closeout
```

其中：

```text
main:
translation ── handoff ─────────────────────── merge ── closeout
     │                                          ╱
     └── blind-review ── open-review ── finalize
```

Reviewer 审校分支从 `translation` commit 创建。

Operator 随后继续在 `main` 提交 handoff。

Reviewer 的盲审分支不包含 handoff，因此最终使用正常 merge commit 汇合两条历史。

### commit 命名

格式：

```text
<type>(<group>-<batch>): ...
```

例如：

```text
translation(14-b01): ...
blind-review(14-b01): ...
closeout(14-b01): ...
```

### commit 绑定

`operator_commit`：

> 当前批次的 `translation` commit。

在后续 `handoff` commit 中写入 `status.json`。

`reviewer_commit`：

> Reviewer 分支最终合回 `main` 后产生的 `merge` commit。

在后续 `closeout` commit 中写入 `status.json`。

绑定保存相应步骤的实际提交，不换绑为最新修改或统稿提交。事实性回填须有明确提交证据，不得为补齐流程而虚填 hash。

### 状态

```text
untranslated
      ↓ translation
in_progress
      ↓ closeout
translated
```

只允许：

- `translation`：`untranslated → in_progress`
- `closeout`：`in_progress → translated`

其他步骤不得主动修改 `status`。

`translated` 表示当前批次已按本流程完成，不表示原文已经核验、全书统稿或成书排版已经完成，也不赋予公开许可。后续发现具体问题时按问题分流处理，不因此回退批次状态。

---

## 4. 批次流程

### 第 0 步 — Operator 起手

#### 读取

1. `status.json`
2. `index.json`
3. `TRANSLATION_STYLE.md`
4. `PUNCTUATION.md`
5. `glossary/`
6. `comments.md`
7. 当前批次全部原文

#### 操作

从 `status.json` 取得下一个 `untranslated` 批次，并确认：

- group 正确；
- batch 正确；
- unit 与 `index.json` 一致。

#### 完成

进入第 1 步。

---

### 第 1 步 — Operator 翻译

#### 操作

1. 翻译当前批次全部 unit。
2. 保持底本与译文 block-id 对应。
3. 按 glossary 检查已有术语。
4. 按 `TRANSLATION_STYLE.md` 与 `PUNCTUATION.md` 完成译文。

#### 原文存疑

遇到原文、OCR 或底本疑点时登记到 `source-issues.json`。

处理原则：

- 不影响可靠翻译的，按能够确认的内容继续；
- 有明确证据能够可靠恢复的明显错误，按原文存疑规则处理；
- 无法可靠恢复的内容不得猜补；
- 文本完整但事实错误时，不因常识改写原文；
- 作者观点、用词习惯或不符合现代学科规范，不属于原文存疑。

只有疑点导致当前内容无法可靠翻译时才交 Owner。

#### 提交

提交：

- 当前批次译文；
- 本步骤新增或修改的 `source-issues.json`；
- `status`：`untranslated → in_progress`。

```text
translation(<group>-<batch>): ...
```

取得该 commit hash。

#### 完成

进入第 2 步。

---

### 第 2 步 — Operator Handoff

#### 操作

将上一提交的 hash 写入：

```text
status.json.operator_commit
```

建立：

```text
<batch_id>-handoff.md
```

只记录 Reviewer 后续真正需要知道的信息：

- Operator 拿不准的词义、句义或翻译选择；
- 当前选择的必要理由；
- glossary 新增或修改建议；
- 已登记的 source issue id。

例如：

```text
原文存疑：S-013, S-014
```

不要记录：

- 普通翻译过程；
- 已经解决的问题；
- glossary 已明确规定的内容；
- 可以直接从 diff 得出的修改历史。

#### 提交

`operator_commit` 写入和 handoff 一起提交：

```text
handoff(<group>-<batch>): ...
```

不得单独增加 status 提交。

#### 完成

Operator 停止。

---

### 第 3 步 — Reviewer 盲审

#### 起点

从当前批次的 `translation` commit 创建独立审校分支。

#### 禁止

**盲审完成前不得读取 `<batch_id>-handoff.md`。**

#### 读取

只使用：

- 当前批次原文；
- `operator_commit` 中的译文；
- `glossary/`；
- `REVIEW_STYLE.md`；
- `PUNCTUATION.md`。

#### 操作

直接修改译文。

优先级：

```text
准确性
> 语言自然度
> 术语一致性
```

具体规则依 `REVIEW_STYLE.md`。

#### rv 注释

Reviewer 每一处实际修改都必须在对应 block-id 后增加：

```html
<!-- block-id: b000012 -->
<!-- rv: terminology | положительное знание 是既有术语，应作「实证知识」 -->
```

类型：

| 类型          | 含义                               |
| ------------- | ---------------------------------- |
| `error`       | 理解错误、漏译、增译、事实性错误等 |
| `terminology` | 术语一致性                         |
| `preference`  | 语言表达或风格偏好                 |

`rv:` 是 Owner 审核 Reviewer 实际修改的证据，不得遗漏。

#### 提交

```text
blind-review(<group>-<batch>): ...
```

#### 完成

只有提交完成后，才能进入第 4 步并读取 handoff。

---

### 第 4 步 — Reviewer 明审

#### 读取 handoff

从 `main` 的 handoff commit 读取：

```text
<batch_id>-handoff.md
```

只读取文件内容。

不得：

- merge handoff commit；
- cherry-pick handoff commit。

#### 范围

明审只处理：

- handoff 明确提出的问题；
- 对应位置的必要上下文；
- handoff 引出的 glossary 问题；
- 与这些问题直接相关的必要检查。

**明审不是第二次 Full Review。**

#### 当前批次译文问题

明审阶段：

- 不直接修改译文；
- 不新增 `rv:`；
- 新发现的问题写入 reports，交 Owner。

#### glossary

Reviewer 可以新增或修改 `provisional` 条目；既有 `needs_review` 条目只读使用。对已有 `approved` 译法的实质变更写入 reports 交 Owner，裁决前保留现行权威。

所有 glossary 变更都必须写入 reports。

Reviewer 的修改在 Owner 裁决前不是最终权威。

#### 已完成批次问题

若发现其他已经 `translated` 的批次存在具体译文或体例问题：

- 不修改该批次；
- 登记到 `review-notes.json`。

glossary 自身问题直接处理 glossary，不进入 `review-notes.json`。

#### reports

建立：

```text
<batch_id>-reports.md
```

固定包含三部分。

##### A. 术语变更清单

记录本批次实际发生的：

- 新增 glossary 条目；
- 修改 glossary 条目；
- 建议的状态变化。

无则写「无」。

##### B. 译文修改建议

只记录明审阶段新发现、尚未进入译文的问题。

每条至少写：

- block-id；
- 原文片段；
- 当前译文；
- 建议改法；
- 理由；
- `error` / `terminology` / `preference`。

盲审已经修改的内容不重复记录。

无则写「无」。

##### C. 待裁决条目

只记录 Reviewer 无法可靠决定、必须由 Owner 判断的问题。

每条至少写：

- block-id；
- 原文片段；
- 当前译文；
- 可选方案；
- 各方案理由。

无则写「无」。

#### 提交

```text
open-review(<group>-<batch>): ...
```

#### 完成

Reviewer 停止，等待 Owner。

---

### 第 5 步 — Owner 裁决

Owner 只处理当前批次。

#### 审核盲审

检查：

- Reviewer 实际译文修改；
- 对应 `rv:`。

对每项决定：

- 接受；
- 撤回；
- 调整。

#### 审核明审

检查 reports：

- A. 术语变更；
- B. 译文修改建议；
- C. 待裁决条目。

#### 落实

Owner 根据裁决直接：

- 修改当前批次译文；
- 修改 glossary；
- 撤回或调整 Reviewer 修改；
- 决定 glossary 条目状态。

不得因此修改其他已经 `translated` 的批次。

这些问题继续保留在 `review-notes.json`，等待统稿。

#### 更新 reports

在 reports 中记录：

- 对盲审修改的总体决定；
- 对明审建议的决定；
- 对待裁决条目的决定；
- 对 glossary 变更的决定；
- Owner 实际采取的必要修改。

reports 只保存裁决结果，不重复能够直接从 Git diff 得出的机械修改历史。

#### 完成

Owner 停止。

本步骤不单独提交；Owner 的最终修改由下一步 `finalize` commit 固化。

---

### 第 6 步 — Reviewer Finalization

Reviewer 在 Owner 裁决后重新接手审校分支。

先行翻译未核验底本的任务，须确认 Owner 已明确授权当前 Finalization 阶段；未获授权时停止，不宣告流程完成。

#### 操作

1. 确认 Owner 的修改已经落入当前分支。
2. 确认 reports 已记录必要裁决。
3. 删除当前批次全部 `rv:`。
4. 确认无 `rv:` 残留。

本阶段：

- 不重新进行 Full Review；
- 不自行新增翻译修改；
- 不扩大检查范围。

若 Owner 已明确裁决但尚未实际落实，只落实该裁决。

#### finalize 提交

```text
finalize(<group>-<batch>): ...
```

#### merge

将审校分支合并回 `main`，生成正常 merge commit。

merge commit：

- 只汇合 handoff 历史和 Reviewer 分支历史；
- 不额外修改文件；
- 不附带 translation、review 或 cleanup。

```text
merge(<group>-<batch>): ...
```

取得 merge commit hash。

#### 完成

Reviewer 停止。

---

### 第 7 步 — Operator Closeout

Operator 回到 `main`。

#### 同步上下文

取得：

- `operator_commit`
- 当前批次 merge commit hash

先查看：

```text
git diff <operator_commit>..<merge_commit>
```

确认最终发生的译文和 glossary 变化。

再阅读：

```text
<batch_id>-reports.md
```

理解 Owner 裁决。

本步骤不是新一轮翻译或审校。

#### 机械复核

检查：

- 当前批次底本与译文 block-id 序列一致；
- block-id 无重复、缺失或错误顺序；
- 译文中无 `rv:`。

只允许修复明确的流程性错误，不重新展开译文审校。

#### comments.md

只有存在**后续未翻译批次仍需知道的信息**时才更新 `comments.md`。

可以记录：

- 后续必须继续遵守的特殊翻译约定；
- glossary 无法完整承载的作品级上下文；
- 后续仍会遇到的特殊结构处理。

不要记录：

- 完整审校历史；
- 已经解决的问题；
- glossary 已保存的信息；
- Git diff 已保存的历史；
- 单句修改理由；
- 只对已完成批次有意义的信息。

#### closeout

将 merge commit hash 写入：

```text
status.json.reviewer_commit
```

然后：

```text
status:
in_progress → translated
```

提交：

```text
closeout(<group>-<batch>): ...
```

#### 完成

当前批次完成。

若仍有 `untranslated` 批次，下一次流程重新从第 0 步开始。

若全书所有批次均为 `translated`，翻译流程结束。

---

## 5. 问题分流

遇到问题时按对象处理：

| 问题                                            | 去向                 |
| ----------------------------------------------- | -------------------- |
| 当前批次译文问题                                | 当前批次流程内处理   |
| 已完成批次的具体译文或体例问题                  | `review-notes.json`  |
| glossary 自身的术语权威、状态、forms 或结构问题 | `glossary/`          |
| 原文、OCR 或底本问题                            | `source-issues.json` |
| 跨批次统一、全书术语反向检查                    | `CONSOLIDATION.md`   |

不得把同一问题重复登记到多个系统。

---

## 6. 边界

正常批次流程不执行：

- 已完成批次回改；
- 全书一致性修改；
- glossary 全书反向扫描；
- regression review；
- 第二轮 Full Review；
- verification of verification；
- 全书统稿。

以上属于后续统稿阶段，依 `CONSOLIDATION.md`。

---

## 7. 批次完成条件

一个批次只有同时满足以下条件才算完成：

- 当前批次全部 unit 已翻译；
- 底本与译文 block-id 对应正确；
- `operator_commit` 已绑定 `translation` commit；
- blind-review 已完成；
- open-review 已完成；
- Owner 已完成裁决；
- glossary 变更已得到 Owner 处理；
- `rv:` 已全部清除；
- Reviewer 分支已合并回 `main`；
- `reviewer_commit` 已绑定 merge commit；
- 必要的后续上下文已经进入 `comments.md`；
- `status` 为 `translated`。

全书全部批次均满足以上条件后，本流程结束，并依 `CONSOLIDATION.md` 进入统稿。
