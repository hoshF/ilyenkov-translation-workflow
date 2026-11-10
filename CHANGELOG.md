# 更新记录

## 未发布

### 许可

- 全部内容统一以 MIT 发布，许可文件为 `LICENSE`；此前发布的版本仍适用其发布时的 CC BY 4.0（Markdown）与 MIT（代码）。

### 使用入口

- 重写 README：以 Agent 为默认使用方式，只保留开始、约定、内容、依赖与许可。
- 新增 `scripts/new_project.py`：在工作流仓库之外建立独立的文章或书籍翻译项目，复制规范到项目的 `workflow/`；成功时不输出，不覆盖已有文件，不执行 Git 操作。
- 新增 `CLAUDE.md`，让 Claude Code 读取同一份 `AGENTS.md`。
- 新增 `AGENT_TASKS.md`：从建立项目到统稿，每一步对 Agent 说的一句话。
- 新增文章教学示例 `examples/article/`。
- 新增 `tests/test_new_project.py`。

## 2026-11-10：规范同步

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
