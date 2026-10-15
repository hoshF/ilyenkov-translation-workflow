---
title: "翻译预处理规范"
type: "agent-guide"
---

# 翻译预处理规范

## 适用判定

以下作品进入本流程：已完成 [`BOOK_PREPROCESSING.md`](BOOK_PREPROCESSING.md) 的书籍。DJVU 文字层流程内已按该规范完成目录、单元、语义分块和 block-id 的，视为已完成相应结构预处理，不重复拆分或编号。

默认要求数字化正文达到 `human_verified`。Owner 明确授权未完成全文数字化核验的底本先翻译指定范围时，可以建立该任务所需的翻译结构；保留真实数字化状态，按翻译流程记录未核验风险和授权范围。结构建立不代替底本验收，Finalization 须有 Owner 对该阶段的明确授权，不据此推导最终质量验收或发布许可。

单篇文章不进入本流程，直接依 [`ARTICLE_TRANSLATION_WORKFLOW.md`](../translation/ARTICLE_TRANSLATION_WORKFLOW.md) 翻译。

## 输入与产出

翻译分组、批次、`index.json` 和 `status.json` 在本阶段建立。底本侧文件在本阶段保持不变，翻译与
审校在翻译流程中执行。

本阶段完成后，依 [`TRANSLATION_WORKFLOW.md`](../translation/TRANSLATION_WORKFLOW.md) 执行既有书籍批次。

产出：

```text
<译文作品目录>/
  index.json
  status.json
```

## 基本单位

**分组（group）**：将内容性质、体例或翻译要求相近，适合按同一上下文连续处理的单元归在一起。

**批次（batch）**：翻译流程的实际执行单位。一个分组可以包含一个或多个批次，一个批次不得跨分组。

---

## 第 1 步 — 建立 index.json

根据底本侧 `index.md` 和 `work.json` 建立 `index.json`，登记全书的翻译分组及其单元。

人工示例：

```json
{
  "title": "Наблюдение и сопоставление",
  "source_edition": "教学示例初稿（未作最终验收）",
  "groups": [
    {
      "id": "text",
      "label": "示例正文",
      "dir": "01-text",
      "units": [
        {
          "unit_id": "u001",
          "title": "Наблюдение",
          "part": "Наблюдение и сопоставление",
          "file": "01-text/u001-observation.md"
        },
        {
          "unit_id": "u002",
          "title": "Сопоставление",
          "part": "Наблюдение и сопоставление",
          "file": "01-text/u002-comparison.md"
        }
      ]
    }
  ]
}
```

### 字段

| 字段             | 内容                                       |
| ---------------- | ------------------------------------------ |
| `title`          | 书名，取自 `work.json`                     |
| `source_edition` | 底本版次，取自 `work.json`                 |
| `id`             | 分组稳定标识，使用小写连字符，不带顺序编号 |
| `label`          | 分组的简短中文说明                         |
| `dir`            | 译文侧分组目录，格式为 `NN-<id>`           |
| `unit_id`        | 单元编号，与底本侧一致                     |
| `title`          | 单元标题，取自 `index.md`                  |
| `part`           | 单元在原书目录中的所属部、节或同级结构     |
| `file`           | 译文文件路径，相对于译文作品目录           |

### 分组规则

1. 按内容性质、体例和翻译上下文划分分组，不要求与底本侧目录结构一致。
2. 同一作者、同一文献类型、同一编者材料或需要共享翻译上下文的单元，可归入同一分组。
3. 分组内部的单元顺序可以根据翻译需要调整，不要求与原书目录顺序完全一致。
4. 分组之间按其在原书中首次出现的顺序排列。
5. `dir` 的 `NN` 表示分组顺序，从 `01` 起连续编号。
6. 每个单元必须且只能属于一个分组。
7. `index.json` 必须覆盖 `index.md` 中的全部单元，不得遗漏或重复。
8. 译文侧分组目录与底本侧章节目录可以不同，数量也不要求一致。

完成后进入第 2 步。

---

## 第 2 步 — 建立 status.json

根据 `index.json` 建立 `status.json`，登记每个分组的翻译批次及其状态。

人工示例：

```json
{
  "groups": [
    {
      "group_id": "01-text",
      "batches": [
        {
          "batch_id": "b01",
          "units": ["u001"],
          "status": "untranslated",
          "operator_commit": null,
          "reviewer_commit": null
        },
        {
          "batch_id": "b02",
          "units": ["u002"],
          "status": "untranslated",
          "operator_commit": null,
          "reviewer_commit": null
        }
      ]
    }
  ]
}
```

### 字段

| 字段              | 内容                                          |
| ----------------- | --------------------------------------------- |
| `group_id`        | 分组目录名，与 `index.json` 的 `dir` 完全一致 |
| `batch_id`        | 批次标识，在每个分组内从 `b01` 起连续编号     |
| `units`           | 属于该批次的单元编号                          |
| `status`          | `untranslated` / `in_progress` / `translated` |
| `operator_commit` | 该批次完成翻译生产后的 translation commit     |
| `reviewer_commit` | 该批次完成审校并合并后的 merge commit         |

### 批次规则

1. 批次是 [`TRANSLATION_WORKFLOW.md`](../translation/TRANSLATION_WORKFLOW.md) 使用的执行单位。
2. 根据单元数量、篇幅和一次任务适合处理的工作量划分批次。
3. 一个分组可以只设一个批次，也可以拆成多个批次。
4. 只有一个单元的分组只建立一个批次。
5. 批次不得跨分组。
6. 批次内的单元按 `index.json` 中该分组的单元顺序排列。
7. 每个单元必须且只能属于一个批次。
8. 同一分组的全部批次合起来必须完整覆盖该分组全部单元，不得遗漏或重复。

本阶段只建立初始状态：

```text
status = untranslated
operator_commit = null
reviewer_commit = null
```

所有批次均以该状态开始。

本阶段结束后，这三个字段只由翻译流程按实际进度更新。

完成后停止本阶段。

---

## 输出约束

`index.json` 在本阶段完成后作为翻译任务结构的稳定索引；进入翻译流程后不得因普通翻译或审校操作修改。

下列文件由后续翻译流程按实际需要建立，本阶段不产出：

- `comments.md`
- `source-issues.json`
- `review-notes.json`

## 完成条件

以下条件必须全部满足：

- `index.json` 的 `title` 与 `source_edition` 和 `work.json` 一致；
- `index.json` 覆盖 `index.md` 中全部单元，每个单元恰好出现一次；
- 每个 `file` 路径符合预定译文目录结构；
- 分组顺序正确，`dir` 序号从 `01` 起连续；
- `status.json` 的分组与 `index.json` 的 `dir` 一一对应；
- 每个分组至少包含一个批次；
- 每个分组的全部批次完整覆盖该分组全部单元，每个单元恰好出现一次；
- 批次不跨分组，`batch_id` 在各分组内从 `b01` 起连续；
- 全部批次的 `status` 为 `untranslated`；
- 全部 `operator_commit` 与 `reviewer_commit` 为 `null`。
