# 辅助工具

这些工具分别辅助数字化、转换和编译，不负责调用翻译模型、分派角色或完成质量验收。先阅读对应阶段规范，由 Owner 指定工作区和任务范围。

以下命令在本仓库根目录调用，示意输入路径均由使用者替换。输入数据和输出工程可以位于仓库之外。输出选在使用者的临时目录或指定工作项目中，不覆盖教学参考材料。

## 运行条件

- Python 3；`pdf_object_audit.py` 声明 Python ≥ 3.10，经 [`uv`](https://docs.astral.sh/uv/) 运行时按脚本头安装依赖。不同脚本还需下表中的外部程序或库。当前未建立跨平台版本兼容矩阵，不承诺所有 Python 3 版本均支持。
- 外部命令须在 `PATH` 中可找到；本仓库不附带程序、字体或底本。
- 命令执行成功，只证明相应程序完成了已实现的检查。语义判断、人工核验和 Owner 授权依各阶段规范。
- 实际验证范围见本文[验证范围与限制](#验证范围与限制)；未运行的依赖不报告为已通过。

| 工具 | 外部条件 | 主要读取 | 写入或输出 |
|---|---|---|---|
| `djvu_text_layer.py extract` | DjVuLibre：`djvudump`、`djvutxt` | 指定 DJVU | 指定目录的逐页文本、坐标及诊断数据 |
| `djvu_text_layer.py rebuild` | Python 标准库；提取结果已存在 | 提取目录、单元表、底本、作品登记；可选修复/表格/图片配置 | 指定目录的单元 Markdown 和索引；确定性检查通过后才替换生成文件 |
| `djvu_text_layer.py crop` | `ddjvu`、Pillow；未提供已提取坐标时还需 `djvutxt` | DJVU、可选词坐标 | 指定图像；处理中会建立同名临时 `.pnm`／`.word.txt` |
| `md_to_latex.py` | Python 标准库 | 一个 Markdown 文件 | 正式 `.tex`、标准输出或显式草稿 |
| `build_book.py` | `xelatex`、`pdfinfo`、`pdffonts`；TeX 宏包、字体和资源 | 已装配的 `main.tex` 工程 | 在工程目录编译 PDF、日志及辅助文件 |
| `pdf_object_audit.py extract` | `uv`（按脚本头声明安装 `pdfplumber`） | 数字原生 PDF、`work.json` | 指定目录的逐页字符、规线与图像对象；底本 SHA-256 不符或未登记时非零退出 |
| `pdf_object_audit.py audit` / `show` | 同上；提取结果已存在 | 提取目录、正文 Markdown、可选 `audit.json` | 候选差异报告 `report.json`；不修改正文 |
| `pdf_object_audit.py targets` | 同上 | 提取目录、可选 `audit.json` 与报告 | 须定向对照的页清单 `targets.json` |
| `pdf_object_audit.py crop` | 同上，另需 Poppler 的 `pdftoppm` | PDF、页码、行内文字 | 指定 PNG 局部放大图 |

## DJVU 文本层

先读 [`DJVU_TEXT_LAYER_WORKFLOW.md`](../digitization/DJVU_TEXT_LAYER_WORKFLOW.md)。

```bash
python3 scripts/djvu_text_layer.py extract 底本.djvu --out 临时目录/提取
python3 scripts/djvu_text_layer.py rebuild 临时目录/提取 --units 单元表.json --source 底本.djvu --work-json 作品目录/work.json --out 临时目录/重建
python3 scripts/djvu_text_layer.py crop 底本.djvu --page 1 --find 行内文字 --out 临时目录/定位.png
```

行末连字符依 [`DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md`](../digitization/DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md) 第 2 步的规则判定，同章以单元为范围；单元表的 `keep_hyphen` 给出经页面图像确认的接法，仍有歧义的保留连字符并列为待核。`standalone_lines`、`numbered_entries` 是按书版面关闭的开关；跨页续接的注文与注文首部的注标由重建识别。

公开用法显式指定 `--source` 和 `--work-json`。兼容默认是输出目录中的 `work.json`，以及该登记文件同级 `source_files/<source_scan.filename>`；不在私有研究目录查找底本。参数结构见脚本末尾 `SCHEMA`。使用者提供实际单元表、修复规则和图片资源，脚本不自动决定全文结构或提取全部插图。

重建前必须完成登记 SHA-256 核验：摘要不符与因底本／登记缺失而未完成核验分别报告，均非零退出。block-id、脚注配对、front matter 和索引等已实现结构检查失败时，重建失败。逐页字符数交叉校验失败也非零退出。字符差、漏词和异文种字母等候选仍须人工核对，不把统计差异直接认定为文本错误。结构通过不能替代逐页核验或最终验收。

裁图使用专用临时目录及新文件名，避免中间文件与既有数据重名。输入的底本、文字层和图片可能受权利限制；工具可执行不构成再分发许可。

## Markdown 转 LaTeX

先读 [`TYPESETTING.md`](../book/TYPESETTING.md)。

```bash
python3 scripts/md_to_latex.py 译文.md -o 临时目录/章节.tex
python3 scripts/md_to_latex.py 译文.md --draft-output 临时目录/章节.draft.tex
```

转换器只处理文件头列出的约定 Markdown 子集，包括 `<em>`、`<strong>`、`<br>`、`<sup>`、`<sub>` 等 HTML 样式、链接、简单表格、诗行和 Markdown 转义，输出 `book…` 语义命令及 `\href`、`\url`、`\textsuperscript`、`\textsubscript`；接收模板负责定义命令、字体、版式和资源。署名识别等规则保留俄中哲学文献实践的具体用法，不能将其理解为通用 Markdown 支持。`--speaker-labels`、`--entry-headwords` 和 `--numeric-notes` 仅在作品结构适用时启用；连续下划线默认按字面输出，`--inline-rule` 显式确认的完整序列才转为图形横线。嵌套脚注、跨单元注释、复杂表格或未列出的 HTML／Markdown 结构没有统一完整支持，须人工检查和作品级处理。

正常输出使用 `-o`。脚注缺定义、数字注未解决等阻断问题出现时返回非零，不写入或覆盖正式文件。正常输出成功时会替换指定文件，因此调用者须核对目标。不要用 shell 重定向覆盖正式文件：重定向会先截断目标。

`--draft-output` 必须显式指定独立、新建的 `*.draft.tex` 路径，不覆盖既有文件，不写回输入。草稿有无未决问题均非零退出，并明确报告草稿性质。它不表示完整转换成功。

自动目录保护只针对**脚本所在仓库**的 `book/projects/` 和 `book/templates/`，包括解析后的路径别名；它不自动保护其他工作区的成书目录。处理外部工程时始终另选独立临时目录。

## 数字 PDF 对象审计

先读 [`DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md`](../digitization/DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md) 第 4 步。

```bash
uv run scripts/pdf_object_audit.py extract 底本.pdf --work-json 作品目录/work.json --out 临时目录
uv run scripts/pdf_object_audit.py audit 临时目录 --md 正文.md --config 临时目录/audit.json --out 临时目录/report.json
uv run scripts/pdf_object_audit.py show 临时目录/report.json --category 类别
uv run scripts/pdf_object_audit.py targets 临时目录 --config 临时目录/audit.json --report 临时目录/report.json --out 临时目录/targets.json
uv run scripts/pdf_object_audit.py crop 底本.pdf --page N --find 行内文字 --out 临时目录/定位.png
```

`extract` 先按 `work.json` 的 `source_scan.sha256` 核对底本，再导出页面对象。`audit` 从页面对象独立推定文字、大小写、斜体、上标、断词、段落、脚注分段与条目边界，与正文 Markdown 比对，输出候选差异；`targets` 列出须定向对照渲染页面的页；`crop` 裁出含指定文字的行及上下若干行。页码范围、条目式版面及已确认的残余差异写在临时目录的 `audit.json`，格式见脚本末尾 `SCHEMA`。

判据针对文字层可用的数字原生 PDF 设计，以页内正文字号、行距和字宽的相对量表述。扫描 PDF、无文字层或字形无法映射的页面不在其适用范围内。候选只作核对线索：程序退出成功不表示核验通过，候选须按页面对象和渲染页面逐条判定。

## 已装配工程编译

```bash
python3 scripts/build_book.py 成书工程目录
```

工程须自行提供主文件、语义宏、章节、字体和图片。脚本不运行 Markdown 转换，不替换模板占位符，不生成版本文件，也不从翻译状态自动装配书籍。

默认执行两遍 XeLaTeX。编译失败或日志发现缺字返回非零；Overfull／Underfull 是需要定位的诊断，不由计数直接裁定排版质量。脚本还显示页数、开本和嵌入字体。`pdfinfo`／`pdffonts` 的返回状态没有被用作统一验收条件，显示缺失或异常时须单独核查，不能把脚本零退出解释为它们均已成功。

编译会原地更新工程产物。教学练习先把人工示例的文本输入和装配文件放入使用者临时工程。最小示例只验证所展示的接口，不完成底本版式测量、正式字体适配或最终校阅。

## 测试

```bash
python3 -B -m unittest discover -s tests
```

`tests/test_md_to_latex.py` 用临时人工输入检查转换器的脚注、数字注、表格、链接、HTML 样式、诗行、图形横线及输出保护，只依赖 Python 标准库。测试不覆盖 DJVU 重建、PDF 对象审计或 LaTeX 编译。

## 验证范围与限制

2026-11-10 的一次本机验证使用 macOS 15.7、Python 3.15.2、uv 0.11.7（pdfplumber 0.11.10）、XeTeX（TeX Live 2026）和 Poppler 26.10.0。以下记录说明实际验证范围，不作为跨平台兼容承诺。

| 范围 | 已验证的内容 |
| --- | --- |
| 脚本语法 | 四个脚本及测试文件语法解析通过 |
| 转换器测试 | 25 项单元测试通过 |
| 教学示例 | 两单元转换退出码为 0；临时工程两遍编译成功，一页，无缺字及 Overfull／Underfull 诊断 |
| PDF 对象审计 | 以教学示例编译出的 PDF 为临时样本，`extract`、`audit`、`show`、`targets`、`crop` 均完成；登记摘要不符时 `extract` 非零退出 |
| DJVU 工具 | 命令行可加载；缺少 Pillow 时 `crop` 报告依赖并非零退出 |

PDF 对象审计的样本是中文排版的教学 PDF，只证明命令链可运行和摘要核对生效，不证明对实际俄文底本的候选质量。尚未验证实际 DJVU 的 extract／rebuild／crop 端到端、实际数字原生 PDF 的审计、完整生产模板、全部特殊 Markdown 结构及跨平台环境。上述检查没有调用翻译模型，也不证明语义质量、最终校阅或公开许可。

## 第三方依赖许可

本项目不分发依赖程序、宏包或字体，使用者须另行核对实际版本的许可。`pdf_object_audit.py` 的 `pdfplumber` 及其依赖由 `uv` 在使用者环境中安装。

第一版暂不收录 PDF 批注提取工具，因为其依赖 PyMuPDF 的具体分发安排尚未完成审查；该工具以后可以另行审议和恢复。PyMuPDF 官方列明 [AGPLv3 或商业许可](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)。这一范围决定不表示 MIT 与 PyMuPDF 必然不兼容，人工 PDF 校阅和验收规则继续适用。

## 尚未随附的能力

未提供统一翻译调度器、通用 OCR、全格式电子书转换器、自动章节拆分器、自动语义验收、字体分发、完整生产成书模板、PDF 批注提取工具或网站发布程序。相应阶段仍依规范、使用者选择的工具及人工判断完成。
