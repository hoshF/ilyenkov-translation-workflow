# ilyenkov-translation-workflow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

这是一套面向哲学文献的 Agent 辅助翻译工作流，由中文伊里因科夫小组在俄译中哲学文献的数字化、翻译、审校和成书实践中逐步形成。

工作流通过文本规范、角色分工和辅助工具，组织从原文准备到译文定稿的各个环节。Agent 分别承担翻译、独立审校和检查任务；人类 Owner 负责交办任务、裁决疑难问题并决定最终文本。

仓库不内置翻译模型，也不提供自动化的 Agent 调度。使用者通过 Claude Code、Codex 等本地 Agent 执行任务；原文、译文、术语和审校记录都保存在使用者自己的翻译项目中。

## 工作方式

以单篇文章为例：

| 角色 | 做什么 |
| --- | --- |
| Operator（Agent） | 翻译原文、自查，把拿不准的问题写进交接记录 |
| Reviewer（另一个 Agent 会话） | 先不看交接独立盲审，再读交接定向明审 |
| Owner（人） | 裁决译文、术语和未决问题 |
| Reviewer | 落实裁决，完成定稿检查 |

Reviewer 与 Operator 不共用会话，盲审在读到译者的交接之前完成；所有疑难最终由人裁决。这两点是这套工作流与一般 AI 翻译提示词的主要区别。

文章的全部工作记录在一份 `handoff.md` 中，不需要分支和批次。书籍另有预处理（单元与 block-id）、按批次的 Git 分支审校、批次收尾和全书统稿。详见[文章流程](translation/ARTICLE_TRANSLATION_WORKFLOW.md)和[书籍流程](translation/TRANSLATION_WORKFLOW.md)。

## 快速开始

需要先安装一个能读取项目文件、执行命令的本地 Agent，例如 Claude Code 或 Codex。

**1. 下载工作流，在工作流仓库中启动 Agent**

```bash
git clone https://github.com/hoshF/ilyenkov-translation-workflow.git
cd ilyenkov-translation-workflow
claude    # 或 codex
```

**2. 让 Agent 建立翻译项目**

翻译项目是工作流仓库之外的另一个目录，有自己的文件和 Git 历史。下面用随附的教学原文：

```text
按 AGENTS.md 和 scripts/README.md，使用 examples/article/sravnenie-i-razlichie.md
在 ../my-translation 创建文章翻译项目。
作品标识：sravnenie-i-razlichie
原文题名：Сравнение и различие
中文题名：比较与区别
在新项目中初始化独立 Git 仓库，主分支为 main。
只完成项目初始化，不开始翻译。
```

**3. 在翻译项目中逐步交办**

```bash
cd ../my-translation
claude    # 或 codex
```

按 [AGENT_TASKS.md](AGENT_TASKS.md)（项目中为 `workflow/AGENT_TASKS.md`）一次交办一步，例如先说“作为 Operator，按文章流程第 1 步翻译 sravnenie-i-razlichie”。审校时另开一个会话。

教学原文尚未完成底本核验。练习翻译时，在指令中写明授权先行翻译未核验底本；进入定稿时再另行授权。

## 核心约定

- **一次一个角色、一个步骤。** Agent 完成当前步骤后停下，下一步由 Owner 交办。
- **审校独立。** Reviewer 由未参与翻译的会话担任，盲审完成前不看 Operator 的交接。
- **人做决定。** 译法、原文疑点和术语的最终结论由 Owner 裁决；只有 Owner 批准的术语是权威译法。
- **记录可查。** 译文、交接、裁决和术语决定都以 Markdown 或 JSON 保存在项目中，可以追溯每处处理的依据。
- **版本固定。** 每个翻译项目在 `workflow/` 中保存建立时的规范副本，工作流以后的更新不影响进行中的项目。

## 文档

先读：

| 文档 | 内容 |
| --- | --- |
| [AGENT_TASKS.md](AGENT_TASKS.md) | 每一步对 Agent 说的一句话 |
| [examples/article/](examples/article/README.md) | 文章教学示例 |
| [examples/minimal/](examples/minimal/README.md) | 书籍教学示例：两个批次 |

需要时查阅：

| 文档 | 内容 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Agent 的权限、Git 规则，以及每类任务要读哪些规范 |
| [STRUCTURE.md](STRUCTURE.md) | 翻译项目中的文件及各自保存什么 |
| [translation/](translation/) | 翻译、审校、统稿、标点规范；[英译中补充规则](translation/EN_ZH_PATCH.md) |
| [glossary/](glossary/GLOSSARY_RULES.md) | 术语规则 |
| [digitization/](digitization/) | 电子文本、数字 PDF、扫描 PDF、DJVU 的数字化，以及成书与翻译预处理 |
| [book/](book/TYPESETTING.md) | 排版规范与最小模板 |
| [scripts/](scripts/README.md) | 项目初始化、数字化、转换与编译工具 |

## 运行环境

- 本地 Agent：Claude Code、Codex 等。仓库本身不提供 Agent 运行环境。
- Git、Python 3。各脚本的版本要求和可选外部依赖（XeLaTeX、Poppler、DjVuLibre、uv 等）见[工具说明](scripts/README.md)。

## 许可与维护

本仓库是经过审核、可独立使用的公开工作流版本，由中文伊里因科夫小组根据实际项目经验持续维护。规范的来源、更新与同步机制见 [SOURCE_MAP.md](SOURCE_MAP.md)，版本变化见 [CHANGELOG.md](CHANGELOG.md)。欢迎通过 Issue 提出问题和改进建议。

以 [MIT License](LICENSE) 发布。许可不涵盖使用者的底本、译文、第三方依赖和字体。
