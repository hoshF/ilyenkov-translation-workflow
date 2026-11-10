# 更新记录

## 2026-11-10：术语导入导出

- 新增 `scripts/glossary_io.py`：把术语表导出为交换格式（只含 approved 词条），或把交换格式导入术语表（写为 provisional，Owner 批准时写为 approved）；交换格式与小组网站发布的术语文件一致。
- 新增 `tests/test_glossary_io.py`。

## 2026-11-10：以处理流程为主线

- README 以处理流程为主线：数字化、预处理、翻译与审校、统稿、成书排版；快速开始先请 Agent 介绍流程并给出计划。
- `AGENTS.md`：Owner 未指定角色和步骤时，Agent 先说明处理流程并建议到成书为止的步骤。
- `AGENT_TASKS.md` 新增“了解流程”“数字化”“成书排版”三步。
- 文章教学示例改名为 `examples/article/example-article.md`，作品标识 `example-article`。

## 2026-11-10：规范同步与项目初始化

### 许可

- 全部内容统一以 MIT 发布，许可文件为 `LICENSE`；此前的提交仍适用当时的 CC BY 4.0（Markdown）与 MIT（代码）。

### 使用入口

- 重写 README：面向首次使用者，说明工作方式、快速开始、核心约定与文档导航。
- 新增 `scripts/new_project.py`：在工作流仓库之外建立独立的文章或书籍翻译项目，复制规范到项目的 `workflow/`；成功时不输出，不覆盖已有文件，不执行 Git 操作。
- 新增 `CLAUDE.md`，让 Claude Code 读取同一份 `AGENTS.md`。
- 新增 `AGENT_TASKS.md`：从建立项目到统稿，每一步对 Agent 说的一句话。
- 新增文章教学示例 `examples/article/`。
- 新增 `tests/test_new_project.py`。

### 规范同步

同步小组实践中的现行规范与工具。

- 书籍翻译改为批次分支模型：Operator 批次分支、Reviewer 审校分支、两次 merge；新增补正提交、并行批次与共享文件、Owner 裁决 D 节、Finalization 与 Closeout 核对清单、批次完成后删除分支。流程内的分支、提交与合并在使用者的翻译项目中默认执行。
- 译者与审校规范新增书目、参考文献与索引规则，重复引文核对，原书页码照录，图注标记，标题、关键词与小节编号写法。
- 术语规则新增裁决范围与多个 approved 条目的适用判断。
- 单篇文章注释改为保留原刊注码，新增 `note-label` 显示注码标记与图表标签。
- 文章流程扩大正文排除范围，新增定稿后的后续修订；统稿新增基线、检查结果分类报告与默认 Git 步骤。
- 数字化新增字符恢复、行末连字符判定顺序与排印错误校正；数字 PDF 的 Reviewer 核验改为对象审计加定向页面对照。
- 排版规范新增页码概念区分与 PDF 交付检查。
- 新增 `scripts/pdf_object_audit.py`、`translation/EN_ZH_PATCH.md` 与转换器测试；更新 `md_to_latex.py`、`djvu_text_layer.py`。

## 2026-10-14：首次公开

公开规范、Agent 指令、DJVU 与排版工具及最小教学示例。
