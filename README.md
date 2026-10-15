# 文献数字化与 Agent 辅助翻译工作流

这是中文伊里因科夫小组实际使用的文献数字化、AI Agent 辅助翻译、独立审阅、统稿与文本成书工作流的公开整理。公开内容包括规范、Agent 指令和辅助工具，目的是提高翻译方法的透明度，方便他人参考、复用和交流。

使用者按明确的任务交办，结合 Agent、外部工具和人工判断执行各阶段。这不是一套自动翻译软件。

## 适用范围

主要规则形成于俄中哲学文献翻译，保留中文体例、俄文引文和术语判断中的具体约定。使用其他语言或文献类型前，应由 Owner 判断适用范围。

没有随附实际作品、私有术语库、真实审阅记录、扫描件、字体或既有 PDF。示例是为教学人工编写的短文本。

## 从哪里开始

| 任务 | 入口 |
| --- | --- |
| Agent 接受任务及确认权限 | [AGENTS.md](AGENTS.md) |
| 准备使用者自己的项目文件 | [STRUCTURE.md](STRUCTURE.md) |
| 整理 HTML、EPUB、FB2、TXT 等电子文本 | [既有数字文本流程](digitization/EXISTING_DIGITAL_TEXT_WORKFLOW.md) |
| 重建数字原生 PDF | [数字 PDF 流程](digitization/DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md) |
| 核验扫描 PDF | [扫描流程](digitization/SCAN_DIGITIZATION_WORKFLOW.md) |
| 利用 DJVU 文字层 | [DJVU 流程](digitization/DJVU_TEXT_LAYER_WORKFLOW.md) |
| 建立书籍目录、单元和 block-id | [成书预处理](digitization/BOOK_PREPROCESSING.md) |
| 建立翻译分组与批次 | [翻译预处理](digitization/TRANSLATION_PREPROCESSING.md) |
| 翻译一本书或一篇文章 | [书籍流程](translation/TRANSLATION_WORKFLOW.md) · [文章流程](translation/ARTICLE_TRANSLATION_WORKFLOW.md) |
| 翻译与独立审阅 | [Operator 规范](translation/TRANSLATION_STYLE.md) · [Reviewer 规范](translation/REVIEW_STYLE.md) |
| 中文体例与术语 | [标点规范](translation/PUNCTUATION.md) · [术语规则](glossary/GLOSSARY_RULES.md) |
| 记录问题及全书统稿 | [审阅记录](translation/REVIEW_NOTES.md) · [统稿](translation/CONSOLIDATION.md) |
| 整理为可排版文本及校阅 | [成书规范](book/TYPESETTING.md) |
| 查看工具依赖与执行边界 | [工具说明](scripts/README.md) |
| 阅读或练习最小示例 | [示例说明](examples/minimal/README.md) |
| 了解来源与维护方式 | [来源与维护](SOURCE_MAP.md) |

## 怎样使用

先阅读项目契约，再选择当前阶段。任务交办应说明使用者工作区、所用原文与译文、作品和版本、当前角色、范围及完成条件。

规范文件中的相对链接用于阅读本目录的规范。任务中的底本、译文、术语和输出路径属于使用者自己的工作区；命令示例中的占位路径需要明确替换。工具可以使用显式路径调用，不要求将实际项目放入本目录。

主要执行顺序为：

1. 按来源格式选择数字化路线，形成并核验结构化 Markdown。
2. 书籍建立目录、单元和 block-id，再建立翻译分组和批次。
3. Operator 翻译并交接；独立 Reviewer 盲审、明审；Owner 裁决后按流程完成当前批次。
4. 全书批次完成后统稿，处理审阅记录中的具体问题。
5. 将 Markdown 转为语义 LaTeX，由作品工程装配、编译和最终校阅。

文章有独立入口；Owner 也可以明确指定已有译文直接进入某个校阅阶段。以对应流程的进入条件和停止条件为准。

## 人与程序分别做什么

Owner 确定任务范围，裁决文本、术语和质量，决定是否验收及是否允许公开。Operator 与 Reviewer 按角色执行当前阶段，Reviewer 必须独立于本次翻译生产。

程序可以检查部分结构、SHA、脚注配对及编译问题。语义准确性、概念适用、底本疑难、最终版式和公开权利仍需判断。批次完成、定稿、编译成功和最终质量验收分别成立；任何一个状态都不会自动产生发布许可。

规范不绑定固定模型、服务商或 OCR 平台，也没有统一翻译调度器。电子文本提取、PDF 重建、扫描核验、语义分块及统稿中仍有人工或 Agent 操作步骤。

## 实际提供的工具

- DJVU 文字层导出、重建和裁图。
- 约定 Markdown 子集到语义 LaTeX 的转换。
- 已装配 TeX 工程的编译及部分诊断。

依赖、读写范围及限制见[工具说明](scripts/README.md)。没有提供通用 OCR、任意 Markdown 转换、自动章节装配、站点抓取或字体合并工具。

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
