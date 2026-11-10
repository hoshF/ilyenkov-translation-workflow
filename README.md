# 文献数字化与 Agent 辅助翻译工作流

这是中文伊里因科夫小组实际使用的文献数字化、AI Agent 辅助翻译、独立审阅、统稿与成书工作流的公开整理。它由规范、Agent 指令和少量辅助工具组成：使用者在自己的翻译项目里，把具体任务交给 Claude Code、Codex 等本地 Agent，由 Owner 判断和裁决。

它不是自动翻译软件，也不调度模型。每一步由 Owner 交办，Agent 执行一个角色的当前步骤后停止。

规则主要形成于俄译中的哲学文献翻译，保留中文体例、俄文引文和术语判断的具体约定；英文底本另有[英译中补充规则](translation/EN_ZH_PATCH.md)。用于其他语言或文献类型前，由 Owner 判断适用范围。

## 快速开始

需要 Git、Python 3，以及 Claude Code 或 Codex。下面用随附的文章示例走一遍。

**1. 下载工作流**

```bash
git clone https://github.com/hoshF/ilyenkov-translation-workflow.git
cd ilyenkov-translation-workflow
```

**2. 在工作流之外建立翻译项目**

```bash
python3 scripts/new_project.py article ../translation-practice --work-id sravnenie-i-razlichie --title "Сравнение и различие" --title-zh "比较与区别" --source examples/article/sravnenie-i-razlichie.md
cd ../translation-practice
git init -b main
```

项目里有入口文件 `AGENTS.md`、`CLAUDE.md`，规范副本 `workflow/`，空术语表 `glossary/`，原文 `source/` 和作品信息 `translation/<work-id>/work.json`。翻译工件由后续步骤建立。

**3. 在项目目录启动 Agent**

```bash
claude
```

或

```bash
codex
```

先让 Agent 检查项目，再按结果交办下一步：

```text
工作区：当前项目根目录。先读 AGENTS.md 和 workflow/AGENTS.md。
任务：只读检查作品 sravnenie-i-razlichie 所处的阶段。不修改文件，不执行 Git 写操作。
handoff 文件只确认是否存在，不读取内容，使本会话以后仍可担任 Reviewer。
报告：原文与 work.json 的位置及 text_status；已有的翻译工件；下一步由哪个角色执行哪一步；
开始前需要 Owner 决定或授权的事项。
停止：报告后停止。
```

后续各步的指令见 [Agent 任务指令模板](AGENT_TASKS.md)。示例原文的核验状态和练习授权见[文章示例说明](examples/article/README.md)。

## 建立自己的项目

```bash
python3 scripts/new_project.py article 项目目录 --work-id 作品标识 --title "原文题名" --title-zh "中文题名" --source 原文.md
python3 scripts/new_project.py book 项目目录 --work-id 作品标识 --title "原文题名" --year 出版年 --source-edition "底本版本"
```

- 项目目录不存在或为空时建立新项目；已是本工具建立的项目时，只加入新作品。其他非空目录、已被占用的作品标识都会被拒绝，不改动任何文件。
- 作品标识用小写字母、数字和连字符。`--year`、`--source-edition`、`--source-url` 按实际填写，没有就不填。
- 加 `--dry-run` 只列出将要建立的文件。
- 在项目里加入其他作品时，可以直接调用项目自带的副本：`python3 workflow/scripts/new_project.py book . --work-id 作品标识 --title "原文题名"`。
- 本工具不执行 Git 操作。书籍流程要求项目是以 `main` 为主分支的 Git 仓库，由使用者自己 `git init -b main` 并提交初始文件。

## Agent 怎样找到规范

项目的 `AGENTS.md` 指向 `workflow/AGENTS.md`，并列出规范中的工作区位置在本项目的对应目录。Codex 直接读取项目根目录的 `AGENTS.md`；Claude Code 读取 `CLAUDE.md`，其内容 `@AGENTS.md` 导入同一份文件。

`workflow/` 是建立项目时复制的规范，随项目一起提交，版本记在 `workflow/WORKFLOW_VERSION.txt`。项目因此不依赖工作流仓库的位置，以后的规范更新也不会改变已在进行的项目。

## 文章与书籍

**单篇文章**依[文章流程](translation/ARTICLE_TRANSLATION_WORKFLOW.md)，在一个译文目录中完成：

1. 原文尚未整理为 Markdown 时，按来源格式选择[数字化路线](#文档导航)。
2. Operator 翻译全文并写 `handoff.md` 的交接。
3. Reviewer 在新会话中先盲审，盲审完成后才读 handoff，再明审。
4. Owner 修改译文并在 handoff 记录裁决。
5. Reviewer 完成 Finalization。

文章流程默认不建分支、不要求提交。

**书籍**依[书籍流程](translation/TRANSLATION_WORKFLOW.md)，按批次执行：

1. 数字化并核验原文，再做[成书预处理](digitization/BOOK_PREPROCESSING.md)（单元与 block-id）和[翻译预处理](digitization/TRANSLATION_PREPROCESSING.md)（分组、批次、`index.json`、`status.json`）。
2. 每个批次：Operator 在批次分支翻译并提交 handoff → Reviewer 在新会话中从 translation 提交建审校分支，盲审、明审 → Owner 裁决 → Reviewer Finalization 并合回批次分支 → Operator closeout 合入 `main`。
3. 全书批次完成后[统稿](translation/CONSOLIDATION.md)。
4. 需要时按[成书规范](book/TYPESETTING.md)转为 LaTeX 并编译。

书籍流程中的分支、提交与合并由 Agent 按规范在翻译项目里默认执行。[最小书籍示例](examples/minimal/README.md)有两个单元、两个批次，可用于练习一个批次的全过程。

## 角色

| 角色 | 做什么 |
| --- | --- |
| Owner | 交办任务、确定范围与授权；裁决译法、原文疑点和术语；决定验收与是否公开 |
| Operator | 翻译、自查、交接；书籍还负责批次分支与 closeout |
| Reviewer | 独立盲审、明审、维护候选术语、落实 Owner 裁决后的 Finalization |

Reviewer 由未参与本次 Operator 翻译的独立 Agent 或会话承担，盲审完成前不接触 Operator 的 handoff。每个角色完成当前步骤后停止，由 Owner 交办下一步。只有 Owner 批准的 `approved` 词条是术语权威。

## 文档导航

| 任务 | 入口 |
| --- | --- |
| Agent 接受任务及确认权限 | [AGENTS.md](AGENTS.md) |
| 复制给 Agent 的任务指令 | [任务指令模板](AGENT_TASKS.md) |
| 项目文件与工件关系 | [STRUCTURE.md](STRUCTURE.md) |
| 整理 HTML、EPUB、FB2、TXT 等电子文本 | [既有数字文本流程](digitization/EXISTING_DIGITAL_TEXT_WORKFLOW.md) |
| 重建数字原生 PDF | [数字 PDF 流程](digitization/DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md) |
| 核验扫描 PDF | [扫描流程](digitization/SCAN_DIGITIZATION_WORKFLOW.md) |
| 利用 DJVU 文字层 | [DJVU 流程](digitization/DJVU_TEXT_LAYER_WORKFLOW.md) |
| 建立书籍目录、单元和 block-id | [成书预处理](digitization/BOOK_PREPROCESSING.md) |
| 建立翻译分组与批次 | [翻译预处理](digitization/TRANSLATION_PREPROCESSING.md) |
| 翻译一本书或一篇文章 | [书籍流程](translation/TRANSLATION_WORKFLOW.md) · [文章流程](translation/ARTICLE_TRANSLATION_WORKFLOW.md) |
| 翻译与独立审阅 | [Operator 规范](translation/TRANSLATION_STYLE.md) · [Reviewer 规范](translation/REVIEW_STYLE.md) |
| 英文底本译成中文 | [英译中补充规则](translation/EN_ZH_PATCH.md) |
| 中文体例与术语 | [标点规范](translation/PUNCTUATION.md) · [术语规则](glossary/GLOSSARY_RULES.md) |
| 记录问题及全书统稿 | [审阅记录](translation/REVIEW_NOTES.md) · [统稿](translation/CONSOLIDATION.md) |
| 整理为可排版文本及校阅 | [成书规范](book/TYPESETTING.md) |
| 工具依赖与执行边界 | [工具说明](scripts/README.md) |
| 教学示例 | [文章示例](examples/article/README.md) · [书籍示例](examples/minimal/README.md) |
| 版本变化 | [更新记录](CHANGELOG.md) |
| 来源与维护方式 | [来源与维护](SOURCE_MAP.md) |

## 工具、依赖与限制

| 工具 | 用途 | 依赖 |
| --- | --- | --- |
| `new_project.py` | 建立翻译项目、加入作品 | Python 标准库 |
| `djvu_text_layer.py` | DJVU 文字层导出、重建和裁图 | DjVuLibre；裁图另需 Pillow |
| `pdf_object_audit.py` | 数字原生 PDF 对象审计、定向对照页清单和裁图 | `uv`（自动安装 pdfplumber）；裁图另需 Poppler |
| `md_to_latex.py` | 约定 Markdown 子集转语义 LaTeX | Python 标准库 |
| `build_book.py` | 编译已装配的 TeX 工程并报告诊断 | XeLaTeX、Poppler |

各工具的读写范围、命令和已验证范围见[工具说明](scripts/README.md)。在工作流仓库运行测试：

```bash
python3 -B -m unittest discover -s tests
```

程序可以检查部分结构、摘要、脚注配对及编译问题；语义准确性、概念适用、底本疑难、最终版式和公开权利仍由人判断。批次完成、定稿、编译成功和最终验收各自成立，任何一个都不自动产生发布许可。规范不绑定固定模型、服务商或 OCR 平台。没有提供通用 OCR、任意 Markdown 转换、自动章节装配、站点抓取或字体合并工具。

仓库不附带实际作品、私有术语库、真实审阅记录、扫描件、字体或既有 PDF。示例是为教学编写的短文本。

## 来源与维护

工作流实质规则以小组私有实践仓库为权威来源。本目录经逐文件选择及公开适配形成，不包含其 Git 历史。公开适配限于目录、登记、环境和使用说明。

维护者依据内部来源映射核对更新。共同规则的改进经私有侧评审和实际验证后重新投影；公开文件不会自动反向覆盖私有仓库。来源与维护方式见 [说明](SOURCE_MAP.md)。

## 报告问题与提出改进

可以向维护者提交问题或修改建议，并注明相关文件、步骤、工具环境、复现方法和期望行为。优先提供人工编写的最小样例；实际作品、批注、密钥和内部记录须先确认可以分享。

规则建议、工具缺陷和具体译文判断应说明各自范围。涉及工作流实质规则的建议由 Owner 审定。

## 许可与署名

本项目由 **Chinese Ilyenkov Group（中文伊里因科夫小组）** 维护，并以小组名义对外署名。

个人保留其有权许可的原创内容版权，版权声明见 [LICENSE-CODE](LICENSE-CODE)。对外署名不改变个人版权归属。

| 文件范围 | 适用许可证 |
| --- | --- |
| 所有 Markdown：规范、Agent 指令、说明及原创教学文本 | [CC BY 4.0](LICENSE-DOCS) |
| Python 脚本、LaTeX 模板、JSON 配置及根目录 `.gitignore` | [MIT License](LICENSE-CODE) |
| 两份 LICENSE 文件 | 保留正式条款及其自身说明，不主张项目拥有条款文本版权 |

本项目使用 AI Agent 辅助创作、编辑及开发。对于不构成受版权保护的人类创作的部分，不主张超出法律所允许范围的专有权利。

上述许可只涉及有权许可的原创内容。标准名称、书目和格式示例中的现有作者、题名及出处信息保留，不据此授予相关外部作品的权利。第三方材料、使用者底本与译文、外部依赖和字体不因出现在工作流中被重新许可；来源或授权不能确认的材料不自动纳入上述许可。
