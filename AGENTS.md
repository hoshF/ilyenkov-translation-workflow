---
title: "Agent 操作规范"
type: "agent-guide"
---

# Agent 操作规范

Agent 是项目助手，不接管项目。做被交代的事，做完停下。

Owner 人工维护项目。Operator 负责翻译、自查和交接；Reviewer 执行独立审阅及对应阶段任务；Owner 裁决疑难、术语和最终质量。Reviewer 必须由未参与本次 Operator 生产的独立 Agent 或会话承担。

数据结构以人工可理解、可直接维护为优先。能通过已有字段、目录结构和文件内容检查的关系，不另建常驻字段、索引或状态系统。

## 任务与工作区

先确认所用规范位置、实际工作区、作品和底本、原文与译文位置、目标语言、范围、当前角色及完成条件。

维护规范目录时，只处理明确交办的文件。示例存在不构成执行练习、更新状态或启动翻译的授权。

使用工作流时，数据位置由任务明确指定。不得到未指定的私人目录寻找底本、术语或记录。原文、译文、术语、记录和成书产物由使用者在自己的工作区维护。

规范文件是执行规则。读取规范不等于收到执行整个流程的任务。各角色完成当前步骤后停止，不自行进入下一角色。

结构与工件关系依 [STRUCTURE.md](STRUCTURE.md)。

## 动手之前先读

| 做什么 | 读哪份 |
| --- | --- |
| 文章翻译／审校 | [文章流程](translation/ARTICLE_TRANSLATION_WORKFLOW.md) · 对应角色规范 · [标点](translation/PUNCTUATION.md) |
| 书籍翻译 | [书籍流程](translation/TRANSLATION_WORKFLOW.md) · [Operator 规范](translation/TRANSLATION_STYLE.md) · [标点](translation/PUNCTUATION.md) |
| 书籍审校 | [书籍流程](translation/TRANSLATION_WORKFLOW.md) · [Reviewer 规范](translation/REVIEW_STYLE.md) · [审阅记录](translation/REVIEW_NOTES.md) · [标点](translation/PUNCTUATION.md) |
| 统稿 | [统稿](translation/CONSOLIDATION.md) · [审阅记录](translation/REVIEW_NOTES.md) |
| 术语 | [术语规则](glossary/GLOSSARY_RULES.md) |
| 排版成书 | [成书规范](book/TYPESETTING.md) |
| 数字化 | [电子文本](digitization/EXISTING_DIGITAL_TEXT_WORKFLOW.md) · [数字 PDF](digitization/DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md) · [扫描 PDF](digitization/SCAN_DIGITIZATION_WORKFLOW.md) · [DJVU](digitization/DJVU_TEXT_LAYER_WORKFLOW.md) |
| 成书预处理 | [成书预处理](digitization/BOOK_PREPROCESSING.md) |
| 书籍翻译预处理 | [翻译预处理](digitization/TRANSLATION_PREPROCESSING.md) |

文章 Operator 使用 TRANSLATION_STYLE，Reviewer 使用 REVIEW_STYLE。阶段权限、工件和停止条件按文章或书籍对应流程执行。

## front matter

单篇文章要，成书章节不要。字段与禁写清单依 STRUCTURE。

## 工具

执行前阅读 [scripts/README.md](scripts/README.md)，确认外部依赖、输入范围和输出位置。

正式转换使用 `-o`，不以 shell 重定向覆盖已有成书文件。不完整草稿显式指定独立临时路径，按非零状态处理。脚本自动保护目录只覆盖其明确实现的范围，不能推定覆盖任意外部工作区。

不得自行增加常驻脚本或统一调度程序。

## Git

**默认不提交。** 只有明确要求时才提交。

Owner 明确交办“执行完整书籍翻译流程”时，授权执行该流程规定的 Git 分支、提交与合并。该授权只作用于指定工作项目。

调查、检查、部分翻译或规范修订不自动取得上述授权；阅读流程文件本身不构成授权。

底本、字体和工作记录不因执行流程取得 Git 收录或公开许可。

要求提交时尽量一步一个主题；不为拆分提交专门还原用户文件。提交信息用英文，只写本次改变。不重写历史，不加 assistant 署名，不代项目签名。

## 验收与边界

- Owner 明确授权时可先翻译未完成全文核验的指定范围；保留真实状态、风险和授权范围。Finalization 另须明确授权。
- 已有译文只进入指定校阅阶段，不补造翻译批次、审阅或提交历史。
- 真实术语冲突按角色及术语规范暂译、交接和裁决，不擅自改写 approved 权威。
- 数字化核验、批次 translated、Finalization、统稿、转换、编译、最终校阅和公开许可分别判断。
- 检查失败报告失败并附输出；跳过报告跳过，不将未核验报告为通过。
- 保留用户改动，覆盖或删除前先检查目标。
- 写规范只写结构与规则；任务中的临时补丁不进入通则。
- 角色规范的完整规则与完成标准保留，不因其他角色也有同类规则而删除。
- 不扩大交办范围，不增加只为 Agent 推断或自治服务的永久数据。
