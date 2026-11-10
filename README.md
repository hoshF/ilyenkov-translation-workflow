# ilyenkov-translation-workflow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

这是一套面向哲学文献的 Agent 辅助处理工作流，把一部外文文献从原始底本带到中文定稿和成书：数字化、预处理、翻译与审校、统稿、排版。它由中文伊里因科夫小组在俄译中哲学文献的实践中逐步形成。

工作流通过文本规范、角色分工和辅助工具组织各个环节。Agent 分别承担整理、翻译、独立审校和检查任务；人类 Owner 交办任务、裁决疑难问题并决定最终文本。

仓库不内置翻译模型，也不提供自动化的 Agent 调度。使用者通过 Claude Code、Codex 等本地 Agent 执行任务；底本、原文、译文、术语和审校记录都保存在使用者自己的项目中。

## 处理流程

| 阶段 | 做什么 | 产出 |
| --- | --- | --- |
| 1. 数字化 | 把电子文本、数字 PDF、扫描 PDF 或 DJVU 整理为 Markdown，逐项核验 | 核验过的原文 |
| 2. 预处理 | 书籍拆分单元、编排 block-id，再划分翻译分组与批次 | 单元文件、批次表 |
| 3. 翻译与审校 | Operator 翻译并交接，Reviewer 独立盲审与明审，Owner 裁决，Reviewer 定稿 | 定稿译文、交接与裁决记录 |
| 4. 统稿 | 书籍各批次完成后，核对全书术语与体例的一致性 | 统稿记录 |
| 5. 成书排版 | 定稿译文转为 LaTeX，编译并检查校样 | PDF |

单篇文章不需要第 2、4 步：全部工作记录在一份 `handoff.md` 中，也不用分支和批次。书籍按批次在 Git 分支上翻译和审校。各阶段的规范见[文档](#文档)。

### 角色

| 角色 | 承担者 | 职责 |
| --- | --- | --- |
| Operator | Agent | 整理底本、翻译、自查，把拿不准的问题写进交接 |
| Reviewer | 另一个 Agent 会话 | 先不看交接独立盲审，再读交接定向明审；落实裁决后定稿 |
| Owner | 人 | 交办与授权；裁决译法、原文疑点和术语；验收 |

Reviewer 与 Operator 不共用会话，盲审在读到交接之前完成；所有疑难最终由人裁决。这两点是这套工作流与一般 AI 翻译提示词的主要区别。

## 快速开始

需要一个能读取项目文件、执行命令的本地 Agent，例如 Claude Code 或 Codex。

### 1. 下载工作流并启动 Agent

```bash
git clone https://github.com/hoshF/ilyenkov-translation-workflow.git
cd ilyenkov-translation-workflow
claude    # 或 codex
```

### 2. 了解流程，制定计划

先让 Agent 说明处理流程，并按你手头的底本给出步骤建议：

```text
按 AGENTS.md 介绍这套工作流的处理流程。
我要处理〈一本扫描 PDF 的俄文书／一篇网页上的文章〉，
请建议从数字化到成书的步骤，以及每一步需要我决定什么。先不建立文件。
```

### 3. 建立项目

翻译项目是工作流仓库之外的另一个目录，有自己的文件和 Git 历史。下面用随附的教学示例：

```text
按 AGENTS.md 和 scripts/README.md，使用 examples/article/example-article.md
在 ../example-translation 建立文章翻译项目。
作品标识：example-article
原文题名：Сравнение и различие
中文题名：比较与区别
在新项目中初始化独立 Git 仓库，主分支为 main。只建立项目，不开始翻译。
```

### 4. 在项目中逐步交办

```bash
cd ../example-translation
claude    # 或 codex
```

先说“检查 example-article 处于哪一步，列出到成书为止的剩余步骤”，再按 [AGENT_TASKS.md](AGENT_TASKS.md)（项目中为 `workflow/AGENT_TASKS.md`）一次交办一步。审校时另开一个会话。

> [!NOTE]
> 教学示例的原文没有经过底本核验。练习翻译时，在指令中写明“授权先行翻译未核验底本”；定稿时再另行授权。

## 核心约定

| 约定 | 含义 |
| --- | --- |
| 一次一步 | Agent 一次担任一个角色、执行一个步骤，完成后停下，下一步由 Owner 交办 |
| 审校独立 | Reviewer 由未参与翻译的会话担任，盲审完成前不看 Operator 的交接 |
| 人做决定 | 译法、原文疑点和术语由 Owner 裁决；只有 Owner 批准的术语是权威译法 |
| 记录可查 | 原文、译文、交接、裁决和术语都以 Markdown 或 JSON 保存在项目中，可以追溯每处处理的依据 |
| 版本固定 | 每个项目在 `workflow/` 中保存建立时的规范副本，工作流以后的更新不影响进行中的项目 |

## 术语表

每个项目的 `glossary/` 保存三类术语表：

| 文件 | 收录 |
| --- | --- |
| `glossary.json` | 人名、机构、著作、刊物等专名和体制词 |
| `terms.json` | 通用学科术语 |
| `<作者>.json` | 某位作者的理论概念，如 `ilyenkov.json` |

每个词条记录原词及其词形、中文主译与其他译法、说明和状态。翻译和审校中提出的新词条是候选（`provisional`），Owner 审定后成为权威译法（`approved`）；审校和统稿按 `approved` 词条核对译文。

术语表可以导入和导出，交换格式与小组网站发布的 [glossary.json](https://ilyenkov.cn/glossary.json) 相同。例如在项目中导入小组已审定的术语：

```bash
curl -o tmp/glossary.json --create-dirs https://ilyenkov.cn/glossary.json
python3 workflow/scripts/glossary_io.py import tmp/glossary.json glossary/
```

导入的词条写为候选，是否采用仍由 Owner 决定。导出本项目已审定的术语：

```bash
python3 workflow/scripts/glossary_io.py export glossary/ > glossary-export.json
```

规则见[术语表规则](glossary/GLOSSARY_RULES.md)，选项见[工具说明](scripts/README.md#术语导入导出)。

## 文档

先读：

| 文档 | 内容 |
| --- | --- |
| [AGENT_TASKS.md](AGENT_TASKS.md) | 从了解流程到成书排版，每一步对 Agent 说的一句话 |
| [examples/article/](examples/article/README.md) | 文章教学示例 |
| [examples/minimal/](examples/minimal/README.md) | 书籍教学示例：两个批次 |

按阶段查阅：

| 阶段 | 文档 |
| --- | --- |
| 数字化 | [电子文本](digitization/EXISTING_DIGITAL_TEXT_WORKFLOW.md) · [数字 PDF](digitization/DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md) · [扫描 PDF](digitization/SCAN_DIGITIZATION_WORKFLOW.md) · [DJVU](digitization/DJVU_TEXT_LAYER_WORKFLOW.md) |
| 预处理 | [成书预处理](digitization/BOOK_PREPROCESSING.md) · [翻译预处理](digitization/TRANSLATION_PREPROCESSING.md) |
| 翻译与审校 | [文章流程](translation/ARTICLE_TRANSLATION_WORKFLOW.md) · [书籍流程](translation/TRANSLATION_WORKFLOW.md) · [Operator](translation/TRANSLATION_STYLE.md) · [Reviewer](translation/REVIEW_STYLE.md) · [标点](translation/PUNCTUATION.md) · [术语](glossary/GLOSSARY_RULES.md)（[导入导出](scripts/README.md#术语导入导出)） · [英译中](translation/EN_ZH_PATCH.md) |
| 统稿 | [统稿](translation/CONSOLIDATION.md) · [审阅记录](translation/REVIEW_NOTES.md) |
| 成书排版 | [成书规范](book/TYPESETTING.md) |
| 全程 | [AGENTS.md](AGENTS.md)：Agent 权限与 Git 规则 · [STRUCTURE.md](STRUCTURE.md)：项目文件 · [scripts/](scripts/README.md)：工具 |

## 运行环境

- 本地 Agent：Claude Code、Codex 等。仓库本身不提供 Agent 运行环境。
- Git、Python 3。各脚本的版本要求和可选外部依赖（XeLaTeX、Poppler、DjVuLibre、uv 等）见[工具说明](scripts/README.md)。

## 许可与维护

本仓库是经过审核、可独立使用的公开工作流版本，由中文伊里因科夫小组根据实际项目经验持续维护。规范的来源、更新与同步机制见 [SOURCE_MAP.md](SOURCE_MAP.md)，版本变化见 [CHANGELOG.md](CHANGELOG.md)。欢迎通过 Issue 提出问题和改进建议。

以 [MIT License](LICENSE) 发布。许可不涵盖使用者的底本、译文、第三方依赖和字体。
