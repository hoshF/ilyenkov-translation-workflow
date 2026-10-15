---
title: "校阅记录规范"
type: "agent-guide"
---

# 校阅记录规范

`review-notes.json` 用于记录**已经完成批次中发现、需要在全书统稿阶段处理的具体译文层问题**。

Owner 指定已有书籍译文直接校阅时，也沿用本文件记录指定范围内的具体译文层问题，不为使用校阅记录而补造批次或流程历史。

文件位置：

```text
translation/<人>/<作品>/review-notes.json
```

具体统稿流程依 [`CONSOLIDATION.md`](CONSOLIDATION.md)。

---

## 0. 边界

可以进入 `review-notes.json` 的问题必须能够定位到具体译文文件。

包括：

- 具体译文问题；
- 跨批次译法不一致；
- 体例不一致；
- 记号问题；
- 注释问题；
- 与译文成书有关的具体排版标记问题。

下列问题不进入本文件：

```text
glossary 自身的权威、forms 或结构问题
→ glossary/

原文、OCR 或底本问题
→ source-issues.json

当前未完成批次的问题
→ 当前批次翻译 / 审校流程
```

不得把 `review-notes.json` 当作一般项目待办清单。

---

## 1. 结构

```json
{
  "source": "",
  "categories": {
    "translation": [],
    "notation": [],
    "annotation": [],
    "typography": []
  }
}
```

### source

`source` 表示：

> 全书翻译完成、进入统稿前的基线 commit。

全书尚未完成翻译时留空。

进入统稿后依 `CONSOLIDATION.md` 填写。

保存 8 位 commit hash。

---

## 2. 分类

| 分类          | 范围                             | id 前缀 |
| ------------- | -------------------------------- | ------- |
| `translation` | 具体翻译或译法一致性问题         | `tr`    |
| `notation`    | 记号、编号和符号问题             | `no`    |
| `annotation`  | 注释内容、归属或形式问题         | `an`    |
| `typography`  | 与译文成书有关的具体排版标记问题 | `ty`    |

分类按问题的主要性质判断。

---

## 3. 条目

```json
{
  "id": "tr001",
  "file": "00-front/u003-predislovie.md",
  "block_id": "b000002",
  "quote": "……",
  "comment": "……",
  "solution": "",
  "checked": ""
}
```

| 字段       | 内容                                   |
| ---------- | -------------------------------------- |
| `id`       | 分类前缀 + 三位序号                    |
| `file`     | 译文文件路径，相对于译文作品目录       |
| `block_id` | 该单元中问题的首个 occurrence 所在 block |
| `quote`    | 能够识别问题的最短必要译文片段         |
| `comment`  | 问题是什么、涉及哪些位置及为什么需要处理 |
| `solution` | 最终处理方案                           |
| `checked`  | 落实或确认该方案的 commit hash，取 8 位 |

### id

每个分类独立连续编号：

```text
tr001
tr002
...
no001
no002
...
```

已经使用的 id 不重新分配。

### comment

`comment` 只说明问题本身。

同一单元有多个 occurrence 时：

- `block_id` 填首处；
- 其余 block-id 写入 `comment`。

不得在 `comment` 中保存无必要的审校历史。

### solution

如果登记时已有明确方案，可以直接填写。

需要在统稿阶段裁决时留空。

最终 `solution` 应保存：

> 最终应该怎样处理。

不保存完整裁决过程。

### checked

`checked` 保存：

> 实际落实该 solution，或确认现译无需修改的最终状态 commit。

不是问题发现时的 commit。

---

## 4. 登记粒度

同一问题跨多个单元时：

> 每个单元一条。

同一单元内存在多个同类 occurrence 时：

> 只登记一条。

例如：

```text
u012：
b000014
b000021
b000038

→ 一条 review-note
→ block_id = b000014
→ comment 中列出 b000021、b000038
```

不得因为同一问题出现多次就逐 occurrence 建立大量重复条目。

---

## 5. 生命周期

### 翻译阶段

发现已经 `translated` 的批次存在问题时：

1. 新增 review-note；
2. 填写实际问题；
3. `solution` 有明确结论时可填写，否则留空；
4. `checked` 留空；
5. 不直接修改已完成批次译文。

### 统稿阶段

依 [`CONSOLIDATION.md`](CONSOLIDATION.md)：

```text
清点
→ 裁决
→ 落实
→ checked
```

实际范围大于原登记范围时，以实际文本为准。

---

## 6. 已完成条目

`checked` 非空表示该条目已经闭环。

只有实际落实 `solution` 或完成「现译无需修改」的确认，且有对应提交时才填写 `checked`；已提出方案、文件存在或其他阶段完成都不能代替该条件。未产生提交时保留为空，不填虚构 hash。

已 `checked` 条目不得重新修改其：

- `file`
- `block_id`
- `quote`
- `comment`
- `solution`
- `checked`

以后发现新的问题时，新建条目。

不得为了重写历史而修改已经闭环的旧记录。

`checked` 只表示该条目在绑定提交时已经闭环，不表示当前全书没有新问题。后续必要处理使用新条目，保留既有条目及其提交绑定。

---

## 7. 完成条件

全书统稿完成时：

- `source` 非空；
- 所有条目均有明确 `solution`；
- 所有条目的 `checked` 均非空；
- 所有 `file` 和 `block_id` 均可解析。

具体停止条件依 [`CONSOLIDATION.md`](CONSOLIDATION.md)。
