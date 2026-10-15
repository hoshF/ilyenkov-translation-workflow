#!/usr/bin/env python3
r"""把一份译文 Markdown 转成 LaTeX 章节文件。

只处理本项目译文实际用到的这几种标记，不追求通用 Markdown：

* `<!-- block-id: bNNNNNN -->`  —— 块锚点，用作分块依据，不输出
* 其余 HTML 注释                —— 结构标记，读取后剥除，不输出
* `### 标题`                    —— section*（保留原文标题，不进目录编号）
* `*强调*`                      —— \bookemph{}（署名与行内著录走 \bookapparatus）
* `**强调**`                    —— \bookstrong{}（发言人、词头见下）
* `***强调***`                  —— 粗斜体：\bookstrong{\bookemph{}}；落在发言人、词头、署名上时随该结构
* 行尾 `\`                      —— 强制换行（诗行）：\\；含强制换行的块整块走 \bookverse{}
* `[^id]` 与 `[^id]:`           —— 脚注：把定义就地嵌进第一次引用处
* 数字注（--numeric-notes）     —— 正文里的裸数字注号与文末 `N 注文` 块，同样转成脚注
* `* * *`                       —— \bookseparator
* 行首 `- ` 与 `> `             —— \bookitem{} 与 \booknote{}
* 连续下划线                    —— \bookinlinerule（手稿分隔线，非字面下划线）
* `![说明](assets/…)`           —— \bookfigure{}（就地插入；说明文字不输出）
* 段落                          —— 逐块输出

样式记号到语义命令的分流依 `book/TYPESETTING.md` 第二、三节。发言人标签与人物志词头
按**块的结构位置**判断，不按字面像不像人名，且只在调用方明确开启时才判（见 --speaker-labels
与 --entry-headwords）——这两种结构不是每本书都有，不能作全局启发式。

**为什么不用 pandoc**：pandoc 会重排中文标点、可能吃掉六角括号与全角空格，
而本书的〔〕、强调、`＊　＊　＊` 都是体例的一部分，错一个就破坏可分辨性。
这个转换器处理已知记号；转换报告包含已识别的脚注问题、数字续段及标题注人工处理提示。
未知格式没有统一检测，须按排版规范人工核对。

用法：
    python3 scripts/md_to_latex.py 译文.md -o 章节.tex

正常转换未完成时不写输出；作品级手工处理用独立的 --draft-output 章节.draft.tex，退出码仍非零。
不要用重定向覆盖已有章节：shell 会在脚本运行前截断文件。
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
import tempfile
from pathlib import Path


def blocks_of(path: Path) -> list[str]:
    """按 `<!-- block-id: bNNNNNN -->` 锚点切块；无锚点时按空行分段。"""
    text = path.read_text(encoding="utf-8")
    # 不换行连字符 U+2011 是底本转换留下的技术字符，正文西文字体没有这个字形，
    # 排出来是缺字。它的语言功能就是连字符，按 PUNCTUATION.md 第五节归普通连字符。
    text = text.replace("\u2011", "-")
    front = re.match(r"\A---\r?\n.*?\r?\n---\r?\n", text, re.DOTALL)
    body = text[front.end():] if front else text
    marks = list(re.finditer(r"(?m)^<!-- block-id: b\d{6} -->\s*$", body))
    if marks:
        return [
            body[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(body))].strip()
            for i, m in enumerate(marks)
        ]
    return [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]


# LaTeX 特殊字符转义（中文正文里主要是这几个会出问题）。
SPECIALS = [
    ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
    ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
    ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
]
# 反斜杠不能与上面这些同批处理，两种次序都错：先转它，它换出的
# `\textbackslash{}` 里那对花括号会被后面的 { } 规则再转义一遍，排成可见的
# 「\{}」；后转它，又会把 \& \% 一类刚加上的反斜杠再转一遍。故先换成哨符
# （NUL 包夹，正文不可能出现），全部转完再还原。
BACKSLASH_SENTINEL = "\0BS\0"


# 字体路由由接收这些语义命令的 template / preamble 实现，依 book/TYPESETTING.md。
# 转换器不选择具体字体，也不调整 Cyrillic 的字体路由。


def escape(text: str) -> str:
    text = text.replace("\\", BACKSLASH_SENTINEL)
    for raw, rep in SPECIALS:
        text = text.replace(raw, rep)
    return text.replace(BACKSLASH_SENTINEL, r"\textbackslash{}")


# 正文里**不是强调**的两种斜体。底本的斜体在这两处是体例，不是强调：
#   署名   `(курсив мой — *Э.И.*)` 伊里因科夫给自己的签名加斜体，那是签名的写法
#   著录   `(*Маркс К.* Grundrisse)` 俄文文献著录格式，落在正文括号里
# 照正文的 \emph 排黑体会变成「强调署名」「强调人名」。脚注那侧靠位置就能区分
# （在脚注里即走 \footnoteemph）；正文里没有位置可依，只能靠形态，故此二式必须窄：
# 署名只有这两种写法，著录要求「姓氏＋空格＋西里尔或拉丁缩写」。
# 判不准的一律留给 \emph——当成强调而其实不是，只是显得重一点；反过来会抹掉原文的信息。
BYLINE = re.compile(r"^(?:Э\.\s*И\.|埃·伊)$")
CITATION = re.compile(r"^[\u4e00-\u9fff]{2,6}\s+(?:[А-ЯЁA-Z]\.){1,3}$")


def is_apparatus(inner: str) -> bool:
    """True 表示这段斜体是署名或行内著录，不是强调。"""
    stripped = inner.strip()
    return bool(BYLINE.match(stripped) or CITATION.match(stripped))


COMMENT = re.compile(r"<!--.*?-->", re.S)
LAYER = re.compile(r"<!--\s*text-layer:")
SEPARATOR = re.compile(r"\A(?:\* \* \*|＊　＊　＊)[ \t]*(?:\n|\Z)")
LIST_ITEM = re.compile(r"\A- +")
IMAGE = re.compile(r"\A!\[[^\]]*\]\((?:[^()]*/)?assets/([^()]+)\)[ \t]*(?:\n|\Z)")
BLOCKQUOTE = re.compile(r"\A> +")
SPEAKER_ONLY = re.compile(r"\A\\bookspeaker\{[^{}]*\}\Z")
HARD_BREAK = re.compile(r"\\\n")


def strong_command(inner: str, speaker: bool, entry: bool) -> str:
    """`**…**` 的目标命令。

    底本粗体在本项目里承担四种功能，判据是**块的结构位置**，不是字面像不像人名：
    速记稿里位于块首、以冒号收尾的是发言人标签；人物志一类词条表里的是词头；
    章末落款走 apparatus；其余一律回落到 \bookstrong，保住底本的强强调属性。
    speaker / entry 由调用方按作品结构开启——不是每本书都有这两种结构。
    """
    stripped = inner.strip()
    if is_apparatus(stripped):
        return r"\bookapparatus{"
    if speaker and stripped.endswith(("：", ":")):
        return r"\bookspeaker{"
    if entry and not stripped.endswith(("：", ":")):
        return r"\bookentry{"
    return r"\bookstrong{"


def convert_styles(text: str, speaker: bool = False, entry: bool = False) -> str:
    """只做样式记号 → 语义命令，不碰脚注。标题与正文共用，标题里的样式才不会漏转。"""
    # 行尾反斜杠是强制换行（诗行）。先占位：escape 会把反斜杠换成 \textbackslash{}。
    text = re.sub(r"\\\n", "\0BREAK\0\n", text)

    strongs: list[str] = []

    def stash_strong(match: re.Match) -> str:
        strongs.append(match.group(1))
        return f"\0STRONG{len(strongs) - 1}\0"

    bolditalics: list[str] = []

    def stash_bolditalic(match: re.Match) -> str:
        bolditalics.append(match.group(1))
        return f"\0BI{len(bolditalics) - 1}\0"

    # 三星号（粗斜体）要先抽：两星号的正则会从它左端咬掉两个星号，剩一个漏在正文里
    text = re.sub(r"\*\*\*(.+?)\*\*\*", stash_bolditalic, text)

    # 先抽双星号：单星号的正则靠前后不是 * 来排除它，先抽走更稳
    text = re.sub(r"\*\*(.+?)\*\*", stash_strong, text)

    emphs: list[str] = []

    def stash_emph(match: re.Match) -> str:
        emphs.append(match.group(1))
        return f"\0EMPH{len(emphs) - 1}\0"

    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", stash_emph, text)

    # 手稿分隔线：下划线个数只表示画了一条线，不表示线长，故先占位再换成定长命令
    text = re.sub(r"_{5,}", "\0RULE\0", text)

    text = escape(text)

    text = text.replace("\0RULE\0", r"\bookinlinerule ")
    text = text.replace("\0BREAK\0", r"\\")

    # 粗斜体：底本兼有粗与斜两层。落在发言人、词头、署名这些结构上时，结构语义已经
    # 固定字面，不再叠斜体；其余按正文强调叠 \bookstrong{\bookemph{}}。
    for i, inner in enumerate(bolditalics):
        command = strong_command(inner, speaker, entry)
        body = escape(inner)
        if command == r"\bookstrong{":
            body = r"\bookemph{" + body + "}"
        text = text.replace(f"\0BI{i}\0", command + body + "}")

    for i, inner in enumerate(strongs):
        text = text.replace(
            f"\0STRONG{i}\0", strong_command(inner, speaker, entry) + escape(inner) + "}"
        )
    for i, inner in enumerate(emphs):
        command = r"\bookapparatus{" if is_apparatus(inner) else r"\bookemph{"
        text = text.replace(f"\0EMPH{i}\0", command + escape(inner) + "}")
    return text


def convert_inline(
    text: str,
    footnotes: dict[str, str],
    report: list[str],
    unresolved: list[str],
    speaker: bool = False,
    entry: bool = False,
) -> str:
    # 先抽出脚注标记，占位，避免正文转义碰到 [^…]
    marks: list[str] = []

    def stash_mark(match: re.Match) -> str:
        marks.append(match.group(1))
        return f"\0MARK{len(marks) - 1}\0"

    text = re.sub(r"\[\^([A-Za-z0-9._-]+)\](?!:)", stash_mark, text)

    text = convert_styles(text, speaker, entry)

    # 还原脚注：把定义就地嵌入
    for i, fid in enumerate(marks):
        body = footnotes.get(fid)
        if body is None:
            unresolved.append(f"本单元中脚注 [^{fid}] 无定义，须核对是否需跨单元或作品级处理")
            replacement = f"[^{fid}]"  # 不完整草稿保留定位记号，正常输出由入口阻止
        else:
            replacement = r"\footnote{" + convert_footnote(body, footnotes, report) + "}"
        text = text.replace(f"\0MARK{i}\0", replacement)
    return text


def convert_footnote(body: str, footnotes: dict[str, str], report: list[str]) -> str:
    """脚注里的强调另走 \footnoteemph。

    脚注斜体可能表示文献著录或引文内强调。转换为独立的语义命令，
    由接收模板依 book/TYPESETTING.md 确定具体视觉实现。
    """
    # 脚注正文自身可能含强调；此处不递归脚注。
    body = body.strip()
    strongs: list[str] = []
    body = re.sub(
        r"\*\*(.+?)\*\*",
        lambda m: strongs.append(m.group(1)) or f"\0S{len(strongs) - 1}\0",
        body,
    )
    emphs: list[str] = []
    body = re.sub(
        r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
        lambda m: emphs.append(m.group(1)) or f"\0E{len(emphs) - 1}\0",
        body,
    )
    body = escape(body)
    for i, inner in enumerate(emphs):
        body = body.replace(f"\0E{i}\0", r"\footnoteemph{" + escape(inner) + "}")
    for i, inner in enumerate(strongs):
        body = body.replace(f"\0S{i}\0", r"\bookstrong{" + escape(inner) + "}")
    # 多段注文以 \0PAR\0 相连（见 split_numeric_notes）
    return body.replace("\0PAR\0", r"\par ")


def parse_footnote_block(text: str) -> dict[str, str]:
    """一个块里的全部脚注定义。

    一个块可以放**多条**：底本的脚注与译者补的 `[^zh-N]` 常并在同一块，因为译注没有
    自己的源块、不能另起锚点。原先用 re.S 一次匹配整块，`.*` 会把后一条定义吃进前一条的
    注文里，后一条于是「无定义」——转换器会报出来（不是静默丢弃），但书里那条译注就没了。
    """
    found: dict[str, str] = {}
    for part in re.split(r"\n(?=\[\^[A-Za-z0-9._-]+\]:)", text):
        match = re.match(r"^\[\^([A-Za-z0-9._-]+)\]:\s*(.*)$", part.strip(), re.S)
        if match:
            found[match.group(1)] = match.group(2).strip()
    return found


NUMERIC_DEF = re.compile(r"\A(\d{1,3}) +(\S.*)\Z", re.S)
# 裸数字注号：前面是空格或收束性标点，后面是空格、标点或块尾，且不接年月、页码等单位字。
# 只按注号顺序逐个找「下一个」号，不做全局匹配，正文里的年份、页码便不会被误认。
NUMERIC_REF_AFTER = r"(?=[\s。，；：！？、”’）」』》…—\\]|\Z)"


def split_numeric_notes(blocks: list[str], report: list[str],
                        unresolved: list[str]) -> tuple[list[str], dict[str, str]]:
    """把文末 `1 注文`、`2 注文`… 的块切出来，返回（正文块，{号: 注文}）。

    注区从最后一个以「1 」起头的块开始，到单元末尾；其间不带号的块是上一条注的续段。
    注号不连续时只报告，不猜。
    """
    start = None
    for i, raw in enumerate(blocks):
        if re.match(r"\A1 +\S", COMMENT.sub("", raw).strip()):
            start = i
    if start is None:
        return blocks, {}
    notes: dict[str, str] = {}
    current = None
    for raw in blocks[start:]:
        text = COMMENT.sub("", raw).strip()
        match = NUMERIC_DEF.match(text)
        if match:
            if current is not None and int(match.group(1)) != int(current) + 1:
                unresolved.append(f"数字注号不连续：{current} 后为 {match.group(1)}；原注区保留，须人工处理")
                return blocks, {}
            current = match.group(1)
            notes[current] = match.group(2).strip()
        elif current is not None and text:
            report.append(f"数字注 {current} 的续段已并入：{text[:20]}…")
            notes[current] += "\0PAR\0" + text
    return blocks[:start], notes


def mark_numeric_refs(blocks: list[str], count: int, unresolved: list[str]) -> list[str]:
    """按 1、2、3… 顺序在正文块里找注号，换成 `[^num-N]`，交给常规脚注流程。

    每个号从上一个号之后往下找；整篇找不到的号只报告、跳过，不让它卡住后面的号。
    """
    out = list(blocks)
    block, pos = 0, 0
    for number in range(1, count + 1):
        pattern = re.compile(
            r"(?:(?<=[\u4e00-\u9fff*）)』」》”’。！？…]) ?| )" + str(number) + r"(?!\d)" + NUMERIC_REF_AFTER
        )
        for i in range(block, len(out)):
            match = pattern.search(out[i], pos if i == block else 0)
            if match:
                mark = f"[^num-{number}]"
                out[i] = out[i][:match.start()] + mark + out[i][match.end():]
                block, pos = i, match.start() + len(mark)
                break
        else:
            unresolved.append(f"数字注 {number}：正文里找不到注号，注文未排入；须作品级人工处理")
    return out


def convert(
    path: Path, speaker_labels: bool = False, entry_headwords: bool = False,
    numeric_notes: bool = False,
) -> tuple[str, list[str], list[str]]:
    report: list[str] = []
    unresolved: list[str] = []
    body_blocks: list[tuple[str, bool, bool]] = []
    footnotes: dict[str, str] = {}
    raw_blocks = blocks_of(path)
    if numeric_notes:
        raw_blocks, numbered = split_numeric_notes(raw_blocks, report, unresolved)
        raw_blocks = mark_numeric_refs(raw_blocks, len(numbered), unresolved)
        footnotes.update({f"num-{k}": v for k, v in numbered.items()})
    for raw in raw_blocks:
        if not raw:
            continue
        # 块里的其余 HTML 注释是结构标记：先读，再剥；留着会被转义成正文字符。
        layered = bool(LAYER.search(raw))
        quoted = raw.lstrip().startswith(">")
        text = COMMENT.sub("", raw).strip()
        if not text:
            continue
        # 一个块可以放**多条**脚注定义：底本的脚注与译者补的 `[^zh-N]` 常并在
        # 同一块，因为译注没有自己的源块、不能另起锚点。
        if text.startswith("[^"):
            footnotes.update(parse_footnote_block(text))
            continue
        body_blocks.append((text, layered, quoted))

    out: list[str] = []
    for text, layered, quoted in body_blocks:
        # 带 text-layer 的块（档案出处、编者说明）与引用块不是发言记录，
        # 其中以冒号收尾的粗体是栏目标签，不是发言人。
        speaker = speaker_labels and not layered and not quoted
        entry = entry_headwords
        stripped = text.strip()
        if stripped.startswith("###") and re.sub(r"^#+\s*", "", stripped) == "注释":
            continue  # 脚注已就地嵌入，不需要单独的「注释」小节
        if text.startswith("#"):
            title = re.sub(r"^#+\s*", "", text).strip()
            # 标题里的脚注只在数字注模式下就地嵌入：别的项目里标题上的 `[^id]` 定义
            # 可能在另一个单元，按正文那套处理会把它吞掉，故保持原样输出。
            if not numeric_notes and re.search(r"\[\^[A-Za-z0-9._-]+\]", title):
                report.append("标题中的脚注标记保留，须在作品 .tex 中处理标题或跨单元注释")
            body = (convert_inline(title, footnotes, report, unresolved, speaker, entry)
                    if numeric_notes else convert_styles(title, speaker, entry))
            out.append(r"\section*{" + body + "}")
            continue
        match = SEPARATOR.match(text)
        if match:
            out.append(r"\bookseparator")
            rest = text[match.end():].strip()
            if rest:
                out.append(convert_inline(rest, footnotes, report, unresolved, speaker, entry))
            continue
        # 图片就地插入；记号里的说明文字不输出（图题另有正文块）
        image = IMAGE.match(text)
        if image:
            out.append(r"\bookfigure{assets/" + image.group(1) + "}")
            rest = text[image.end():].strip()          # 图题与图记号常在同一块
            if rest:
                out.append(convert_inline(rest, footnotes, report, unresolved, speaker, entry))
            continue
        # 结构记号本身不输出，只决定用哪个命令
        wrapper = None
        if HARD_BREAK.search(text):
            # 含强制换行的块是诗行：整块缩进，行首对齐，不另作首行缩进
            wrapper = r"\bookverse{"
        elif LIST_ITEM.match(text):
            wrapper, text = r"\bookitem{", LIST_ITEM.sub("", text)
        elif BLOCKQUOTE.match(text):
            wrapper, text = r"\booknote{", BLOCKQUOTE.sub("", text)
        body = convert_inline(text, footnotes, report, unresolved, speaker, entry)
        if wrapper:
            out.append(wrapper + body + "}")
            continue
        # 只有一个发言人标签的块：标签不能与它的发言分页
        if SPEAKER_ONLY.match(body.strip()):
            out.append(body + r"\par\nopagebreak")
            continue
        out.append(body)
    return "\n\n".join(out) + "\n", report, unresolved


def write_output(path: Path, latex: str) -> None:
    """写完再替换，写入或替换失败时保留原文件。"""
    path = path.resolve()  # 保持原写入行为：已有符号链接写到其目标
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as f:
            temporary = Path(f.name)
            f.write(latex)
        if mode is not None:
            temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_draft(path: Path, input_path: Path, latex: str) -> None:
    target = path.resolve()
    root = Path(__file__).resolve().parents[1]
    protected = [(root / "book" / name).resolve() for name in ("projects", "templates")]
    if not path.name.endswith(".draft.tex"):
        raise ValueError("草稿路径必须以 .draft.tex 结尾")
    if target == input_path.resolve() or any(target.is_relative_to(p) for p in protected):
        raise ValueError("草稿不得写到输入文件或 book/projects、book/templates（含路径别名）")
    if path.exists() or path.is_symlink():
        raise ValueError("草稿路径已存在，拒绝覆盖")
    # 独占创建也防止检查后目标被另一进程建立。
    created = False
    try:
        with path.open("x", encoding="utf-8") as f:
            created = True
            f.write(latex)
    except OSError:
        if created:
            path.unlink(missing_ok=True)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description="译文 Markdown → LaTeX")
    ap.add_argument("input", type=Path, help="译文 .md 文件")
    output = ap.add_mutually_exclusive_group()
    output.add_argument("-o", "--output", type=Path, help="输出 .tex；未解决的转换问题不写入（默认标准输出）")
    output.add_argument("--draft-output", type=Path,
                        help="独占新建 *.draft.tex 草稿，允许待处理问题；退出码仍非零")
    ap.add_argument("--speaker-labels", action="store_true",
                    help="本单元是会议、讨论或速记记录：块首以冒号收尾的 **…** 作发言人标签")
    ap.add_argument("--entry-headwords", action="store_true",
                    help="本单元是人物志或辞典式词条表：不以冒号收尾的 **…** 作词头")
    ap.add_argument("--numeric-notes", action="store_true",
                    help="本单元的注是裸数字注号加文末「N 注文」块：按号配对转成脚注")
    args = ap.parse_args()
    if not args.input.is_file():
        print(f"找不到文件：{args.input}", file=sys.stderr)
        return 2
    latex, report, unresolved = convert(args.input, args.speaker_labels, args.entry_headwords, args.numeric_notes)
    if report:
        sys.stderr.write("\n转换报告（须人核）：\n" + "\n".join("  " + r for r in report) + "\n")
    if unresolved:
        sys.stderr.write("\n转换未完成：\n" + "\n".join("  " + r for r in unresolved) + "\n")
    try:
        if args.draft_output:
            write_draft(args.draft_output, args.input, latex)
            status = "草稿不完整" if unresolved else "草稿已生成，未作正式验收"
            print(f"{status}：{args.draft_output}；须作品级人工处理，退出码为非零", file=sys.stderr)
            return 1
        if unresolved:
            print("未写入正常输出；需要手工处理时请指定独立的 --draft-output", file=sys.stderr)
            return 1
        if args.output:
            write_output(args.output, latex)
        else:
            sys.stdout.write(latex)
    except (OSError, ValueError) as exc:
        print(f"输出未完成：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
