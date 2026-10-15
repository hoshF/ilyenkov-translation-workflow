# 最小教学示例：观察与比较

这是为本项目编写的俄中教学材料，不是已完成的研究项目。原文、示范译文和术语均不摘录私有作品；没有真实内部审阅记录、Owner 裁决、Git 提交或流程完成证明。许可和署名状态见[项目许可说明](../../README.md#许可与署名)。

## 阅读顺序与工件

1. 阅读 [连续原文](source/original.md) 和 [作品信息](source/work.json)。
2. 阅读 [单元索引](source/index.md)，对照两个单元的语义分块。
3. 阅读 [翻译分组](translation/index.json) 和 [初始状态](translation/status.json)。
4. 阅读 [候选术语](glossary/terms.json)。
5. 按练习任务生成自己的译文和交接；需要核对接口时再阅读 `reference/` 的示范译文。

`source/` 是底本侧，`translation/` 是练习任务的初始译文工作区，`reference/` 只放教学参考，不是生产译文目录。`translation/index.json` 中的 `file` 均相对于 `translation/`，表示尚待生成的译文路径；这些文件目前不存在，不是遗漏。

对应关系如下：

| 对象 | 底本侧 | 译文侧或任务记录 |
| --- | --- | --- |
| 作品 | `work_id = example-observation-comparison` | 一个译文任务索引 |
| 分组 | 两个来源单元 | `id = text`，`dir = 01-text` |
| 批次 b01 | `u001-observation.md` | 只包含 u001 |
| 批次 b02 | `u002-comparison.md` | 只包含 u002 |
| block-id | 每单元 b000001 至 b000004 | 对应译文照录；不同单元可以重复编号 |

每个单元有四个块，总共八个块。第一单元的脚注定义独立成块；第二单元重新从 b000001 起编。示范译文保留了讨论中的俄词及其强调，用于演示中文与西里尔文混排接口。

## 输入状态与授权

底本就是新编的 `source/original.md`，没有扫描件、HTML 抓取、OCR 或外部版本。不存在的 ISBN、来源登记和扫描摘要不填写，也不为示例建立虚构登记表。

`digitization_route = existing_digital_text` 标识本例采用已有电子文本的整理入口，不表示已经发生某种历史转换。`html_conversion_unverified` 沿用该路线现有的未核验状态名；本例没有进行 HTML 转换，也没有完成正式底本验收，不标为 `human_verified`。

阅读与机械检查不需要启动翻译。若实际开展翻译练习，Owner 须先明确授权使用这一未核验教学输入、指定范围和执行角色。这里没有记录任何授权已经发生。Finalization 仍需单独明确授权；翻译、编译或教学演练均不推导底本验收、最终质量验收或发布许可。

`translation/status.json` 中两个批次都为 `untranslated`，两个提交字段均为 `null`。`reference/` 中有参考文本不改变这些状态。

## 术语格式

`terms.json` 为 JSON 数组，每项使用既有字段：

| 字段 | 内容 |
| --- | --- |
| `id` | 条目标识 |
| `canonical` | 原文规范词形 |
| `forms` | 需要识别的其他词形 |
| `zh_preferred` | 当前候选中文译法 |
| `zh_alternatives` | 其他候选译法；没有则为空数组 |
| `status` | 本例全部为 `provisional` |
| `notes` | 可长期复用的信息；本例留空 |

这些只是结构示范，不是 Reviewer 实际提出或 Owner 批准过的词条，不能当作长期权威。词条归属和权限仍依 [术语表规则](../../glossary/GLOSSARY_RULES.md)。

## 翻译与交接练习

练习应在本地独立副本或指定工作项目中进行，不把教学参考直接改写成生产记录。先读 [书籍翻译流程](../../translation/TRANSLATION_WORKFLOW.md)、对应角色规范和 [标点规范](../../translation/PUNCTUATION.md)。

Owner 实际交办时至少指明：原文为 `source/`、译文根为练习副本的 `translation/`、术语为 `glossary/terms.json`、分组为 `01-text`、批次为 `b01` 或 `b02`，以及本次角色、授权阶段和停止条件。若交办完整书籍流程，Git 操作授权只作用于明确指定的练习项目，不能据此提交规范仓库或其他项目。

- Operator：在指定范围翻译，照录原文 block-id，按主流程自查、交接后停止；不代 Reviewer 或 Owner 完成后续步骤。
- Reviewer：由未参加这次生产的独立 Agent 或会话承担；盲审前不读取 Operator handoff，也不读取示范译文。盲审后的步骤和停止条件依主流程。
- Owner：人工决定疑难、术语和后续阶段；示例不提供可冒用的预填裁决。

以下只是 `b01-handoff.md` 的空白格式，不是已经发生的交接。实际使用时只保留确有必要的未决事项：

```markdown
# b01 Operator handoff

## 待 Reviewer 判断

- 原文和位置：
- 当前译法：
- 未决问题及必要理由：

## glossary 建议

- 候选或修改建议：
- 依据及适用语境：

## 已登记原文疑点

- source issue ID：
```

不要照抄空条目充当已完成的审阅记录。没有原文疑点就不建立虚构 issue；实际原文风险按主流程登记，handoff 只引用对应 ID。

若只练习文章流程，由 Owner 另行指定一份输入和文章译文位置，按 [文章流程](../../translation/ARTICLE_TRANSLATION_WORKFLOW.md) 建立文章工件；不将本书籍示例状态当作文章验收。

## 最小 Markdown → LaTeX 接口

需要 Python 3、XeLaTeX，以及 `ctex`、`xeCJK`、`fontspec`、`geometry`。字体由本机 TeX 环境提供：Fandol Song／Hei／Kai 和 CM Unicode；本项目不分发字体。`build_book.py` 还需要 Poppler 的 `pdfinfo` 和 `pdffonts`。

教学模板将 Cyrillic 纳入 CJK 子块并随语义族切换：汉字正文用 Fandol Song、正文强调用显式 Fandol Hei Bold、附属著录用 Fandol Kai；对应俄文分别显式使用比例 CMU Serif、Sans Bold、Serif Italic 字面，避免使用中文字体中的全角俄文字形。Latin 仍按 Roman／Italic／Bold 路由，并保留俄文词间空格。它只验证本例使用的命令，不能替代生产作品的版式和字体选型。

从仓库根目录运行以下命令。所有转换和编译产物进入新建临时工程，不写回示例或正式成书文件：

```bash
example_tmp=$(mktemp -d "${TMPDIR:-/tmp}/workflow-example.XXXXXX")
python3 scripts/md_to_latex.py examples/minimal/reference/01-text/u001-observation.md -o "$example_tmp/u001.tex"
python3 scripts/md_to_latex.py examples/minimal/reference/01-text/u002-comparison.md -o "$example_tmp/u002.tex"
cp examples/minimal/latex/main.tex "$example_tmp/main.tex"
cp book/templates/minimal/preamble.tex "$example_tmp/preamble.tex"
python3 scripts/build_book.py "$example_tmp"
```

两份转换应包含 `section*`、`bookemph`、`bookstrong` 和一个内嵌 `footnote`，不输出 block-id 注释。实际是否成功以当次诊断和退出状态为准，随后还须检查 PDF 的字形、脚注和强调。编译成功不证明译文质量或正式排版已获验收。

最小模板没有实现转换器的全部语义命令；本例不验证图片、诗行、表格、跨单元注释、标题注或数字注。正式作品遇到这些结构仍按 [成书规范](../../book/TYPESETTING.md) 处理。

不完整转换不能通过 shell 重定向覆盖正常文件；需要保留不完整结果时，显式使用新的独立 `*.draft.tex` 路径，并将非零状态及待处理问题保留为失败结果。
