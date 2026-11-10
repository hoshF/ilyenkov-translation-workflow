# ilyenkov-translation-workflow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

交给本地 Agent 执行的文献翻译工作流：纯文本规范，加几个各做一件事的小工具。

由中文伊里因科夫小组在俄译中哲学文献翻译中形成并实际使用。Agent 按角色分步工作，人做决定。它不翻译，也不调度模型。

## 开始

```bash
git clone https://github.com/hoshF/ilyenkov-translation-workflow.git
cd ilyenkov-translation-workflow
claude    # 或 codex
```

对 Agent 说：

```text
按 AGENTS.md，在 ../my-translation 为 examples/article/sravnenie-i-razlichie.md 建立文章翻译项目。
```

然后在新项目里启动 Agent，一次交办一步，指令见 [AGENT_TASKS.md](AGENT_TASKS.md)。

## 约定

- **一个文件管一件事。** 规范、原文、译文、术语和记录都是 Markdown 或 JSON，人和 Agent 读同一份。
- **一次做一步。** Agent 一次只担任一个角色、执行一个步骤，完成后停下。
- **人做决定。** Owner 交办、授权和裁决；Reviewer 由另一个会话担任，盲审前不看 Operator 的交接。
- **项目自带规范。** 每个翻译项目把规范复制到自己的 `workflow/`，各自固定版本，互不影响。
- **工具安静。** 成功时不输出，失败时写 stderr 并以非零状态退出；不覆盖已有文件。

## 内容

| 路径 | 内容 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Agent 入口：权限、Git、动手前要读哪份规范 |
| [AGENT_TASKS.md](AGENT_TASKS.md) | 每一步对 Agent 说的一句话 |
| [STRUCTURE.md](STRUCTURE.md) | 项目里有哪些文件，各存什么 |
| [translation/](translation/) | 翻译、审校、统稿与标点规范；[书籍](translation/TRANSLATION_WORKFLOW.md) · [文章](translation/ARTICLE_TRANSLATION_WORKFLOW.md) |
| [digitization/](digitization/) | 电子文本、数字 PDF、扫描 PDF、DJVU 的数字化，及成书、翻译预处理 |
| [glossary/](glossary/GLOSSARY_RULES.md) | 术语规则 |
| [book/](book/TYPESETTING.md) | 排版规范与最小模板 |
| [scripts/](scripts/README.md) | `new_project.py` · `md_to_latex.py` · `build_book.py` · `djvu_text_layer.py` · `pdf_object_audit.py` |
| [examples/](examples/) | [文章](examples/article/README.md)与[书籍](examples/minimal/README.md)教学示例 |

## 依赖

Git 和 Python 3。可选：XeLaTeX 与 Poppler（排版），DjVuLibre（DJVU），uv（PDF 审计）。

```bash
python3 -B -m unittest discover -s tests
```

## 许可

[MIT](LICENSE)。不涵盖使用者的底本、译文、第三方依赖和字体。规则以小组的私有实践仓库为准，单向同步到这里，见 [SOURCE_MAP.md](SOURCE_MAP.md)；问题和建议请提 Issue。
