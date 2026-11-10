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
* 连续下划线                    —— 默认按字面输出；--inline-rule 显式确认的完整字符序列转为 \bookinlinerule
* `![说明](assets/…)`           —— \bookfigure{}（就地插入；说明文字不输出）
* `[文字](https://…)`           —— \href{}{}；文字与地址相同时用 \url{}
* `\*` 等 Markdown 转义        —— 对应可见字符，不输出转义反斜杠
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


def blocks_of(path: Path, locations: list[str] | None = None) -> list[str]:
    """按 `<!-- block-id: bNNNNNN -->` 锚点切块；无锚点时按空行分段。"""
    text = path.read_text(encoding="utf-8")
    # 不换行连字符 U+2011 是底本转换留下的技术字符，正文西文字体没有这个字形，
    # 排出来是缺字。它的语言功能就是连字符，按 PUNCTUATION.md 第五节归普通连字符。
    text = text.replace("\u2011", "-")
    front = re.match(r"\A---\r?\n.*?\r?\n---\r?\n", text, re.DOTALL)
    body = text[front.end():] if front else text
    marks = list(re.finditer(r"(?m)^<!-- block-id: b\d{6} -->\s*$", body))
    if marks:
        blocks = [
            body[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(body))].strip()
            for i, m in enumerate(marks)
        ]
    else:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]
    if locations is not None:
        cursor = front.end() if front else 0
        for block in blocks:
            offset = text.find(block, cursor)
            line = text.count("\n", 0, offset) + 1
            anchors = list(re.finditer(r"<!-- block-id: (b\d{6}) -->", text[cursor:offset]))
            anchor = f" ({anchors[-1].group(1)})" if anchors else ""
            locations.append(f"{path}:{line}{anchor}")
            cursor = offset + len(block)
    return blocks


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


def mark_inline_rules(text: str, inline_rules: tuple[str, ...]) -> str:
    """按完整可见序列确认横线；含转义下划线的整段保持字面。"""
    confirmed = set(inline_rules)
    return re.sub(
        r"(?:\\_|_)+|\\[\\`*_{}\[\]()#+\-.!>~]",
        lambda match: "\0RULE\0" if match.group() in confirmed else match.group(),
        text,
    )


def convert_styles(text: str, speaker: bool = False, entry: bool = False,
                   inline_rules: tuple[str, ...] = ()) -> str:
    """只做样式记号 → 语义命令，不碰脚注。标题与正文共用，标题里的样式才不会漏转。"""
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.S | re.I)
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\0HTMLBREAK\0", text, flags=re.I)
    links: list[tuple[str, str]] = []

    def stash_link(match: re.Match) -> str:
        links.append((match.group(1), match.group(2)))
        return f"\0LINK{len(links) - 1}\0"

    text = re.sub(r"(?<!!)\[([^\]\n]+)\]\((https?://[^\s)]+)\)", stash_link, text)

    def stash_autolink(match: re.Match) -> str:
        target = match.group(1)
        links.append((target, target))
        return f"\0LINK{len(links) - 1}\0"

    text = re.sub(r"<((?:https?://|www\.)[^<>\s]+)>", stash_autolink, text)
    def stash_bare_link(match: re.Match) -> str:
        target = match.group(1)
        clean = target.rstrip(".,;:!?)")
        links.append((clean, clean))
        return f"\0LINK{len(links) - 1}\0" + target[len(clean):]

    text = re.sub(r"(?<![A-Za-z0-9/])((?:https?://|www\.)[A-Za-z0-9./_~#?=&%:+–-]+)",
                  stash_bare_link, text)
    text = mark_inline_rules(text, inline_rules)
    literals: list[str] = []

    def stash_literal(match: re.Match) -> str:
        literals.append(match.group(1))
        return f"\0LITERAL{len(literals) - 1}\0"

    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!>~])", stash_literal, text)

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

    text = escape(text)

    text = text.replace("\0HTMLBREAK\0", r"\newline ")
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
    for i, literal in enumerate(literals):
        text = text.replace(f"\0LITERAL{i}\0", escape(literal))
    for i, (label, target) in enumerate(links):
        if label == target:
            link = r"\url{" + target + "}"
        else:
            link = r"\href{" + escape(target) + "}{" + convert_styles(label, inline_rules=inline_rules) + "}"
        text = text.replace(f"\0LINK{i}\0", link)
    # HTML 上下标是通用行内结构；样式转换后保留其内部文字与强调。
    text = re.sub(r"<sup>(.*?)</sup>", lambda m: r"\textsuperscript{" + m.group(1) + "}", text, flags=re.S | re.I)
    text = re.sub(r"<sub>(.*?)</sub>", lambda m: r"\textsubscript{" + m.group(1) + "}", text, flags=re.S | re.I)
    return text.replace("\0RULE\0", r"\bookinlinerule ")


def convert_inline(
    text: str,
    footnotes: dict[str, str | None],
    report: list[str],
    unresolved: list[str],
    speaker: bool = False,
    entry: bool = False,
    seen_refs: dict[str, str] | None = None,
    location: str = "",
    inline_rules: tuple[str, ...] = (),
) -> str:
    if seen_refs is None:
        seen_refs = {}
    # 先抽出脚注标记，占位，避免正文转义碰到 [^…]
    marks: list[tuple[str, int]] = []

    def stash_mark(match: re.Match) -> str:
        marks.append((match.group(1), text.count("\n", 0, match.start())))
        return f"\0MARK{len(marks) - 1}\0"

    text = re.sub(r"\[\^([A-Za-z0-9._-]+)\](?!:)", stash_mark, text)

    text = convert_styles(text, speaker, entry, inline_rules)

    # 还原脚注：把定义就地嵌入
    for i, (fid, line_offset) in enumerate(marks):
        where = f"{location}（块内行 +{line_offset}）"
        body = footnotes.get(fid)
        if fid in seen_refs:
            unresolved.append(f"[待人工确认] {where}: 脚注 [^{fid}] 重复引用；首次引用在 {seen_refs[fid]}，须核对复用注号或作品级处理")
            replacement = f"[^{fid}]"
        elif body is None:
            if fid not in footnotes:
                unresolved.append(f"[阻断错误] {where}: 脚注 [^{fid}] 无定义，须核对是否需跨单元或作品级处理")
            replacement = f"[^{fid}]"  # 缺失或定义有冲突时保留引用，不选择某条注文。
        else:
            replacement = r"\footnote{" + convert_footnote(body, footnotes, report, inline_rules) + "}"
        seen_refs.setdefault(fid, where)
        text = text.replace(f"\0MARK{i}\0", replacement)
    return text


def convert_footnote(body: str, footnotes: dict[str, str | None], report: list[str],
                     inline_rules: tuple[str, ...] = ()) -> str:
    """脚注与正文使用同一套行内语义；附属著录由结构判别。"""
    return convert_styles(body.strip(), inline_rules=inline_rules).replace("\0PAR\0", r"\par ")


def parse_footnote_block(text: str) -> list[tuple[str, str, int]]:
    """按源顺序保留所有定义及其块内行号，重复标识交由汇总环节诊断。"""
    starts = list(re.finditer(r"(?m)^\[\^([A-Za-z0-9._-]+)\]:[ \t]*", text))
    return [
        (match.group(1), text[match.end():starts[i + 1].start()
         if i + 1 < len(starts) else len(text)].strip(),
         text.count("\n", 0, match.start()))
        for i, match in enumerate(starts)
    ]


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
    numeric_notes: bool = False, inline_rules: tuple[str, ...] = (),
) -> tuple[str, list[str], list[str]]:
    report: list[str] = []
    unresolved: list[str] = []
    if any(not re.fullmatch(r"_+", rule) for rule in inline_rules):
        raise ValueError("已确认的横线必须是完整的连续下划线序列")
    body_blocks: list[tuple[str, bool, bool, str]] = []
    footnotes: dict[str, str | None] = {}
    definition_locations: dict[str, str] = {}
    definition_blocks: list[tuple[int, str]] = []
    seen_refs: dict[str, str] = {}
    title_refs: set[str] = set()
    locations: list[str] = []
    raw_blocks = blocks_of(path, locations)
    numeric_source: list[str] = []
    if numeric_notes:
        original_blocks = raw_blocks
        raw_blocks, numbered = split_numeric_notes(raw_blocks, report, unresolved)
        if numbered:
            numeric_source = original_blocks[len(raw_blocks):]
        raw_blocks = mark_numeric_refs(raw_blocks, len(numbered), unresolved)
        footnotes.update({f"num-{k}": v for k, v in numbered.items()})
        for raw, location in zip(original_blocks[len(raw_blocks):], locations[len(raw_blocks):]):
            match = NUMERIC_DEF.match(COMMENT.sub("", raw).strip())
            if match:
                definition_locations[f"num-{match.group(1)}"] = location
    for raw, location in zip(raw_blocks, locations):
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
        if re.match(r"^\[\^[A-Za-z0-9._-]+\]:", text):
            definitions = parse_footnote_block(text)
            definition_blocks.append((len(body_blocks), text))
            for fid, body, offset in definitions:
                where = f"{location}（块内行 +{offset}）"
                if fid in footnotes:
                    unresolved.append(f"[阻断错误] {where}: 脚注 [^{fid}] 重复定义；首次定义在 {definition_locations[fid]}，须人工处理全部定义")
                    footnotes[fid] = None  # 冲突标记；全部定义原文仍按源顺序保留。
                else:
                    footnotes[fid] = body
                    definition_locations[fid] = where
            continue
        body_blocks.append((text, layered, quoted, location))

    out: list[str] = []
    output_positions: list[int] = []
    for text, layered, quoted, location in body_blocks:
        output_positions.append(len(out))
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
                ids = re.findall(r"\[\^([A-Za-z0-9._-]+)\]", title)
                title_refs.update(ids)
                report.append(f"[警告] {location}: 标题中的脚注标记 " +
                              "、".join(f"[^{fid}]" for fid in ids) +
                              " 保留，须在作品 .tex 中处理标题或跨单元注释")
            body = (convert_inline(title, footnotes, report, unresolved, speaker, entry, seen_refs, location, inline_rules)
                    if numeric_notes else convert_styles(title, speaker, entry, inline_rules))
            out.append(r"\section*{" + body + "}")
            continue
        match = SEPARATOR.match(text)
        if match:
            out.append(r"\bookseparator")
            rest = text[match.end():].strip()
            if rest:
                out.append(convert_inline(rest, footnotes, report, unresolved, speaker, entry, seen_refs, location, inline_rules))
            continue
        # 图片就地插入；记号里的说明文字不输出（图题另有正文块）
        image = IMAGE.match(text)
        if image:
            out.append(r"\bookfigure{assets/" + image.group(1) + "}")
            rest = text[image.end():].strip()          # 图题与图记号常在同一块
            if rest:
                out.append(convert_inline(rest, footnotes, report, unresolved, speaker, entry, seen_refs, location, inline_rules))
            continue
        # Markdown 表格：保留行、列与单元格内换行，版式由作品定义。
        table_lines = text.splitlines()
        if (len(table_lines) >= 2 and table_lines[0].lstrip().startswith("|")
                and re.fullmatch(r"[\s|:\-]+", table_lines[1])):
            rows = [[c.strip() for c in line.strip().strip("|").split("|")]
                    for line in table_lines]
            width = len(rows[0])
            if any(len(row) != width for row in rows):
                unresolved.append("表格列数不一致，须核对结构")
                continue
            table = [r"\begin{booktable}{" + str(width) + "}"]
            for row_number, row in enumerate(rows):
                if row_number == 1:
                    continue
                cells = [convert_inline(c, footnotes, report, unresolved, seen_refs=seen_refs, location=location, inline_rules=inline_rules) for c in row]
                if row_number == 0:
                    cells = [r"\bookstrong{" + c + "}" for c in cells]
                table.append(" & ".join(cells) + r" \tabularnewline")
            table.append(r"\end{booktable}")
            out.append("\n".join(table))
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
        body = convert_inline(text, footnotes, report, unresolved, speaker, entry, seen_refs, location, inline_rules)
        if wrapper:
            out.append(wrapper + body + "}")
            continue
        # 只有一个发言人标签的块：标签不能与它的发言分页
        if SPEAKER_ONLY.match(body.strip()):
            out.append(body + r"\par\nopagebreak")
            continue
        out.append(body)
    output_positions.append(len(out))
    unused = footnotes.keys() - seen_refs
    for fid in sorted(unused):
        reason = "仅在标题引用，须作品级排印注文" if fid in title_refs else "未使用定义，须核对跨单元注释或底本结构"
        unresolved.append(f"[待人工确认] {definition_locations[fid]}: 脚注 [^{fid}] {reason}；注文保留在草稿源注释中")
    # 不完整草稿保留全部定义原文及原顺序，便于作品级处理；正常结果不增加注释。
    if unresolved:
        if numeric_source:
            out.append("% 待核对的源数字注释（不作为排印结果）：\n" +
                       "\n".join("% " + line for raw in numeric_source for line in raw.splitlines()))
        for position, text in reversed(definition_blocks):
            comment = "% 待核对的源脚注定义（不作为排印结果）：\n"
            comment += "\n".join("% " + line for line in text.splitlines())
            out.insert(output_positions[position], comment)
    unresolved = [r if r.startswith(("[阻断错误]", "[待人工确认]"))
                  else f"[阻断错误] {path}: {r}" for r in unresolved]
    report = [r if r.startswith(("[警告]", "[待人工确认]")) else f"[提示] {path}: {r}" for r in report]
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
    ap.add_argument("--inline-rule", action="append", default=[], metavar="UNDERSCORES",
                    help="确认本单元内所有未转义的该完整序列均为图形横线；可重复指定。默认按字面输出，同长序列含义混用时在作品 .tex 中定位处理")
    args = ap.parse_args()
    if any(not re.fullmatch(r"_+", rule) for rule in args.inline_rule):
        ap.error("--inline-rule 只接受完整的连续下划线序列")
    if not args.input.is_file():
        print(f"找不到文件：{args.input}", file=sys.stderr)
        return 2
    latex, report, unresolved = convert(args.input, args.speaker_labels, args.entry_headwords, args.numeric_notes, tuple(args.inline_rule))
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
