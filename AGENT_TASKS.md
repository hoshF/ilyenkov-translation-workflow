---
title: "Agent 任务指令模板"
type: "agent-guide"
---

# Agent 任务指令模板

以下指令供 Owner 复制给 Claude Code、Codex 等本地 Agent。在用 [`scripts/new_project.py`](scripts/new_project.py) 建立的翻译项目根目录启动 Agent，路径按该项目的 `AGENTS.md`。使用时替换 `〈…〉`，删去不适用的选项。

- 一个会话执行一个角色的当前步骤，到停止条件即停止。
- Reviewer 使用新开的会话，该会话未参与本次 Operator 翻译。
- Owner 裁决由 Owner 本人完成；下文只给出交给 Reviewer 的书面裁决格式。
- 指令中的规定与 `workflow/` 规范不一致时，以规范为准，并向 Owner 报告。

## 1. 检查项目与所处阶段

```text
工作区：当前项目根目录。先读 AGENTS.md 和 workflow/AGENTS.md。
任务：只读检查作品 〈work-id〉 所处的阶段。不修改文件，不执行 Git 写操作。
handoff 文件只确认是否存在，不读取内容，使本会话以后仍可担任 Reviewer。
报告：原文与 work.json 的位置及 text_status；已有的翻译工件；书籍 status.json 中各批次的状态与在途分支；
下一步由哪个角色执行哪一步；开始前需要 Owner 决定或授权的事项。
停止：报告后停止。
```

## 2. 文章：Operator 翻译与交接

```text
工作区：当前项目根目录。角色：Operator。
依 workflow/translation/ARTICLE_TRANSLATION_WORKFLOW.md 第 1 步，读取其中列出的规范。
输入：原文 source/〈work-id〉.md；作品信息 translation/〈work-id〉/work.json；术语 glossary/。
范围：全文。
授权：〈底本已完成数字化核验 / Owner 授权先行翻译未核验底本，风险记入 handoff 的原文疑点〉。不提交。
产出：translation/〈work-id〉/〈work-id〉.md；translation/〈work-id〉/handoff.md 的「Operator 交接」。
停止：写完 handoff 后停止，不进入审校。
```

## 3. 文章：Reviewer 盲审与明审

```text
新会话。本会话未参与这篇文章的翻译。工作区：当前项目根目录。角色：Reviewer。
依 workflow/translation/ARTICLE_TRANSLATION_WORKFLOW.md 第 2、3 步。
盲审：只读第 2 步列出的材料，即规范、相关 glossary 条目、source/〈work-id〉.md 和当前译文。
全文盲审完成前不打开、不搜索 translation/〈work-id〉/handoff.md。
明审：盲审完成后读取 handoff，处理交接问题和盲审暂留问题，结果写入「Reviewer 处理」。
授权：可以按第 3 步维护 provisional 术语条目。不提交。
停止：明审完成后交 Owner，停止。
```

## 4. 文章：Reviewer Finalization

```text
工作区：当前项目根目录。角色：Reviewer。
依 workflow/translation/ARTICLE_TRANSLATION_WORKFLOW.md 第 5 步。
输入：Owner 已修改的译文；handoff 中的「Owner 裁决」。
授权：〈底本已核验 / Owner 授权本篇进入 Finalization〉。不提交。
停止：完成第 5 步检查并写入 Finalization 记录后停止；有未落实的裁决时报告 Owner。
```

## 5. 书籍：成书预处理与翻译预处理

```text
工作区：当前项目根目录。
任务：依 workflow/digitization/BOOK_PREPROCESSING.md 处理 source/〈work-id〉/。
输入：完整连续的原文 Markdown 〈文件〉、必要图片、source/〈work-id〉/work.json。
产出：work.json 补全、index.md、章节单元与 block-id。
停止：完成后报告单元划分与待 Owner 确认的问题，停止。不建立 index.json、status.json。不提交。
```

Owner 确认单元划分后，另起任务：

```text
工作区：当前项目根目录。
任务：依 workflow/digitization/TRANSLATION_PREPROCESSING.md 为 〈work-id〉 建立翻译分组与批次。
产出：translation/〈work-id〉/index.json、status.json，各批次为 untranslated，提交字段为 null。
停止：完成后报告分组与批次，停止。不开始翻译。不提交。
```

## 6. 书籍：Operator 翻译与交接

```text
工作区：当前项目根目录（Git 仓库，主分支 main）。角色：Operator。
依 workflow/translation/TRANSLATION_WORKFLOW.md 第 0—2 步，开始前完整阅读该文件。
作品：〈work-id〉。批次：〈group-batch / 未指定时按第 0 步从 main 的 status.json 选下一个 untranslated 批次〉。
授权：按流程建立批次分支，提交 translation 与 handoff。〈底本未核验时：Owner 授权先行翻译，风险记入 source-issues.json〉。
停止：handoff 提交后停止，报告批次分支名和 translation commit。
```

## 7. 书籍：Reviewer 盲审与明审

```text
新会话。本会话未参与当前批次的翻译。工作区：当前项目根目录。角色：Reviewer。
依 workflow/translation/TRANSLATION_WORKFLOW.md 第 3、4 步，开始前完整阅读该文件。
批次：〈group-batch〉；Operator 交付的 translation commit：〈hash〉。
盲审：从该 translation commit 建立审校分支，读取第 3 步列出的材料。
blind-review 提交前，不检出批次分支，不打开、不 git show、不 diff 当前批次的 handoff。
明审：blind-review 提交后，从批次分支最新的 handoff commit 读取 handoff 内容，按第 4 步写 reports；审校分支保持不含 handoff commit。
授权：按流程提交 blind-review 与 open-review。
停止：open-review 提交后停止，交 Owner 裁决。
```

## 8. 书籍：Owner 书面裁决

Owner 可以直接修改审校分支并在 reports 末尾写 D 节，也可以给出书面裁决，由 Reviewer 在 Finalization 中照录：

```text
〈group-batch〉 Owner 裁决
### 盲审修改：〈接受全部 / 撤回 rv 位置 …〉
### handoff：〈逐条决定〉
### 明审建议：〈B 各条决定〉
### 待裁决条目：〈C 各条决定，术语写明适用范围〉
### glossary：〈各条变更的批准、调整或撤回〉
〈先行翻译未核验底本时：授权 / 暂不授权 本批次进入 Finalization〉
```

## 9. 书籍：Reviewer Finalization

```text
工作区：当前项目根目录。角色：Reviewer。
依 workflow/translation/TRANSLATION_WORKFLOW.md 第 6 步。批次：〈group-batch〉；审校分支：〈分支名〉。
输入：Owner 在审校分支的修改与 reports 的 D 节，或下列书面裁决：〈粘贴〉。
授权：按流程提交 finalize，并将审校分支合回批次分支（merge review branch）。
停止：merge 完成后停止，报告 merge commit。
```

## 10. 书籍：Operator Closeout

```text
工作区：当前项目根目录。角色：Operator。
依 workflow/translation/TRANSLATION_WORKFLOW.md 第 7 步。批次：〈group-batch〉。
授权：按流程完成合入 main 前核对、merge batch branch、合入后核对、comments.md、closeout 提交，并删除已合并的本地批次分支和审校分支。
停止：closeout 完成后停止，分别报告机械检查结果、裁决落实的核对范围及未通过的项目。
```

全书各批次都完成后，统稿依 [`translation/CONSOLIDATION.md`](translation/CONSOLIDATION.md)，由 Owner 另行交办。
