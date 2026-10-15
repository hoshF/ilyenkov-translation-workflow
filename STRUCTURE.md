---
title: "项目结构与规范"
type: "agent-guide"
---

# 项目结构与规范

## 工作区与路径

任务交办明确原文作品目录、译文作品目录、术语目录和成书工程目录。使用者可采用自己的上层目录。

文件内的路径必须说明相对基准。翻译 index.json 的 file 相对译文作品目录；原文 index.md 的链接相对其所在目录。

不要求建立人物总录、中央著述总录、网站清单或统一来源库。已有登记可以继续使用；底本、作品及输出的事实必须一致，同一事实不在多份登记中独立裁决。

## 文本层

| 层 | 内容 | 形态 |
| --- | --- | --- |
| 原始来源 | 实际采用的电子文本、扫描或版面文件 | HTML、EPUB、FB2、TXT、PDF、DJVU 等 |
| 规范化原文 | 保留结构和必要图片的原文 | Markdown |
| 译文 | 与原文对应的翻译及其工作工件 | Markdown、JSON |
| 成书 | 手工装配的作品工程及派生输出 | TeX、PDF |

原始来源的位置由任务指定。原件、字体和内部记录不因进入工作流而获得公开或 Git 收录许可。

## 作品与底本

书籍以稳定的 work_id 识别作品，以实际采用的版本及来源识别底本。work.json 按对应数字化路线保存题名、年份、版次、来源和真实 text_status。

有实际底本文件时记录文件名；对应路线要求 SHA 时，保留 source_scan.filename 与 source_scan.sha256，并完成核验。不把核验跳过报告为通过。

ISBN、来源登记 ID 等按实际情况填写。没有相应信息或登记体系时，不虚构值，也不为填字段另建登记表。

work.json 保存作品与底本事实。翻译 index.json 的 title、source_edition 从作品信息取得并保持一致，不作为第二处独立权威。

## 书籍原文

```text
<原文作品目录>/
  work.json
  index.md
  assets/                  # 有图片时
  <NN-slug>/
    uNNN-slug.md
```

index.md 覆盖作品全部单元，顺序和层级按作品目录。章节文件无 front matter。

目录节点、单元、语义块及 block-id 的建立依 [BOOK_PREPROCESSING.md](digitization/BOOK_PREPROCESSING.md)。

## 原文与译文对应

作品、unit_id 和单元内 block-id 共同定位书籍文本。

unit 编号全书稳定；block-id 在各单元内编号，原文先赋号，译文照录。合并已固化块时保留链首号，不重新编号后续块。

原文目录按作品结构组织，译文目录按翻译分组组织，两者可以不同。不得仅凭相同相对路径判断原译对应。

## 书籍译文

```text
<译文作品目录>/
  index.json
  status.json
  <NN-group>/
    uNNN-slug.md
    bNN-handoff.md
    bNN-reports.md
```

| 工件 | 职责 |
| --- | --- |
| index.json | 稳定的分组、单元及预定译文路径 |
| status.json | 批次、实际进度及真实提交绑定 |
| 每批次 handoff | Operator 向 Reviewer 交接 |
| 每批次 reports | Reviewer 意见及 Owner 裁决 |
| comments.md | 后续未翻译批次需要的作品级上下文 |
| source-issues.json | 原文、OCR 和底本问题 |
| review-notes.json | 已完成批次中留待统稿处理的具体问题 |

单元恰属一个分组和一个批次；批次不跨组。字段、覆盖和初始状态依 [TRANSLATION_PREPROCESSING.md](digitization/TRANSLATION_PREPROCESSING.md)。

中间工件按实际步骤和需要建立，不预制假记录。完整流程、提交顺序及状态更新依 [TRANSLATION_WORKFLOW.md](translation/TRANSLATION_WORKFLOW.md)。

## 单篇文章

单篇原文和译文保持标题、自然段、引文、注释及保留内容的结构对应。

```text
<文章译文目录>/
  <作品>.md
  work.json
  handoff.md
```

handoff 是唯一翻译中间文件。work.json 保存作品与底本信息，不增加翻译状态或提交绑定。

文章不建立书籍的 index.json、status.json、reports、comments、source-issues 或 review-notes，不专门建立 unit 或 block-id。已有 block-id 按 [ARTICLE_TRANSLATION_WORKFLOW.md](translation/ARTICLE_TRANSLATION_WORKFLOW.md) 保留。

## front matter

单篇 Markdown 使用以下字段，按顺序：

```text
title / type / text_status / source_url
```

事实性字段按需补充：work_year、doi、published_in、translator。

不写：created、updated、conversion_date、language、collection、author、source_license、source_format、source_site、text_role、core_corpus_eligible、redistribution_approved、rights_review_status、schema_version、generated_at。

书籍章节不写 front matter，作品级信息放 work.json。

## 术语

术语目录由任务明确指定，流程中的 glossary/ 指该目录。

- glossary.json：专名和体制词，填写 type。
- terms.json：通用学科术语。
- <作者标识>.json：该作者的理论概念。

条目沿用 id、canonical、forms、zh_preferred、zh_alternatives、status、notes；专名和体制词另有 type。forms 与 zh_alternatives 为数组，其余上述字段为字符串。

状态、归属、权限和 notes 写法依 [GLOSSARY_RULES.md](glossary/GLOSSARY_RULES.md)。示例格式见 [最小示例](examples/minimal/README.md)，不将示例条目作为生产权威。

## 问题、历史与当前状态

source-issues.json 位于单一作品目录时不重复 work_id；多作品共用目录时逐条填写 work_id。条目按对应数字化或书籍流程保存定位、原文、问题和本次处理。

同一问题在其负责工件登记，其他交接引用，不重复维护。

handoff、reports 和已经闭环的 review-note 保留当时结论；后续变化按相应流程追加或新建问题，不覆盖旧裁决。Git 已保存的普通修改历史不重复抄写。

text_status 反映数字化核验程度；批次 status 反映翻译流程。统稿、排版、最终校阅和公开许可各依其规则判断，不合并为统一状态。

## 成书输入与输出

成书输入为确定的译文 Markdown、图片和作品结构。TeX 是可手工维护的派生工程，提供 main.tex、接收语义宏、章节装配、字体和资源。

转换、草稿、编译与最终校阅依 [TYPESETTING.md](book/TYPESETTING.md) 和 [工具说明](scripts/README.md)。使用独立临时目录保存测试与不完整草稿，不将程序成功推导为最终质量或公开许可。
