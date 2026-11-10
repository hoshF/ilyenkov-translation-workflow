---
title: "翻译流程规范"
type: "agent-guide"
---

# 翻译流程规范

## 职责与边界

本流程执行 [`TRANSLATION_PREPROCESSING.md`](../digitization/TRANSLATION_PREPROCESSING.md) 已建立的书籍批次，以既有 `index.json` 和 `status.json` 为任务结构。单元、分组、批次及这两个文件的建立与重构属于预处理。单篇文章执行 [`ARTICLE_TRANSLATION_WORKFLOW.md`](ARTICLE_TRANSLATION_WORKFLOW.md)。

Operator 和 Reviewer 按本流程默认执行各自步骤的分支、提交与合并，commit 绑定写入实际产生的提交。这些 Git 操作在任务指定的翻译项目仓库中进行。

Owner 授权时，可以先翻译尚未完成数字化核验的底本：将数字化原文的实际状态、未决核验风险和授权范围记入 `source-issues.json`，handoff 引用对应 issue。翻译完成只表示译文完成，原文验收和公开许可另行办理。这类批次进入 Finalization 前，取得 Owner 对该阶段的授权。

已有译文的指定范围校阅依 [`REVIEW_STYLE.md`](REVIEW_STYLE.md) 的「已有译文校阅入口」执行。

Operator、Reviewer 开始各自工作前完整阅读本文档。

本流程以**批次（batch）**为执行单位，处理尚未完成的批次。全书所有批次均达到 `translated` 后，本流程结束，全书统稿依 `CONSOLIDATION.md`。

---

## 0. 核心规则

### 执行单位

- **分组（group）**：按内容性质、体例和翻译上下文组织的一组单元，定义在 `index.json`。
- **批次（batch）**：翻译流程的实际执行单位，定义在 `status.json`。
- **单元（unit）**：按作品目录划分的章节或内容单元。

翻译、审校、Owner 裁决和提交均以批次为单位。

### 稳定数据

`index.json` 定义稳定的翻译任务结构，翻译和审校期间保持不变。

`status.json` 只保存：

- 批次状态；
- `operator_commit`；
- `reviewer_commit`。

### 已完成批次

已经 `translated` 的批次译文保持定稿状态。后续发现的问题按「问题分流」处理。

### 角色停止

每个角色执行自己当前步骤，完成规定的提交或裁决后停止，由下一角色接手。

---

## 1. 角色

| 角色     | 职责                                                       | 承担者 |
| -------- | ---------------------------------------------------------- | ------ |
| Operator | 翻译、术语符合性自查、handoff、closeout、后续上下文同步    | Agent  |
| Reviewer | 盲审、明审、reports、术语建议、Finalization                | Agent  |
| Owner    | 审核 Reviewer 修改与建议、裁决疑难、决定最终译文与术语权威 | 人     |

Owner 的最终裁决高于 Operator 和 Reviewer 的建议。

Reviewer 对 glossary 的新增或修改，经 Owner 裁决后成为权威；具体权限与状态依 `glossary/GLOSSARY_RULES.md`。

Reviewer 由未参与当前批次 Operator 翻译的独立 Agent 或会话承担。

---

## 2. 工件

### 全书共用

| 文件                 | 用途                                               |
| -------------------- | -------------------------------------------------- |
| `index.json`         | 分组和 unit 结构                                   |
| `status.json`        | 批次、状态与 commit 绑定                           |
| `comments.md`        | 尚未完成的批次仍需知道的作品级上下文               |
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

保存当前批次翻译后 Reviewer 仍需知道的信息。

`reports`：

> Reviewer → Owner → Operator

保存明审意见、术语变更及 Owner 最终裁决。

流程结束后，handoff 与 reports 保留当时的交接和裁决。后续必要结论按问题分流追加到对应工件，已经闭环的裁决和 review-note 保持原样；普通修改历史以 Git 为准。

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

每个批次从 `main` 创建独立的 Operator 批次分支。分支名称能识别作品与批次；Owner 指定名称时依其指定。

提交顺序：

```text
translation
→ handoff
→ blind-review
→ open-review
→ finalize
→ merge（审校分支合回批次分支）
→ merge（批次分支合回 main）
→ closeout
```

其中：

```text
批次分支：translation → handoff → 接收审校合并
审校分支：从 translation 创建 → blind-review → open-review → finalize
main：接收批次合并 → closeout
```

Operator 在批次分支提交 translation 和 handoff。Reviewer 从实际交付的 `translation` commit 创建审校分支，finalize 后合回批次分支。Operator 在 closeout 时将批次分支合入 `main`。

两次合并都使用保留 merge commit 的普通合并，merge 只汇合历史。

### 并行批次与共享文件

- 合并 `status.json` 时，整合相关批次的状态和绑定，保留其他批次记录。
- 合并 `source-issues.json`、`review-notes.json` 和 glossary 时，逐条保留已登记内容及 Owner 裁决；术语权威以 Owner 裁决为准。
- 新登记条目的编号接在 `main` 与所有在途批次分支已用编号之后；合并后按既有编号排列。
- 编号仍然冲突时，调整尚未交接的新增条目并同步其引用；涉及已交接、已裁决或已闭环的条目，交 Owner 决定。
- 同一问题重复登记时，合并尚未闭环的重复记录及必要位置，保留已裁决结论；已 `checked` 的 review-note 保持原样，必要的后续问题另建条目。
- 合并冲突整合两侧已有改动；译法、身份或裁决互相冲突时，列出具体差异交 Owner。
- 新的作品约定通过 `comments.md` 传递。已开始的其他批次在明审和 closeout 时核对适用的新约定，只处理由此产生的具体差异；已完成批次的具体问题登记 review-note。

### commit 命名

格式：

```text
<type>(<group>-<batch>): ...
```

例如：

```text
translation(14-b01): ...
blind-review(14-b01): ...
merge(14-b01): merge review branch
merge(14-b01): merge batch branch
closeout(14-b01): ...
```

`merge review branch`：审校分支合回批次分支；`merge batch branch`：批次分支合入 `main`。

### 补正提交

已提交的内容需要补正时，追加提交，保留已有提交：

- 补正仍属当前阶段、下一阶段尚未开始时，追加同类型提交；该阶段以最后一个同类型提交为实际交付版本。
- 审校分支创建后，Operator 对当前批次译文的补正写成追加的 handoff 提交说明。open-review 提交前追加的，由 Reviewer 在明审中按 handoff 问题处理；open-review 提交后追加的，报告 Owner，由 Owner 决定交 Reviewer 追加 open-review 提交补充复核后再裁决，或在 closeout 后登记 review-note。
- 盲审以一个 `blind-review` 提交为准；此后 Reviewer 的修改依明审和 finalize 的权限进行。

### commit 绑定

`operator_commit`：

> 当前批次实际交付审校的 `translation` commit，即审校分支的起点。

在 `handoff` commit 中写入 `status.json`。

`reviewer_commit`：

> Reviewer 审校分支完成 Finalization 后，合回当前 Operator 批次分支所产生的 `merge review branch` commit。

批次分支合入 `main` 后，在 `closeout` commit 中写入 `status.json`。

绑定保存相应步骤实际产生的提交，统稿和后续修改不改变绑定。事实性回填以明确的提交证据为依据。

### 状态

```text
untranslated
      ↓ translation
in_progress
      ↓ closeout
translated
```

状态只由以下两个步骤改变：

- `translation`：`untranslated → in_progress`
- `closeout`：`in_progress → translated`

`translated` 表示当前批次已按本流程完成；原文核验、全书统稿、成书排版和公开许可各有其流程。后续发现具体问题时按问题分流处理，批次状态保持 `translated`。

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

按 Owner 指定范围确定批次；未指定时，从当前 `main` 的 `status.json` 选择下一个 `untranslated` 批次，批次状态以 `main` 为准。确认：

- group 正确；
- batch 正确；
- unit 与 `index.json` 一致。

新批次为 `untranslated`，从 `main` 创建其 Operator 分支。批次已有工作时，确认既有分支、工件和实际阶段，从未完成的步骤继续。

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
- 文字或著录差错有已核验底本、同书对应条目或可定位的原始文献支持时，按可靠恢复处理，记录底本位置、原值、恢复值与依据；
- 涉及人物身份、版本选择、索引指向或多个可能恢复值时，保留可靠可译的内容，校正建议交 Owner，经批准后替换；
- 无法可靠恢复的内容保留原状，登记后在 handoff 交接；
- 文本完整但事实错误时照译原文，校正建议交 Owner；
- 作者观点、用词习惯或与现代学科规范的差异按原文翻译，不属于原文存疑。

疑点导致当前内容无法可靠翻译时，先交 Owner 决定。

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

记录 Reviewer 后续需要知道的信息：

- Operator 拿不准的词义、句义或翻译选择；
- 当前选择的必要理由；
- glossary 新增或修改建议；
- 已登记的 source issue id。

例如：

```text
原文存疑：S-NNN, S-NNN
```

handoff 只写上列信息。

#### 提交

`operator_commit` 与 handoff 一起提交：

```text
handoff(<group>-<batch>): ...
```

#### 完成

Operator 停止。

---

### 第 3 步 — Reviewer 盲审

#### 起点

从当前批次实际交付的 `translation` commit 创建独立审校分支。

#### 隔离

**当前批次的 `<batch_id>-handoff.md` 在盲审提交后读取。**

#### 读取

盲审使用：

- 当前批次原文；
- `operator_commit` 中的译文；
- `glossary/`；
- `main` 上已有的 `comments.md` 及作品适用的补充规则；
- `REVIEW_STYLE.md`；
- `PUNCTUATION.md`；
- 已经 `translated` 批次的译文，用于核对一致性。

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

Reviewer 每一处实际修改都在对应 block-id 后增加：

```html
<!-- block-id: b000012 -->
<!-- rv: terminology | 原词 是既有术语，应作「既定译法」 -->
```

类型：

| 类型          | 含义                               |
| ------------- | ---------------------------------- |
| `error`       | 理解错误、漏译、增译、事实性错误等 |
| `terminology` | 术语一致性                         |
| `preference`  | 语言表达或风格偏好                 |

`rv:` 是 Owner 审核 Reviewer 实际修改的依据，每处修改各有一条。

#### 提交

```text
blind-review(<group>-<batch>): ...
```

#### 完成

提交完成后进入第 4 步并读取 handoff。

---

### 第 4 步 — Reviewer 明审

#### 读取 handoff

从当前 Operator 批次分支最新的 handoff commit 读取：

```text
<batch_id>-handoff.md
```

只读取文件内容；审校分支保持不含 handoff commit。

#### 范围

明审处理：

- handoff 明确提出的问题；
- 对应位置的必要上下文；
- handoff 引出的 glossary 问题；
- 与这些问题直接相关的必要检查。

**明审是对 handoff 的定向核对。**核对中顺带发现的其他问题，按本步骤分流写入 reports。

#### 当前批次译文问题

明审阶段的发现写入 reports，交 Owner；译文保持盲审提交时的状态。

#### 原文疑点

盲审和明审中发现的原文疑点，在本步骤查重后登记到 `source-issues.json`，reports 引用对应编号。底本无法可靠翻译，或需要校正身份、版本、回指时，按「原文存疑」交 Owner。

#### 新约定与在途批次

核对已合入 `main`、适用于当前内容的新作品约定及术语裁决，处理由此产生的具体差异。

同组在途批次与当前批次不一致时，写入 C，注明对方批次与位置，由 Owner 一并裁决。

#### glossary

Reviewer 可以新增或修改 `provisional` 条目；既有 `needs_review` 条目只读使用。对已有 `approved` 译法的实质变更写入 reports 交 Owner，裁决前沿用现行权威。

全部 glossary 变更写入 reports，经 Owner 裁决后成为权威。

术语建议的适用范围及多个 `approved` 条目的冲突，依 `GLOSSARY_RULES.md`「裁决范围」与「多个 approved 条目的适用判断」处理。

#### 已完成批次问题

其他已经 `translated` 的批次存在具体译文或体例问题时，登记到 `review-notes.json`。

glossary 自身问题在 glossary 中处理。

#### reports

建立：

```text
<batch_id>-reports.md
```

先逐条写 handoff 复核结论，再写以下三部分。

##### A. 术语变更清单

记录本批次实际发生的：

- 新增 glossary 条目；
- 修改 glossary 条目；
- 建议的状态变化。

无则写「无」。

##### B. 译文修改建议

记录明审阶段新发现、尚未进入译文的问题。

每条至少写：

- block-id；
- 原文片段；
- 当前译文；
- 建议改法；
- 理由；
- `error` / `terminology` / `preference`。

盲审修改以 `rv:` 为准。

无则写「无」。

##### C. 待裁决条目

记录需要 Owner 判断的问题。

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

Owner 处理当前批次。

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

Owner 根据裁决直接修改，或给出书面裁决，由 Reviewer 在 finalize 中落实：

- 修改当前批次译文；
- 修改 glossary；
- 撤回或调整 Reviewer 修改；
- 决定 glossary 条目状态。

涉及其他已经 `translated` 批次的问题保留在 `review-notes.json`，等待统稿。

术语决定写明适用范围，依 `GLOSSARY_RULES.md`「裁决范围」。原文校正决定写入对应 source issue 的 `handling`，保留底本原值和依据。

#### 更新 reports

在 reports 末尾增加 `## D. Owner 裁决`，依次分为：

- `### 盲审修改`：对盲审修改的决定；
- `### handoff`：对 handoff 复核结论的决定；
- `### 明审建议`：对 B 的决定；
- `### 待裁决条目`：对 C 的决定；
- `### glossary`：对 glossary 变更的决定。

Owner 实际采取的必要修改记入相应小节。reports 保存裁决结果，机械修改历史以 Git diff 为准。Owner 给出书面裁决时，D 节由 Reviewer 在 finalize 中照录。

#### 完成

Owner 停止。

本步骤的修改由下一步 `finalize` commit 固化。

---

### 第 6 步 — Reviewer Finalization

Reviewer 在 Owner 裁决后重新接手审校分支，落实裁决并清理审校标记。

#### 操作

1. 确认 Owner 的修改已经落入当前分支；已明确裁决但尚未落实的，落实该裁决。
2. 确认 reports 已有 D 节，批次分支上 open-review 提交后追加的 handoff 已有 Owner 决定的去向。
3. 写定当前批次全部 source issue 的 `handling`：有裁决的写裁决结论，审校确认的写确认结论。
4. 删除当前批次全部 `rv:`。
5. 确认无 `rv:` 残留。

本阶段的修改以 Owner 裁决为限。

#### finalize 提交

```text
finalize(<group>-<batch>): ...
```

#### merge

将审校分支合并回当前 Operator 批次分支，生成普通 merge commit。merge commit 只汇合 handoff 历史和审校分支历史。

```text
merge(<group>-<batch>): merge review branch
```

取得 merge commit hash。

#### 完成

Reviewer 停止。

---

### 第 7 步 — Operator Closeout

Closeout 核对审校结果，合入 `main` 并完成批次。

#### 同步上下文

取得：

- `operator_commit`
- 审校分支合回批次分支的 merge commit hash

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

#### 合入 main 前

在批次分支确认：

- 审校分支已合回批次分支；
- reports 的 D 节所列裁决已全部落实；
- 批次分支上的全部 handoff 提交均已在 reports 中复核，或已有 Owner 决定的去向；
- 当前批次底本与译文 block-id 序列一致，无重复、缺失或错误顺序；
- 译文中无 `rv:`；
- 脚注引用、定义和顺序与底本对应，图片路径可解析；
- 相关 JSON 有效。

全部通过后合入 `main`；未通过的项目报告并交相应角色处理。本步骤只修复明确的流程性错误。

#### 合入 main

将批次分支正常合入 `main`：

```text
merge(<group>-<batch>): merge batch branch
```

共享文件依「并行批次与共享文件」整合。完成合并后留在 `main` 执行本步骤其余部分。

#### 合入后核对

在 `main` 确认：

- 当前批次译文与批次分支一致，批次分支的必要提交已进入 `main`；
- 共享文件中当前批次的记录完整，其他批次的状态、绑定、source issue、review-note 和 glossary 记录完整保留；
- 合并后的 JSON 有效，编号唯一；
- 已批准的 glossary 修改与作品约定已落实。

存在新的语义差异或尚未落实的裁决时，报告并交相应角色处理。

交接分别说明机械检查结果与本阶段实际核对的裁决落实范围，并写明未执行或未通过的检查。

#### comments.md

存在**尚未完成流程的批次（含 `untranslated` 和 `in_progress`）仍需知道的信息**时，更新 `comments.md`。

记录：

- 尚未完成的批次必须遵守的特殊翻译约定；已完成批次的同类问题另登记 review-note；
- glossary 无法完整承载的作品级上下文；
- 后续仍会遇到的特殊结构处理。

`comments.md` 只写上列信息。

#### closeout

将审校分支合回批次分支的 merge commit hash 写入：

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

#### 删除批次与审校分支

closeout 提交完成后，留在 `main`，确认当前批次 Operator 批次分支和 Reviewer 审校分支的全部提交均已合入 `main`，以普通删除方式删除这两个本地分支。

Owner 指定整组 closeout 时，对当前组内各批次分别完成 closeout，并删除对应的本地 Operator 批次分支和 Reviewer 审校分支；不删除其他组的分支。

仍有未合并提交的分支保留并报告 Owner，不强制删除。

#### 完成

当前批次完成。

仍有 `untranslated` 批次时，下一次流程从第 0 步开始。

全书所有批次均为 `translated` 时，翻译流程结束。

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

每个问题登记在一个去向。

---

## 6. 统稿阶段的工作

以下工作在全书统稿阶段依 `CONSOLIDATION.md` 进行：

- 已完成批次回改；
- 全书一致性修改；
- glossary 全书反向扫描；
- 全书统稿。

统稿以清点确认的一致性和遗留问题为修改范围；落实修改后的针对性复扫和最终复核是统稿的正常步骤。逐句全文复审，包括第二轮 Full Review、全文回归审校（regression review）和复核的复核，由 Owner 另行指定。

---

## 7. 批次完成条件

一个批次同时满足以下条件时完成：

- 当前批次全部 unit 已翻译；
- 底本与译文 block-id 对应正确；
- `operator_commit` 已绑定 `translation` commit；
- blind-review 已完成；
- open-review 已完成；
- Owner 已完成裁决；
- glossary 变更已得到 Owner 处理；
- `rv:` 已全部清除；
- 审校分支已合并回 Operator 批次分支，批次分支已合入 `main`；
- `reviewer_commit` 已绑定审校分支合回批次分支的 merge commit；
- 已合并的当前批次本地 Operator 批次分支和 Reviewer 审校分支均已删除；
- 必要的后续上下文已经进入 `comments.md`；
- `status` 为 `translated`。

全书全部批次均满足以上条件后，本流程结束，依 `CONSOLIDATION.md` 进入统稿。
