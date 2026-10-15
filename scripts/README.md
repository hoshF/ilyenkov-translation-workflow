# 辅助工具

这些工具分别辅助数字化、转换和编译，不负责调用翻译模型、分派角色或完成质量验收。先阅读对应阶段规范，由 Owner 指定工作区和任务范围。

以下命令在本仓库根目录调用，示意输入路径均由使用者替换。输入数据和输出工程可以位于仓库之外。输出选在使用者的临时目录或指定工作项目中，不覆盖教学参考材料。

## 运行条件

- Python 3；不同脚本还需下表中的外部程序或库。当前未建立跨平台版本兼容矩阵，不承诺所有 Python 3 版本均支持。
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

## DJVU 文本层

先读 [`DJVU_TEXT_LAYER_WORKFLOW.md`](../digitization/DJVU_TEXT_LAYER_WORKFLOW.md)。

```bash
python3 scripts/djvu_text_layer.py extract 底本.djvu --out 临时目录/提取
python3 scripts/djvu_text_layer.py rebuild 临时目录/提取 --units 单元表.json --source 底本.djvu --work-json 作品目录/work.json --out 临时目录/重建
python3 scripts/djvu_text_layer.py crop 底本.djvu --page 1 --find 行内文字 --out 临时目录/定位.png
```

公开用法显式指定 `--source` 和 `--work-json`。兼容默认是输出目录中的 `work.json`，以及该登记文件同级 `source_files/<source_scan.filename>`；不在私有研究目录查找底本。参数结构见脚本末尾 `SCHEMA`。使用者提供实际单元表、修复规则和图片资源，脚本不自动决定全文结构或提取全部插图。

重建前必须完成登记 SHA-256 核验：摘要不符与因底本／登记缺失而未完成核验分别报告，均非零退出。block-id、脚注配对、front matter 和索引等已实现结构检查失败时，重建失败。逐页字符数交叉校验失败也非零退出。字符差、漏词和异文种字母等候选仍须人工核对，不把统计差异直接认定为文本错误。结构通过不能替代逐页核验或最终验收。

裁图使用专用临时目录及新文件名，避免中间文件与既有数据重名。输入的底本、文字层和图片可能受权利限制；工具可执行不构成再分发许可。

## Markdown 转 LaTeX

先读 [`TYPESETTING.md`](../book/TYPESETTING.md)。

```bash
python3 scripts/md_to_latex.py 译文.md -o 临时目录/章节.tex
python3 scripts/md_to_latex.py 译文.md --draft-output 临时目录/章节.draft.tex
```

转换器只处理文件头列出的约定 Markdown 子集，输出 `book…` 语义命令；接收模板负责定义命令、字体、版式和资源。署名识别等规则保留俄中哲学文献实践的具体用法，不能将其理解为通用 Markdown 支持。`--speaker-labels`、`--entry-headwords` 和 `--numeric-notes` 仅在作品结构适用时启用。嵌套脚注、跨单元注释、复杂表格或未列出的 HTML／Markdown 结构没有统一完整支持，须人工检查和作品级处理。

正常输出使用 `-o`。脚注缺定义、数字注未解决等阻断问题出现时返回非零，不写入或覆盖正式文件。正常输出成功时会替换指定文件，因此调用者须核对目标。不要用 shell 重定向覆盖正式文件：重定向会先截断目标。

`--draft-output` 必须显式指定独立、新建的 `*.draft.tex` 路径，不覆盖既有文件，不写回输入。草稿有无未决问题均非零退出，并明确报告草稿性质。它不表示完整转换成功。

自动目录保护只针对**脚本所在仓库**的 `book/projects/` 和 `book/templates/`，包括解析后的路径别名；它不自动保护其他工作区的成书目录。处理外部工程时始终另选独立临时目录。

## 已装配工程编译

```bash
python3 scripts/build_book.py 成书工程目录
```

工程须自行提供主文件、语义宏、章节、字体和图片。脚本不运行 Markdown 转换，不替换模板占位符，不生成版本文件，也不从翻译状态自动装配书籍。

默认执行两遍 XeLaTeX。编译失败或日志发现缺字返回非零；Overfull／Underfull 是需要定位的诊断，不由计数直接裁定排版质量。脚本还显示页数、开本和嵌入字体。`pdfinfo`／`pdffonts` 的返回状态没有被用作统一验收条件，显示缺失或异常时须单独核查，不能把脚本零退出解释为它们均已成功。

编译会原地更新工程产物。教学练习先把人工示例的文本输入和装配文件放入使用者临时工程。最小示例只验证所展示的接口，不完成底本版式测量、正式字体适配或最终校阅。

## 验证范围与限制

2026-10-14 的一次本机验证使用 macOS、Python 3.14.7、XeTeX（TeX Live 2026）和 Poppler 26.09.0。以下记录说明实际验证范围，不作为跨平台兼容承诺。

| 范围 | 已验证的内容 |
| --- | --- |
| 脚本与人工输入 | 随附三脚本语法通过；正常脚注转换成功 |
| 输出保护 | 缺注返回非零且保留既有正式文件；独立草稿保留未决内容、返回非零并拒绝覆盖既有草稿 |
| DJVU 重建检查 | 人工临时样本中正确 SHA 通过；摘要不符与未完成核验分别报告并非零；错误 block-id 阻断，统计差仅作候选 |
| 教学示例 | 两单元转换及临时工程两遍编译成功；一页，无缺字及 Overfull／Underfull 诊断；已检查页面和字体路由 |

尚未验证实际 DJVU 的 extract／crop 端到端、完整生产模板、全部特殊 Markdown 结构及跨平台环境。上述测试没有调用翻译模型，也不证明语义质量、最终校阅或公开许可。

在上述环境中，执行 `from PIL import Image` 失败，输出 `ImportError: cannot import name 'Image' from 'PIL'`；当次裁图依赖未满足，因此没有报告裁图通过。这是一次环境记录，使用者仍须检查自己的 Pillow 安装。

本次发布前整理重新检查了修改后的文档、文件范围、链接、示例状态和脚本语法；未重新运行 DJVU 或 LaTeX 编译。

## 第三方依赖许可

本项目不分发依赖程序、宏包或字体，使用者须另行核对实际版本的许可。

第一版暂不收录 PDF 批注提取工具，因为其依赖 PyMuPDF 的具体分发安排尚未完成审查；该工具以后可以另行审议和恢复。PyMuPDF 官方列明 [AGPLv3 或商业许可](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)。这一范围决定不表示 MIT 与 PyMuPDF 必然不兼容，人工 PDF 校阅和验收规则继续适用。

## 尚未随附的能力

未提供统一翻译调度器、通用 OCR、全格式电子书转换器、自动章节拆分器、自动语义验收、字体分发、完整生产成书模板、PDF 批注提取工具或网站发布程序。相应阶段仍依规范、使用者选择的工具及人工判断完成。
