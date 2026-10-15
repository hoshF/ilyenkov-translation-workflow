#!/usr/bin/env python3
"""DJVU 隐藏文字层重建正文的工具，对应 `digitization/DJVU_TEXT_LAYER_WORKFLOW.md`。

三个子命令分别对应流程的三个需要跑代码的阶段：

    extract   第 1 步。导出逐页纯文本与词级坐标结构，做逐页字符数校验，
              并列出正文图片的候选页。无词级坐标的页按行级文本提取。
    rebuild   第 3、4、6 步。核对底本 SHA-256 后重建单元 Markdown 与 index.md，
              结构校验通过才写入输出目录，另列需人工核对的候选。
    crop      第 7 步。按行内文字定位，裁出该行的页面图像供逐条核对。

判据全部按该页实测的行距中位数与中位字宽取，不含任何按某一份底本调出来的
绝对像素值。书内的具体情形（单元划分、OCR 修正、表格位置）一律由外部 JSON
给入，脚本本身不带任何一本书的数据。

用法：
    python3 scripts/djvu_text_layer.py extract 底本.djvu --out 临时目录
    python3 scripts/djvu_text_layer.py rebuild 临时目录 --units units.json \
        --source 底本.djvu --work-json 作品目录/work.json --out 临时重建目录
    python3 scripts/djvu_text_layer.py crop 底本.djvu --page 115 --find "Слову-" --out 图.png

外部 JSON 的格式见本文件末尾的 SCHEMA 说明。
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- 解析

WORD = re.compile(r'\(word\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"((?:[^"\\]|\\.)*)"\s*\)')
LINE = re.compile(r"\(line\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s")
LINE_TEXT = re.compile(r'"((?:[^"\\]|\\.)*)"')
PAGE = re.compile(r"\(page\s+\d+\s+\d+\s+(\d+)\s+(\d+)")


def _unescape(s: str) -> str:
    """djvutxt 的字符串里用八进制转义 UTF-8 字节。"""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            m = re.match(r"\\([0-7]{1,3})", s[i:])
            if m:
                out.append(int(m.group(1), 8))
                i += len(m.group(0))
                continue
            out.append(s[i + 1])
            i += 2
            continue
        out.append(s[i])
        i += 1
    buf, txt = bytearray(), []
    for o in out:
        if isinstance(o, int):
            buf.append(o)
        else:
            if buf:
                txt.append(buf.decode("utf-8", "replace"))
                buf = bytearray()
            txt.append(o)
    if buf:
        txt.append(buf.decode("utf-8", "replace"))
    return "".join(txt)


def parse_page(path: Path) -> list[dict]:
    """词级结构 → 行列表，按纵坐标自上而下。

    字段分隔必须用 \\s+：djvutxt 会把长行折成多行，按单空格切会静默漏词。

    以 `(word ...)` 为准。个别页的文字层只有 `(line ... "正文")` 而无词级记录，
    这类行按行内文本切词（各词共用该行 bbox），正文不丢；页眉判定用的行首行尾
    词也在其中。整页既无词也无行内文本的，跳过。
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    idx = [m.start() for m in LINE.finditer(raw)] + [len(raw)]
    lines = []
    for i in range(len(idx) - 1):
        chunk = raw[idx[i]:idx[i + 1]]
        lm = LINE.match(chunk)
        words = [(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)),
                  _unescape(m.group(5))) for m in WORD.finditer(chunk)]
        if not words:
            m = LINE_TEXT.search(chunk)
            if not m:
                continue
            x0, y0, x1, y1 = (int(lm.group(k)) for k in (1, 2, 3, 4))
            words = [(x0, y0, x1, y1, t) for t in _unescape(m.group(1)).split()]
            if not words:
                continue
        lines.append({"x0": int(lm.group(1)), "y0": int(lm.group(2)),
                      "x1": int(lm.group(3)), "y1": int(lm.group(4)),
                      "words": words, "text": " ".join(w[4] for w in words)})
    lines.sort(key=lambda l: -l["y1"])
    return lines


def page_height(path: Path) -> int:
    m = PAGE.search(path.read_text(encoding="utf-8", errors="replace")[:200])
    return int(m.group(2)) if m else 0


# ---------------------------------------------------------------- 页码映射

def parse_page_offset(spec) -> list[dict]:
    """印张页码映射 → 段表。

    段内满足 印张页 = 文档页 − offset。无页码的段（照片插页一类）offset 省略或为 null，
    该段不参与页眉判定。省略 first / last 表示开口段。接受：

    - 整数：全书同一偏移；
    - 字符串："3-242:2,243-258:,259-498:18"；
    - 列表：[{"first": 3, "last": 242, "offset": 2}, {"first": 243, "last": 258},
             {"first": 259, "last": 498, "offset": 18}]。
    """
    if spec is None or spec == "":
        return []
    if isinstance(spec, bool):
        raise ValueError("page_offset 不能是布尔值")
    if isinstance(spec, int):
        return [{"first": None, "last": None, "offset": spec}]
    if isinstance(spec, str):
        segs = []
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            rng, _, off = part.partition(":")
            a, b = (rng.split("-", 1) if "-" in rng else (rng, rng))
            segs.append({"first": int(a), "last": int(b),
                         "offset": int(off) if off.strip() else None})
        return segs
    segs = []
    for s in spec:
        off = s.get("offset")
        segs.append({"first": s.get("first"), "last": s.get("last"),
                     "offset": int(off) if off is not None else None})
    return segs


def printed_page(segs: list[dict], n: int) -> int | None:
    """该文档页的印张页码；落在无页码段或段表之外时返回 None。"""
    for s in segs:
        if (s["first"] is None or n >= s["first"]) and (s["last"] is None or n <= s["last"]):
            return None if s["offset"] is None else n - s["offset"]
    return None


def parse_excluded(spec) -> set[int]:
    """不进入正文的文档页 → 页集合。接受 [243, 244] 与 ["243-258"]，可混用。"""
    pages: set[int] = set()
    for item in spec or []:
        s = str(item)
        a, b = (s.split("-", 1) if "-" in s else (s, s))
        pages.update(range(int(a), int(b) + 1))
    return pages


# ---------------------------------------------------------------- 度量

def char_width(l: dict) -> float:
    n = len("".join(w[4] for w in l["words"]))
    return (l["x1"] - l["x0"]) / max(n, 1)


def page_metrics(lines: list[dict]) -> dict:
    """行距中位数、中位字宽、左右界。本步一切阈值以前两者为单位。"""
    if not lines:
        return {"med_gap": 0.0, "med_cw": 0.0, "left": 0, "right": 0}
    gaps = [lines[i - 1]["y1"] - lines[i]["y1"] for i in range(1, len(lines))]
    med_gap = statistics.median(gaps) if gaps else 0.0
    x1s = sorted(l["x1"] for l in lines)
    right = x1s[int(len(x1s) * 0.80)]
    xs = sorted(l["x0"] for l in lines)
    left = xs[int(len(xs) * 0.20)]
    cw = [char_width(l) for l in lines if l["x1"] > right - 150]
    med_cw = statistics.median(cw) if cw else statistics.median(char_width(l) for l in lines)
    full = [char_width(l) for l in lines if l["x1"] > right - 2 * med_cw]
    if full:
        med_cw = statistics.median(full)
    return {"med_gap": round(med_gap, 1), "med_cw": round(med_cw, 1), "left": left, "right": right}


def clusters(values: list[int], tol: float) -> list[list[int]]:
    """一维聚类：相邻值之差小于 tol 的并作一簇。"""
    out: list[list[int]] = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return out


# ---------------------------------------------------------------- 版面判定

FN_GAP, FN_CW = 1.35, 0.93          # 页下注区：空档倍数、字宽比（多信号之一）
NOTE_START = re.compile(r"^\s*(?:\*{1,5}\s|(?:\d{1,3}|[IVXLC]{1,6})[.)]\s)")
# 行首星号是页下注的强证据；OCR 常把星号认成 ^ \ ` ' 一类小符号，或吃掉星号后的空格
MARK_STAR = re.compile(r"^\s*\*{1,5}")                      # 行首真星号：最强证据
MARK_ODD = re.compile(r"^\s*[\^\\`'|•·~\"]{1,3}\s?")      # 星号被认成 ^ \ ` ' | • · ~ " 的误形
# 悬挂缩进条目：左界上以注号／编号起首的行（尾注区、编号注一类）
LIST_MARK = re.compile(r"^(?:\d{1,3}\.|\d{1,2}\)|[1-9]|[IVXLC]{1,6}[.)]?)\s+[А-ЯЁA-Z]")
NOTE_MARK_STRIP = re.compile(r"^(?:\*{1,5}\s*|[\^\\`'|]{1,2}\s+)")  # 注文首部的注标不留进正文
HEAD_GAP, HEAD_CW = 1.4, 1.10       # 标题：上下空档倍数、字号倍数


class Book:
    """一册底本的导出目录。逐页解析结果与修正结果都在这里缓存。"""

    def __init__(self, work: Path, page_offset: list[dict] | None = None,
                 fixes: list | None = None, normalize: str | None = None,
                 excluded: set[int] | None = None):
        self.dir = work
        self.page_offset = page_offset or parse_page_offset(0)
        self.excluded = excluded or set()
        self.fixes = fixes or []
        self.normalize = normalize
        self.indent = 0.0
        self._cache: dict[int, dict] = {}
        self._inline_hyphen: set[tuple[str, str]] | None = None
        self.height = 0
        self.missing: set[int] = set()
        self.excluded_hit: set[int] = set()

    # -- OCR 修正 -------------------------------------------------
    def apply(self, s: str, scope: str, log: dict) -> str:
        if self.normalize == "ru":
            s = normalize_ru(s, log)
        for r in self.fixes:
            if r.get("scope", "line") != scope:
                continue
            pat = re.escape(r["pattern"]) if r.get("literal") else r["pattern"]
            s2, n = re.subn(pat, r["replace"], s, flags=re.M)
            if n:
                log[r.get("label", r["pattern"])] = log.get(r.get("label", r["pattern"]), 0) + n
                s = s2
        return s

    # -- 单页 -----------------------------------------------------
    def _odd_first_line(self, lines: list[dict], m: dict, n: int) -> bool:
        """页首首行 x0 异常右移：OCR 吃掉行首词留下的痕迹。

        判据：x0 超出段首缩进、在本页只此一处、行占满满版心且不越出右界，
        且上一页末行也是满行。命中即把该行 x0 归到左界，按续行处理。
        """
        l = lines[0]
        if l["x0"] <= m["left"] + (self.indent or 90):
            return False
        if any(abs(o["x0"] - l["x0"]) <= m["med_cw"] for o in lines[1:]):
            return False
        if not (m["right"] - 2 * m["med_cw"] < l["x1"] <= m["right"] + m["med_cw"]):
            return False
        f = self.dir / "word" / f"{n - 1:03d}.txt"
        if n <= 1 or not f.exists():
            return False
        plines = parse_page(f)
        if not plines:
            return False
        pm = page_metrics(plines)
        return plines[-1]["x1"] > pm["right"] - 2 * pm["med_cw"]

    def page(self, n: int) -> dict:
        if n in self._cache:
            return self._cache[n]
        f = self.dir / "word" / f"{n:03d}.txt"
        if n in self.excluded:
            # 不属正文的页（无页码照片插页、扉页一类），只登记不进正文
            self.excluded_hit.add(n)
            lines = []
        elif f.exists():
            lines = parse_page(f)
            if not self.height:
                self.height = page_height(f)
        else:
            # 无文字层的页（封面、空白页）没有导出文件，不参与正文
            lines = []
            self.missing.add(n)
        for l in lines:
            l["text"] = self.apply(l["text"], "line", self.log)
        header = None
        printed = printed_page(self.page_offset, n)
        if printed is not None and lines and self.height and lines[0]["y1"] > 0.93 * self.height:
            ws = [w[4] for w in lines[0]["words"]]
            if ws and (ws[0] == str(printed) or ws[-1] == str(printed)):
                header = lines.pop(0)
        m = page_metrics(lines)
        if lines and self._odd_first_line(lines, m, n):
            lines[0] = dict(lines[0], x0=m["left"])
            m = page_metrics(lines)
        body, notes = self._split_footnotes(lines, m)
        m = page_metrics(body) if body else m
        rec = {"n": n, "body": body, "notes": notes, "header": header, **m}
        rec["clusters"] = self._indent_clusters(body, m)
        rec["indent"] = self.indent
        self._cache[n] = rec
        return rec

    def measure(self, pages: range | list) -> None:
        """全书量一次段首缩进：各行 x0 与该页左界之差的主簇。"""
        offs, cw = [], []
        for n in pages:
            r = self.page(n)
            if not r["clusters"] or not r["med_cw"]:
                continue
            base = base_cluster(r["clusters"], len(r["body"]))[-1]
            cw.append(r["med_cw"])
            offs += [l["x0"] - base for l in r["body"]]
        if not offs:
            return
        unit = statistics.median(cw)
        pos = [o for o in offs if unit * 0.6 < o < unit * 8]
        if not pos:
            return
        cl = clusters(pos, unit)
        self.indent = statistics.median(max(cl, key=len))
        for r in self._cache.values():
            r["indent"] = self.indent

    def _split_footnotes(self, lines: list[dict], m: dict) -> tuple[list[dict], list[dict]]:
        """页下注区判定：多信号合议。

        自底向上取第一个大空档，其下须同时满足——末行贴近下沿；行首多半与正文左界
        齐（排除居中诗行、内缩引文块）；中位字宽小于正文满行；且页内确有注标证据
        （正文里的注标，或注区行首的注标）。任一条不成立即当作正文：书目、索引、
        Хроника、作者名录一类页末块也可能成行更窄、字号更小，不能只看字号与位置。
        """
        if not lines or not m["med_gap"] or not self.height:
            return lines, []
        body_stars = len(MARKER.findall(" ".join(l["text"] for l in lines)))
        for i in range(len(lines) - 1, 0, -1):
            if lines[i - 1]["y1"] - lines[i]["y1"] <= FN_GAP * m["med_gap"]:
                continue
            cand, rest = lines[i:], lines[:i]
            full = [l for l in rest if l["x1"] > m["right"] - 2 * m["med_cw"]]
            if len(full) < 3 or cand[-1]["y1"] >= 0.13 * self.height:
                break
            # 整块整体内缩、离正文左界很远的，是诗行、题词一类，不是页下注
            if min(l["x0"] for l in cand) > m["left"] + 3 * (self.indent or 90):
                break
            # 注区证据：真星号，或内缩位置上的误形星号（引号起的续行不算）
            area_stars = any(MARK_STAR.match(l["text"])
                             or (MARK_ODD.match(l["text"])
                                 and l["x0"] > m["left"] + 0.3 * (self.indent or 90))
                             for l in cand)
            smaller = (statistics.median([char_width(l) for l in cand])
                       < FN_CW * statistics.median([char_width(l) for l in full]))
            # 注区行首星号是强证据，字号不论；只凭字号这一条时，还须正文里确有星号注标，
            # 否则«Примечания»、书目、作者名录一类小字正文小节会被误当页下注。
            if not (area_stars or (body_stars and smaller)):
                break
            return rest, cand
        return lines, []

    @staticmethod
    def _indent_clusters(body: list[dict], m: dict) -> list[list[int]]:
        """该页各行 x0 的簇。行数最多的是左界，右邻的是段首缩进，更右的是内缩块。"""
        if not body or not m["med_cw"]:
            return []
        return clusters([l["x0"] for l in body], m["med_cw"])

    log: dict = {}


BLOCK_GAP, MERGE_GAP, HEAD_MIN = 1.4, 2.0, 1.05

MONTH = r"(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)"
SALUTE = r"(?:Дорог\w+|Уважаем\w+|Мил\w+)"
SALUTE_START = re.compile(r"^[^0-9A-Za-zА-Яа-яЁё]{0,3}(" + SALUTE + r"\s+[^!]{0,45}!)")
DATE_FORMS = (
    r"\d{1,2}[/.\s-][IVXLC]{1,5}[.\s-]?\d{2,4}\s*(?:г\.)?",
    r"(?:[IVXLC]{1,5}\s+)?\d{1,2}[а-яё]*\.?\s*\d{4}\s*(?:г\.)?",
    r"\d{1,2}\s+" + MONTH + r"\w*\s+\d{4}\s*(?:г\.)?",
    MONTH + r"\w*\s+\d{4}\s*(?:г\.)?",
    r"\d{4}\s*(?:г\.|год|года|гг\.)",
)


def is_standalone_line(t: str) -> bool:
    """整行是一个日期（可带地点）或一个称呼——段落级排版，须自成一个块。

    只认整行成立的形式：地名可选，其余由日、月、年、`г.` 与数字构成，
    正文里带年份的句子不在此列。
    """
    s = t.strip().rstrip("*").strip()
    if not s or len(s) > 60 or len(s.split()) > 7:
        return False
    if SALUTE_START.fullmatch(s):
        return True
    body = re.sub(r"^[А-ЯЁ][а-яё-]+,\s*", "", s)
    if not re.search(r"\d", body):
        return False
    for pat in DATE_FORMS:
        if re.fullmatch(r"\s*" + pat + r"\s*", body, re.I):
            return True
    return bool(re.fullmatch(r"[\d\s.,/IVXLC]+", body, re.I) and re.search(r"\d{2}", body))


def split_salutation(t: str) -> list[str]:
    """与后续正文同行的称呼拆成独立一块。"""
    m = SALUTE_START.match(t)
    if not m:
        return [t]
    rest = t[m.end():].strip()
    return [m.group(1), rest] if rest else [t]


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def opener_match(t: str, keys: list[str]) -> bool:
    """篇首页面上的目录信息行：与所录题名／署名／部题同一。容忍 OCR 形近字母与缩写差异。"""
    nt = _norm(t)
    if not nt:
        return False
    for k in keys:
        if not k:
            continue
        if nt == k:
            return True
        if len(nt) >= 6 and (nt in k or k in nt) and min(len(nt), len(k)) >= 0.6 * max(len(nt), len(k)):
            return True
        if _sim(nt, k) >= 0.85:
            return True
    return False


def base_cluster(cls: list[list[int]], n: int) -> list[int]:
    """左界簇＝最靠左的成片簇。不能取最大簇：一页大半是单行缩进条目时最大簇是缩进簇。"""
    if not cls:
        return []
    for c in cls:
        if len(c) >= max(2, 0.15 * n):
            return c
    return max(cls, key=len)


def _classify(body: list[dict], cls: list[list[int]], m: dict, ind: float) -> dict[int, str]:
    """按 x0 相对左界的偏移给每行定性：正文续行 / 段首缩进 / 内缩块。

    缩进量须按全书量（`Book.measure`）。只看一页会出错：一页上可能根本没有
    段首缩进行，那时最靠右的簇（题词一类）会被误当成段首缩进。
    """
    if not cls:
        return {}
    base = base_cluster(cls, len(body))[-1]
    kind = {}
    for l in body:
        off = l["x0"] - base
        kind[id(l)] = "body" if off < ind * 0.5 else ("indent" if off < ind * 1.75 else "block")
    return kind


def page_blocks(rec: dict) -> list[dict]:
    """一页切成 head / para / quote 三种块。"""
    body, m = rec["body"], rec
    if not body:
        return []
    mg, cw, right = m["med_gap"] or 100.0, m["med_cw"] or 45.0, m["right"]
    kind = _classify(body, rec["clusters"], m, rec["indent"])

    runs, cur = [], [body[0]]
    for i in range(1, len(body)):
        if body[i - 1]["y1"] - body[i]["y1"] > BLOCK_GAP * mg:
            runs.append(cur)
            cur = []
        cur.append(body[i])
    runs.append(cur)

    def cand(run):
        short = sum(1 for l in run if l["x1"] < right - 2 * cw)
        return short * 2 >= len(run) and all(char_width(l) >= HEAD_MIN * cw for l in run)

    merged, i = [], 0
    while i < len(runs):
        run = list(runs[i])
        while (cand(run) and i + 1 < len(runs) and cand(runs[i + 1])
               and run[-1]["y1"] - runs[i + 1][0]["y1"] <= MERGE_GAP * mg):
            i += 1
            run += runs[i]
        merged.append(run)
        i += 1

    out = []
    for run in merged:
        plain = " ".join(l["text"] for l in run)
        if len(run) == 1 and re.fullmatch(r"[IVXLC]{1,7}", plain.strip()):
            out.append({"kind": "head", "lines": run})       # 罗马数字单行＝节标题
            continue
        if (cand(run) and any(char_width(l) >= HEAD_CW * cw for l in run)
                and re.search(r"[0-9A-Za-zА-Яа-яЁё]", plain)):
            out.append({"kind": "head", "lines": run})       # 纯标点（* * * 一类分隔行）不作标题
            continue
        brk = False
        hanging = False
        for l in run:
            k = kind.get(id(l), "body")
            if k == "block":
                if out and out[-1]["kind"] == "quote":
                    pv = out[-1]["lines"][-1]
                    if abs(l["x0"] - pv["x0"]) <= cw / 2 or abs(l["x1"] - pv["x1"]) <= cw / 2:
                        out[-1]["lines"].append(l)
                        continue
                out.append({"kind": "quote", "lines": [l]})
                hanging = False
            else:
                alone = is_standalone_line(l["text"])
                mark = bool(k == "body" and LIST_MARK.match(l["text"]))
                # 悬挂条目起首（左界上的编号行）另起一段；其缩进续行并入该条，不再另起
                if (alone or mark or (k == "indent" and not hanging)
                        or not out or brk or out[-1]["kind"] != "para"):
                    out.append({"kind": "para", "lines": [l]})
                else:
                    out[-1]["lines"].append(l)
                hanging = mark or (hanging and not alone)
                brk = alone
    return out


def split_columns(body: list[dict], m: dict) -> list[list[dict]] | None:
    """簇远离其余各簇、两侧各自成片时为双栏。返回左右两栏。"""
    cls = clusters([l["x0"] for l in body], m["med_cw"]) if m["med_cw"] else []
    if len(cls) < 2:
        return None
    gaps = [(cls[i][0] - cls[i - 1][-1], cls[i][0]) for i in range(1, len(cls))]
    width, cut = max(gaps)
    if width < 20 * m["med_cw"]:
        return None
    lft = [l for l in body if l["x0"] < cut]
    rgt = [l for l in body if l["x0"] >= cut]
    return [lft, rgt] if len(lft) >= 10 and len(rgt) >= 10 else None


def hanging_blocks(col: list[dict], m: dict) -> list[dict]:
    """悬挂缩进的栏：贴栏左界的是条目起始，缩进的是续行。"""
    cls = clusters([l["x0"] for l in col], m["med_cw"])
    base = base_cluster(cls, len(col))
    out = []
    for l in col:
        if l["x0"] > base[-1] and out:
            out[-1]["lines"].append(l)
        else:
            out.append({"kind": "para", "lines": [l]})
    return out


# ---------------------------------------------------------------- 语种通则

L2C = {"A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О",
       "P": "Р", "T": "Т", "X": "Х", "Y": "У", "R": "Р", "N": "И"}
G2C = {"Α": "А", "Β": "В", "Ε": "Е", "Η": "Н", "Κ": "К", "Μ": "М", "Ν": "Н", "Ο": "О",
       "Ρ": "Р", "Τ": "Т", "Χ": "Х", "Φ": "Ф", "Γ": "Г"}
G2L = {"Α": "A", "Β": "B", "Ε": "E", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N",
       "Ο": "O", "Ρ": "P", "Τ": "T", "Χ": "X", "Φ": "F", "Γ": "G"}
NONCYR = {**L2C, **G2C}


def normalize_ru(s: str, log: dict) -> str:
    """俄文的通则性 OCR 修正：整词认错字母表的缩写、缩写周围丢掉的空格。

    OCR 不在词内混排字母表，而是整个 token 认错（用拉丁 M. 代西里尔 М.），
    所以查「词内混排」查不出来，必须按上下文的文种判。
    """
    def bump(k: str) -> None:
        log[k] = log.get(k, 0) + 1

    def to_cyr(m):
        bump("缩写字母转西里尔")
        return NONCYR.get(m.group(1), m.group(1)) + m.group(2)

    cls = "[" + "".join(NONCYR) + "]"
    for _ in range(3):                                   # 连续缩写要反复扫过
        s = re.sub(r"\b(%s)(\.\s*[А-ЯЁ]\.)" % cls, to_cyr, s)
        s = re.sub(r"\b(%s)(\.\s*[А-ЯЁ][а-яё]{2,})" % cls, to_cyr, s)
    s = re.sub(r"([А-ЯЁ][а-яё]{2,})\s+(%s)\." % cls,
               lambda m: (bump("姓后缩写转西里尔") or m.group(1) + " " + NONCYR[m.group(2)] + "."), s)
    s = re.sub(r"(?<=[A-Za-z])\s+([%s])\." % "".join(G2L),
               lambda m: (bump("希腊字母转拉丁") or " " + G2L[m.group(1)] + "."), s)
    for pat, rep, tag in (
            (r"(?<=[А-ЯЁ])\.([А-ЯЁ])\.", r". \1.", "缩写点后补空格"),
            (r"(?<=[А-ЯЁ])\.(?=[А-ЯЁ][а-яё])", ". ", "缩写与姓之间补空格"),
            (r"([а-яё]{2})([А-ЯЁ])\.(?=\s|$|[А-ЯЁ])", r"\1 \2.", "姓与缩写之间补空格")):
        s2, n = re.subn(pat, rep, s)
        if n:
            log[tag] = log.get(tag, 0) + n
            s = s2
    return s


# ---------------------------------------------------------------- 断词接合

ORTHO = re.compile(r"^(то|либо|нибудь|таки)$", re.I)


def inline_hyphens(work: Path) -> set[tuple[str, str]]:
    """全书行内出现过的带连字符写法，供接合时查。"""
    seen = set()
    for f in sorted((work / "txt").glob("*.txt")):
        for m in re.finditer(r"(\w+)-(\w+)", f.read_text(encoding="utf-8"), re.UNICODE):
            seen.add((m.group(1).lower(), m.group(2).lower()))
    return seen


BREAK_TAIL = "-\u00ac"          # 行末断词的连接符：连字符，以及文字层用 ¬ 表示的那种


def ends_break(s: str) -> bool:
    """该串以行末断词的连接符结尾。"""
    return bool(s) and s[-1] in BREAK_TAIL


def join_hyphen(a: str, b: str, seen: set, keep: dict[tuple[str, str], str]) -> str:
    """a 以行末断词连接符（`-` 或 `¬`）结尾。默认去掉连接符接合，例外则保留连字符。"""
    mark = a[-1]
    head = a[:-1]
    lw = re.search(r"(\w+)$", head, re.UNICODE)
    rw = re.match(r"(\w+)", b, re.UNICODE)
    if lw and rw:
        l, r = lw.group(1).lower(), rw.group(1).lower()
        if (l, r) in keep:                       # 经页面图像确认的，按给定字符接
            return head + keep[(l, r)] + b
        if (l, r) in seen or ORTHO.match(r):
            return head + "-" + b                # 保留连字符；连接符一律归为 `-`
        if l[-1:].isdigit() and r[:1].isdigit():
            return head + "-" + b
    return head + b


def block_text(block: dict, seen: set, keep: dict, metrics: dict | None = None) -> str:
    """块内各行接成一段；诗行、题署一类保留换行。

    内缩块按散文合并的条件：各行 x0 齐平；除末行外右端都抵同一右界；整块占满版心宽度。
    右对齐署名、题署、诗行的右端参差或只占版心一窄条，保留换行。
    """
    lines = block["lines"]
    if block["kind"] == "quote" and len(lines) > 1:
        xs = [l["x0"] for l in lines]
        x1s = [l["x1"] for l in lines]
        cw = statistics.median([(l["x1"] - l["x0"]) / max(len(l["text"].strip()), 1) for l in lines])
        full = x1s[:-1]
        text_width = (metrics or {}).get("right", 0) - (metrics or {}).get("left", 0)
        wide = text_width <= 0 or (max(x1s) - min(xs)) >= 0.6 * text_width
        prose = (max(xs) - min(xs) <= 60 and full and max(full) - min(full) <= 60
                 and min(full) >= max(x1s) - 3 * cw and wide)
        if not prose:
            return "\n".join(l["text"].strip() for l in lines)
    txt = ""
    for k, l in enumerate(lines):
        t = l["text"].strip()
        txt = t if k == 0 else (join_hyphen(txt, t, seen, keep) if ends_break(txt) else txt + " " + t)
    return re.sub(r"\s+", " ", txt).strip()


# ---------------------------------------------------------------- 注释

MARKER = re.compile(r"(?<![\s*])[*]{1,5}")


def note_start(l: dict, rec: dict) -> bool:
    """该行是否为新注起首：星号或编号注标直接算；误形注标须内缩；其余看是否超过内缩界。"""
    ind = rec["indent"] or 90
    if MARK_STAR.match(l["text"]) or NOTE_START.match(l["text"]):
        return True
    if MARK_ODD.match(l["text"]) and l["x0"] > rec["left"] + 0.3 * ind:
        return True
    return l["x0"] > rec["left"] + 1.2 * ind


def page_notes(rec: dict, seen: set, keep: dict) -> tuple[bool, list[str]]:
    """注区切条：注标起首或明显内缩的行开新条，无新注标的后续行并入当前条。

    页内正文注标数作约束：候选界多于注标数时，先并掉既未内缩、行首也无注标的弱界；
    仍多则从末界起并。注标缺失、界数定不下来时不猜，交由上层记入待核验。
    """
    notes = rec["notes"]
    if not notes:
        return False, []
    base, ind = rec["left"], rec["indent"] or 90
    cut = base + 1.2 * ind                 # 注区内：过此即视为新条起首
    cont_cut = base + rec["med_cw"]        # 条首贴着正文左界的，是上一页末条的续排
    marks = len(MARKER.findall(" ".join(l["text"] for l in rec["body"])))
    cont = (notes[0]["x0"] <= cont_cut and not note_start(notes[0], rec))
    starts = [i for i, l in enumerate(notes) if i == 0 or note_start(l, rec)]
    # 首条若为上一页末条的续排，上层会把它并回去，故页内条数上限是注标数加它
    target = marks + (1 if cont else 0) if marks else 0
    if target:
        def weak(i: int) -> int:
            """越小越先并掉：未内缩、又无注标的界最不可靠。首界不参与并。"""
            return (2 if notes[i]["x0"] > cut else 0) + (1 if note_start(notes[i], rec) else 0)
        while len(starts) > target and len(starts) > 1:
            starts.remove(min(starts[1:], key=weak))
        while len(starts) > target:
            starts.pop()
    paras: list[dict] = []
    for i, l in enumerate(notes):
        if i in starts:
            paras.append({"kind": "para", "lines": [l]})
        else:
            paras[-1]["lines"].append(l)
    out = []
    for p in paras:
        t = block_text(p, seen, keep).strip()
        if t:
            out.append(t)
    # 一行里挤进下一条注（行内出现下一个注标）时再切，且只在条数不足、切完不超数时
    if marks and len(out) < marks:
        more = [x.strip() for t in out for x in re.split(r"\s+(?=\*{1,5}\s)", t) if x.strip()]
        if len(more) <= marks:
            out = more
    return cont, out


# ---------------------------------------------------------------- 表格

def _rows_by_y(cells: list[dict], tol: int = 12) -> list[list[dict]]:
    rows, cur = [], []
    for l in sorted(cells, key=lambda c: -c["y1"]):
        if cur and abs(cur[-1]["y1"] - l["y1"]) > tol:
            rows.append(cur)
            cur = []
        cur.append(l)
    if cur:
        rows.append(cur)
    return rows


def build_table(book: "Book", spec: dict) -> list[list[str]]:
    """按坐标重建表格：最宽的一行定栏，必填栏定行，其余单元格就近归行。"""
    ncol = len(spec["header"])
    out: list[list[str]] = []
    for reg in spec["regions"]:
        cells = [l for l in book.page(reg["page"])["body"] if l["y1"] <= reg["rows_below"]]
        if not cells:
            continue
        widest = max(_rows_by_y(cells), key=len)
        cols = sorted((c["x0"] + c["x1"]) / 2 for c in widest)
        if len(cols) != ncol:
            sys.exit(f"表格定栏失败：P{reg['page']} 最宽行有 {len(cols)} 格，表头有 {ncol} 栏")
        bounds = [(cols[i] + cols[i + 1]) / 2 for i in range(ncol - 1)]
        col_of = lambda c: min(range(ncol), key=lambda i: abs(cols[i] - (c["x0"] + c["x1"]) / 2))
        crosses = lambda c: sum(1 for b in bounds if c["x0"] < b < c["x1"])
        # 各栏依次为 1..N 的一行是续页的栏号行，属分页排印装置
        for row in _rows_by_y(cells):
            if len(row) == ncol and [c["text"].strip() for c in sorted(row, key=lambda c: c["x0"])] \
                    == [str(i + 1) for i in range(ncol)]:
                drop = {id(c) for c in row}
                cells = [c for c in cells if id(c) not in drop]
        grid = [c for c in cells if crosses(c) < 2]          # 跨两条栏界以上的是跨栏行
        loose = [c for c in cells if crosses(c) >= 2]
        anchor_col = spec.get("row_column")
        if anchor_col is None:
            anchor_col = max(range(ncol), key=lambda i: sum(1 for c in grid if col_of(c) == i))
        anchors = sorted({c["y1"] for c in grid if col_of(c) == anchor_col}, reverse=True)
        buckets = {a: [""] * ncol for a in anchors}
        for c in grid:
            if not anchors:
                loose.append(c)
                continue
            a = min(anchors, key=lambda y: abs(y - c["y1"]))
            if abs(a - c["y1"]) > 95:
                loose.append(c)
                continue
            i = col_of(c)
            buckets[a][i] = (buckets[a][i] + " " + c["text"].strip()).strip()
        bands, band = [], []
        for l in sorted(loose, key=lambda x: -x["y1"]):
            if band and band[-1]["y1"] - l["y1"] <= 110:
                band.append(l)
            else:
                if band:
                    bands.append(band)
                band = [l]
        if band:
            bands.append(band)
        rows = [(b[0]["y1"], ["**" + " ".join(x["text"].strip() for x in b) + "**"] + [""] * (ncol - 1))
                for b in bands]
        rows += [(a, [spec.get("cell_fixes", {}).get(v, v) for v in buckets[a]]) for a in anchors]
        out += [r for _, r in sorted(rows, key=lambda r: -r[0])]
    return out


def table_markdown(rows: list[list[str]], header: list[str]) -> str:
    md = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(md)


# ---------------------------------------------------------------- 单元重建

LOOKALIKE = str.maketrans({
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О",
    "P": "Р", "T": "Т", "X": "Х", "Y": "У", "a": "а", "c": "с", "e": "е", "o": "о",
    "p": "р", "x": "х", "y": "у", "Α": "А", "Β": "В", "Ε": "Е", "Η": "Н", "Κ": "К",
    "Μ": "М", "Ν": "Н", "Ο": "О", "Ρ": "Р", "Τ": "Т", "Χ": "Х", "Φ": "Ф", "Γ": "Г"})


def _norm(s: str) -> str:
    """比对篇名署名用：去掉脚注引用，只留字母，并把形近的异文种字母折回。"""
    s = re.sub(r"\[\^[^\]]+\]", "", s).translate(LOOKALIKE).lower()
    return "".join(ch for ch in s if ch.isalpha())


def build_unit(book: "Book", u: dict, seen: set, keep: dict, tables: dict,
               issues: list, section: str | None = None, figures: list | None = None
               ) -> tuple[list[tuple[str, str]], list[str], dict, int]:
    """单元正文。篇首页面上的题名、署名、部题已由 `# 题名` 与署名行代表，不重复进正文。

    返回块表、注释、标题／署名上的注标、以及被抑制的篇首行字符数（供字符守恒校验扣除）。
    """
    blocks: list[tuple[str, str]] = []
    notes: list[str] = []
    head_refs = {"title": "", "author": ""}
    dropped = 0
    fig_at: list[tuple[int, list]] = []          # 插图插在本页末尾的块边界，整单元建完再落位
    opener_keys = [k for k in (_norm(u["title"]), _norm(u.get("author") or ""),
                               _norm(section or "")) if k]
    akey = _norm(u.get("author") or "\0")
    seq = 0
    for n in range(u["first"], u["last"] + 1):
        rec = book.page(n)
        cont, nts = page_notes(rec, seen, keep)
        if cont and nts and notes:
            notes[-1] += " " + nts[0]
            nts = nts[1:]
        def markable(t: str) -> bool:
            """只有含字母数字的行才可能带注标；`* * *` 一类分隔行不算。"""
            return bool(re.search(r"[0-9A-Za-zА-Яа-яЁё]", t))

        body_txt = " ".join(l["text"] for l in rec["body"] if markable(l["text"]))
        marks = list(MARKER.finditer(body_txt))
        if nts and len(marks) == len(nts):
            ids = []
            for t in nts:
                seq += 1
                ids.append(f"{u['unit']}-{seq:03d}")
                notes.append(NOTE_MARK_STRIP.sub("", t))
            k = [0]

            def rep(m, ids=ids, k=k):
                i = k[0]
                k[0] += 1
                return f"[^{ids[i]}]" if i < len(ids) else m.group(0)
            for l in rec["body"]:
                if markable(l["text"]):
                    l["text"] = MARKER.sub(rep, l["text"])
        elif nts or marks:
            # 注标与注释条数不符：注标原样留在正文，注释文字也并回本页正文末尾，
            # 不生成无引用的定义（该页记入 issues，按流程写入 source-issues.json）
            rec["body"] = rec["body"] + rec["notes"]
            rec["notes"] = []
            issues.append({"page": n, "marks": len(marks), "notes": len(nts)})

        tb = tables.get(str(n))
        skip = {int(r["page"]): r["table_below"] for t in tables.values() for r in t["regions"]}
        groups = page_blocks(rec)
        if n in skip:
            groups = [g for g in groups if all(l["y1"] > skip[n] for l in g["lines"])]
        cols = split_columns(rec["body"], rec) if not rec["notes"] else None
        if cols:
            top = min(cols[0][0]["y1"], cols[1][0]["y1"]) + 150
            groups = [{"kind": "head", "lines": [l]} for l in rec["body"] if l["y1"] > top]
            done = {id(l) for g in groups for l in g["lines"]}
            for c in cols:
                groups += hanging_blocks([l for l in c if id(l) not in done], rec)
        for gi, g in enumerate(groups):
            t = book.apply(block_text(g, seen, keep, rec), "block", book.log)
            if not blocks and opener_match(t, opener_keys):
                r = "".join(re.findall(r"\[\^[^\]]+\]", t))
                if r:
                    head_refs["author" if _sim(_norm(t), akey) > _sim(_norm(t), opener_keys[0]) else "title"] += r
                dropped += sum(1 for c in re.sub(r"\[\^[^\]]+\]", "", t) if c.isalnum())
                continue
            if g["kind"] == "head":
                blocks.append(("head", t))
            elif (blocks and blocks[-1][0] in ("para", "quote") and gi == 0
                  and g["kind"] == blocks[-1][0] and rec["clusters"]
                  and g["lines"][0]["x0"] <= base_cluster(rec["clusters"], len(rec["body"]))[-1]):
                prev = blocks[-1][1]
                merged = (join_hyphen(prev, t, seen, keep) if ends_break(prev) else prev + " " + t)
                # 接合会造出跨行/跨页的新词形，block 级修正须在接合后的文本上再走一遍
                blocks[-1] = (blocks[-1][0], book.apply(merged, "block", book.log))
            else:
                blocks += [(g["kind"], p) for p in split_salutation(t)]
        if tb:
            for cap in tb.get("caption", []):
                blocks.append(("raw", cap))
            blocks.append(("raw", table_markdown(build_table(book, tb), tb["header"])))
        for fs in figures or []:
            if fs.get("unit") == u["unit"] and fs.get("after_page") == n:
                fig_at.append((len(blocks), fs["images"]))
    for pos, images in reversed(fig_at):
        blocks[pos:pos] = [
            ("fig", f"![{im.get('caption', '')}](../assets/{im['file']})") for im in images]
    return blocks, notes, head_refs, dropped


def build_toc(book: "Book", u: dict) -> tuple[list[str], int]:
    """目录单元：按纵向空档切条目；条目首行短且不以页码结尾的是作者行，单独成块。

    返回条目表与题名行被去掉的字符数（供字符守恒校验扣除）。
    """
    all_lines = [l for n in range(u["first"], u["last"] + 1) for l in book.page(n)["body"]]
    lines = [l for l in all_lines if _norm(l["text"]) != _norm(u["title"])]
    dropped = sum(sum(1 for c in l["text"] if c.isalnum()) for l in all_lines if l not in lines)
    gaps = [lines[i - 1]["y1"] - lines[i]["y1"] for i in range(1, len(lines))
            if lines[i - 1]["y1"] > lines[i]["y1"]]
    cl = clusters(gaps, statistics.median(gaps) * 0.2) if gaps else []
    cut = (cl[0][-1] + cl[1][0]) / 2 if len(cl) > 1 else 10 ** 6   # 条目内行距与条目间行距的分界
    entries, cur = [], [lines[0]]
    for i in range(1, len(lines)):
        g = lines[i - 1]["y1"] - lines[i]["y1"] if lines[i - 1]["y1"] > lines[i]["y1"] else 10 ** 6
        if g > cut:
            entries.append(cur)
            cur = [lines[i]]
        else:
            cur.append(lines[i])
    entries.append(cur)
    byline = re.compile(r"(?:\w\.\s*){1,3}\w[\w\u2019'-]+(?:\s*,\s*(?:\w\.\s*){1,3}\w[\w\u2019'-]+)*")
    out = []
    for e in entries:
        txt = [l["text"].strip() for l in e]
        if len(e) > 1 and byline.fullmatch(txt[0]):
            out.append(book.apply(txt[0], "block", book.log))
            txt = txt[1:]
        out.append(book.apply(" ".join(txt), "block", book.log))
    return out, dropped


# ---------------------------------------------------------------- 索引

def render_index(spec: dict, links: list[tuple[str, str]], dirs: list[str]) -> str:
    """index.md：units.json 给了 sections 就按目录层级输出「部/章标题 + 单元链接」，
    否则平铺。单元按 sections 的顺序与标题归入各节；未列入 sections 的目录附在末尾。"""
    title = "# " + spec["title"]
    sections = spec.get("sections") or []
    if not sections:
        return "\n".join([title, ""] + [f"- [{t}]({r})" for t, r in links]).rstrip() + "\n"
    grouped: dict[str, list[tuple[str, str]]] = {}
    for (t, r), d in zip(links, dirs):
        grouped.setdefault(d, []).append((t, r))
    lines = [title, ""]
    placed = set()
    for s in sections:
        d = s["dir"]
        if d not in grouped:
            continue
        lines += ["## " + s["title"], ""]
        lines += [f"- [{t}]({r})" for t, r in grouped[d]]
        lines.append("")
        placed.add(d)
    for d in dict.fromkeys(dirs):
        if d in placed or d not in grouped:
            continue
        lines += [f"- [{t}]({r})" for t, r in grouped[d]]
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------- 子命令

def cmd_extract(args) -> None:
    for t in ("djvudump", "djvutxt"):
        if not shutil.which(t):
            sys.exit(f"需要 {t}：DjVuLibre 未安装或不在 PATH 上")
    out = args.out
    (out / "txt").mkdir(parents=True, exist_ok=True)
    (out / "word").mkdir(parents=True, exist_ok=True)

    dump = subprocess.run(["djvudump", str(args.djvu)], capture_output=True, text=True, check=True).stdout
    form = re.compile(r"FORM:DJVU \[\d+\] \{(.+?)\} \[P(\d+)\]")
    chunk = re.compile(r"^\s+(\w+) \[(\d+)\]")
    pages, cur = [], None
    for ln in dump.split("\n"):
        m = form.search(ln)
        if m:
            cur = {"page": int(m.group(2)), "chunks": {}}
            pages.append(cur)
            continue
        if "FORM:DJVI" in ln:
            cur = None
            continue
        m = chunk.match(ln)
        if m and cur is not None:
            cur["chunks"][m.group(1)] = cur["chunks"].get(m.group(1), 0) + int(m.group(2))
    print(f"{args.djvu.name}：{len(pages)} 页")

    recs, bad, notext, linelevel = [], [], [], []
    offsets = parse_page_offset(args.offset)
    for p in pages:
        n = p["page"]
        rec = {"page": n, "has_text": "TXTz" in p["chunks"], "chunks": p["chunks"]}
        if offsets:
            rec["printed"] = printed_page(offsets, n)
        if not rec["has_text"]:
            notext.append(n)
            recs.append(rec)
            continue
        plain = subprocess.run(["djvutxt", f"--page={n}", str(args.djvu)],
                               capture_output=True, text=True, check=True).stdout
        word = subprocess.run(["djvutxt", "--detail=word", f"--page={n}", str(args.djvu)],
                              capture_output=True, text=True, check=True).stdout
        (out / "txt" / f"{n:03d}.txt").write_text(plain, encoding="utf-8")
        (out / "word" / f"{n:03d}.txt").write_text(word, encoding="utf-8")
        lines = parse_page(out / "word" / f"{n:03d}.txt")
        a = sum(1 for l in lines for w in l["words"] for c in w[4] if not c.isspace())
        b = sum(1 for c in plain if not c.isspace())
        if a != b:
            bad.append((n, a, b))
        rec["word_level"] = "(word " in word
        if not rec["word_level"]:
            linelevel.append(n)
        rec.update({"chars": b, "lines": len(lines)}, **page_metrics(lines))
        recs.append(rec)

    (out / "pages.json").write_text(json.dumps({"source": args.djvu.name, "pages": recs},
                                               ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"有文字层 {sum(1 for r in recs if r['has_text'])} 页；无文字层 {len(notext)} 页：{notext}")
    if linelevel:
        print(f"无词级坐标、按行级提取的页 {len(linelevel)} 页：{linelevel}")
    if bad:
        print("逐页字符数校验不通过：")
        for n, a, b in bad:
            print(f"  P{n} 结构={a} 纯文本={b}")
        sys.exit(1)
    print("逐页字符数校验通过")

    img = lambda r: {k: v for k, v in r["chunks"].items() if k != "INFO"}
    blank = [r["page"] for r in recs if not r["has_text"] and not img(r)]
    pic = [r["page"] for r in recs if not r["has_text"] and img(r)]
    ink = [(r["page"], sum(v for k, v in r["chunks"].items() if k != "INFO") / r["chars"])
           for r in recs if r.get("chars", 0) > 50]
    med = statistics.median(v for _, v in ink) if ink else 0
    hot = [p for p, v in ink if med and v > 2 * med]
    print(f"整页图片候选：{pic}")
    print(f"空白页：{blank}")
    print(f"夹图候选（墨量/字数 > 2 倍中位数；表格与大字标题同样上榜，须按文字层排除）：{hot}")


def verify_source(args) -> bool:
    """每次重建前核对登记与实际底本；无法核对不等于通过。"""
    wj = args.work_json or args.out / "work.json"
    try:
        w = json.loads(wj.read_text(encoding="utf-8"))
        scan = w.get("source_scan") or {}
        filename, expected = scan.get("filename"), scan.get("sha256")
        if not filename or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            print(f"底本 SHA-256 未完成核验：{wj} 缺少有效的 source_scan 登记", file=sys.stderr)
            return False
        src = args.source or wj.parent / "source_files" / filename
        if not src.is_file():
            print(f"底本 SHA-256 未完成核验：找不到底本文件 {src}", file=sys.stderr)
            return False
        actual = hashlib.sha256(src.read_bytes()).hexdigest()
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"底本 SHA-256 未完成核验：{exc}", file=sys.stderr)
        return False
    if actual != expected.lower():
        print(f"底本 SHA-256 不符：{src}", file=sys.stderr)
        return False
    print(f"底本 SHA-256 与登记一致：{src}")
    return True


def publish_rebuild(staged: Path, out: Path) -> int:
    """只发布本次生成的 Markdown；发布失败时恢复已替换的文件。"""
    targets = [(p, out / p.relative_to(staged)) for p in sorted(staged.rglob("*.md"))]
    backups: dict[Path, tuple[bytes, int] | None] = {}
    published: list[Path] = []
    try:
        for _, dst in targets:
            if dst.is_symlink():
                raise OSError(f"拒绝覆盖符号链接：{dst}")
            backups[dst] = (dst.read_bytes(), stat.S_IMODE(dst.stat().st_mode)) if dst.exists() else None
        for src, dst in targets:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if backups[dst] is not None:
                src.chmod(backups[dst][1])
            os.replace(src, dst)
            published.append(dst)
    except OSError as exc:
        print(f"发布失败：{exc}；正在恢复本次已替换的文件", file=sys.stderr)
        for dst in reversed(published):
            temporary = None
            try:
                previous = backups[dst]
                if previous is None:
                    dst.unlink()
                else:
                    with tempfile.NamedTemporaryFile(dir=dst.parent, delete=False) as f:
                        temporary = Path(f.name)
                        f.write(previous[0])
                    temporary.chmod(previous[1])
                    os.replace(temporary, dst)
            except OSError as restore_exc:
                print(f"恢复失败：{dst}：{restore_exc}", file=sys.stderr)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return 1
    return 0


def cmd_rebuild(args) -> int:
    if not verify_source(args):
        return 1
    out = args.out.resolve()
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".djvu-rebuild-", dir=out.parent) as tmp:
            staged_args = argparse.Namespace(**vars(args))
            staged_args.out = Path(tmp)
            if not rebuild(staged_args, out):
                print("重建校验未通过，目标 Markdown 未更新", file=sys.stderr)
                return 1
            return publish_rebuild(staged_args.out, out)
    except (OSError, ValueError) as exc:
        print(f"重建未完成：{exc}", file=sys.stderr)
        return 1


def rebuild(args, resource_root: Path) -> bool:
    spec = json.loads(args.units.read_text(encoding="utf-8"))
    fixes = json.loads(args.fixes.read_text(encoding="utf-8")) if args.fixes else []
    tspec = json.loads(args.tables.read_text(encoding="utf-8")) if args.tables else []
    fspec = json.loads(args.figures.read_text(encoding="utf-8")) if args.figures else []
    tables = {str(t["insert_after_page"]): t for t in tspec}
    keep = {(a.lower(), b.lower()): c for a, b, c in spec.get("keep_hyphen", [])}

    page_offset = parse_page_offset(spec.get("page_offset", spec.get("offset", 0)))
    excluded = parse_excluded(spec.get("excluded_pages"))
    book = Book(args.work, page_offset, fixes, args.normalize, excluded)
    book.log = {}
    book.measure(sorted({n for u in spec["units"] for n in range(u["first"], u["last"] + 1)}))
    print(f"全书段首缩进 {book.indent:.0f} px")
    if book.missing:
        print(f"无文字层、不参与正文的页：{sorted(book.missing)}")
    if book.excluded_hit:
        print(f"不进入正文的页（照片插页等）：{sorted(book.excluded_hit)}")
    seen = inline_hyphens(args.work)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    issues, rows, links = [], [], []
    sections = {s["dir"]: s["title"] for s in spec.get("sections") or []}
    dropped: dict[str, int] = {}

    for u in spec["units"]:
        if u.get("kind") == "toc":
            toc, dropped[u["unit"]] = build_toc(book, u)
            blocks = [("para", t) for t in toc]
            notes, refs = [], {"title": "", "author": ""}
        else:
            blocks, notes, refs, dropped[u["unit"]] = build_unit(
                book, u, seen, keep, tables, issues, sections.get(u["dir"]), fspec)
        items: list[tuple[str, bool]] = [("# " + u["title"] + refs["title"], False)]
        if u.get("author"):
            items.append((u["author"] + refs["author"], False))
        for kind, t in blocks:
            items.append((("## " + t) if kind == "head" else t, kind == "fig"))
        for i, t in enumerate(notes, 1):
            items.append((f"[^{u['unit']}-{i:03d}]: " + book.apply(t, "block", book.log), False))
        # 图块的 block-id 续在单元既有末位之后，正文块编号不变
        seq, figseq = 0, len(items) - sum(1 for _, isfig in items if isfig)
        body, n = [], len(items)
        for t, isfig in items:
            if isfig:
                figseq += 1
                k = figseq
            else:
                seq += 1
                k = seq
            body.append(f"<!-- block-id: b{k:06d} -->\n{t}\n")
        rel = f"{u['dir']}/{u['unit']}-{u['slug']}.md"
        (out / u["dir"]).mkdir(parents=True, exist_ok=True)
        (out / rel).write_text("\n".join(body), encoding="utf-8")
        links.append((f"{u['author']}. {u['title']}" if u.get("author") else u["title"], rel))
        rows.append((u["unit"], n, sum(1 for k, _ in blocks if k == "head"), len(notes)))

    (out / "index.md").write_text(
        render_index(spec, links, [u["dir"] for u in spec["units"]]), encoding="utf-8")

    if book.log:
        print("OCR 修正：")
        for k, v in sorted(book.log.items(), key=lambda x: -x[1]):
            print(f"  {k:<34} {v}")
    print(f"\n{'unit':<6} {'块':<6} {'##':<4} 脚注")
    for r in rows:
        print("%-6s %-6d %-4d %d" % r)
    if issues:
        print("\n注标数与注释条数不等的页（注标原样保留，须写入 source-issues.json）：")
        for it in issues:
            print(f"  P{it['page']} 注标={it['marks']} 注释={it['notes']}")
    return verify(out, book, spec, dropped, resource_root)


def verify(out: Path, book: "Book", spec: dict, dropped: dict[str, int] | None = None,
           resource_root: Path | None = None) -> bool:
    """字符守恒：单元正文（不含所录题名／署名，不含被抑制的篇首目录行）对所辖各页。

    单元头的 `# 题名` 与署名行来自目录登记而非页面，比对时整段去掉；篇首页面上与之重复的
    题名／署名／部题行已由 `build_unit` 抑制，其字符数从页面侧扣除。
    """
    dropped = dropped or {}
    print("\n校验：")
    ok = True
    for u in spec["units"]:
        f = out / u["dir"] / f"{u['unit']}-{u['slug']}.md"
        md = f.read_text(encoding="utf-8")
        ids = re.findall(r"<!-- block-id: (b\d+) -->", md)
        # 插图块的 block-id 续在单元末位之后、位置却在单元中间，故只查唯一与无缺号
        if sorted(ids) != [f"b{i + 1:06d}" for i in range(len(ids))]:
            print(f"  ✗ block-id 有缺号或重号：{f}")
            ok = False
        for alt, rel in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", md):
            resource_file = (resource_root / f.relative_to(out)) if resource_root else f
            if not (resource_file.parent / rel).resolve().exists():
                print(f"  ✗ 图片路径不可解析：{f} → {rel}")
                ok = False
        defs = set(re.findall(r"^\[\^([^\]]+)\]:", md, re.M))
        refs = set(re.findall(r"\[\^([^\]]+)\]", re.sub(r"^\[\^[^\]]+\]:", "", md, flags=re.M)))
        if defs != refs:
            print(f"  ✗ 脚注未配对：{f} {sorted(defs ^ refs)[:4]}")
            ok = False
        if md.startswith("---"):
            print(f"  ✗ 章节文件带 front matter：{f}")
            ok = False
        parts = [p for p in re.split(r"(?=<!-- block-id: b\d+ -->)", md) if p.strip()]
        body = "".join(parts[2:] if u.get("author") else parts[1:])
        clean = re.sub(r"<!-- block-id: b\d+ -->", "", body)
        clean = re.sub(r"^!\[[^\]]*\]\([^)]+\)$", "", clean, flags=re.M)   # 插图块不计字符
        clean = re.sub(r"^\[\^[^\]]+\]:", "", clean, flags=re.M)
        clean = re.sub(r"\[\^[^\]]+\]", "", clean)
        clean = re.sub(r"^#+\s*", "", clean, flags=re.M).replace("|", " ").replace("**", " ").replace("---", " ")
        a = sum(1 for c in clean if c.isalnum())
        src = " ".join(l["text"] for n in range(u["first"], u["last"] + 1)
                       for l in book.page(n)["body"] + book.page(n)["notes"])
        b = sum(1 for c in re.sub(r"\[\^[^\]]+\]", "", src) if c.isalnum()) - dropped.get(u["unit"], 0)
        if abs(a - b) > 2:
            print(f"  ! 字符差 {a - b:+d}：{u['unit']}（差额须能逐项说明）")
    bad = [t for t, r in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", (out / "index.md").read_text(encoding="utf-8"))
           if not (out / r).exists()]
    if bad:
        print(f"  ✗ index.md 失效链接 {len(bad)} 条")
        ok = False

    # 行内漏词探测：行 bbox 宽 ÷ 字符数明显超过该页中位字宽、且行接近满行的
    loss = []
    for u in spec["units"]:
        for n in range(u["first"], u["last"] + 1):
            rec = book.page(n)
            cw = rec["med_cw"]
            if not cw:
                continue
            for l in rec["body"] + rec["notes"]:
                t = l["text"]
                if len(t) < 12:
                    continue
                if l["x1"] < rec["right"] - 2 * cw:
                    continue
                if (l["x1"] - l["x0"]) / len(t) > 1.45 * cw:
                    loss.append((n, round((l["x1"] - l["x0"]) / len(t) / cw, 2), t[:56]))
    if loss:
        print(f"  ! 行内漏词候选 {len(loss)} 行（须逐条裁图核对，记入 source-issues.json）")
        for n, r, t in sorted(loss)[:12]:
            print(f"      P{n} {r}× {t!r}")
    else:
        print("  行内漏词探测：无命中")

    # 孤立的异文种字母（整词换字母表的痕迹）
    foreign = {}
    for f in out.rglob("u*.md"):
        txt = f.read_text(encoding="utf-8")
        txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
        txt = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", txt)
        txt = re.sub(r"\[\^[^\]]+\]", "", txt)
        for m in re.finditer(r"(?<![0-9A-Za-zА-Яа-яЁё])[A-Za-z]{1,2}(?![0-9A-Za-zА-Яа-яЁё])", txt):
            foreign[m.group(0)] = foreign.get(m.group(0), 0) + 1
    print(f"  孤立异文种字母：{sum(foreign.values())} 处 " +
          ("（样例： " + ", ".join(f"{k}×{v}" for k, v in sorted(foreign.items(), key=lambda x: -x[1])[:8]) + "）" if foreign else ""))

    print("  block-id、脚注配对、front matter、index.md 链接：" + ("全部通过" if ok else "有未通过项"))
    print("  字符差、漏词与异文种字母候选须人工核对；结构检查通过不代表最终验收完成")
    return ok


def cmd_crop(args) -> None:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("需要 Pillow：python3 -m pip install --user pillow")
    if args.words:
        lines = parse_page(args.words / f"{args.page:03d}.txt")
    else:
        txt = subprocess.run(["djvutxt", "--detail=word", f"--page={args.page}", str(args.djvu)],
                             capture_output=True, text=True, check=True).stdout
        tmp = args.out.with_suffix(".word.txt")
        tmp.write_text(txt, encoding="utf-8")
        lines = parse_page(tmp)
        tmp.unlink()
    hits = [l for l in lines if args.find in l["text"]]
    if not hits:
        sys.exit(f"P{args.page} 未找到：{args.find}")
    l = hits[0]
    x0, x1 = max(0, l["x0"] - args.pad), l["x1"] + args.pad
    y0, y1 = max(0, l["y0"] - args.pad), l["y1"] + args.pad
    pnm = args.out.with_suffix(".pnm")
    subprocess.run(["ddjvu", "-format=pnm", f"-page={args.page}",
                    f"-segment={x1 - x0}x{y1 - y0}+{x0}+{y0}", str(args.djvu), str(pnm)], check=True)
    im = Image.open(pnm)
    im = im.resize((im.width * args.scale, im.height * args.scale), Image.LANCZOS)
    im.save(args.out)
    pnm.unlink()
    print(f"P{args.page} 「{l['text'][:40]}」→ {args.out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="导出逐页数据并校验")
    e.add_argument("djvu", type=Path)
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--offset", default=None,
                   help="印张页映射：整数，或 3-242:2,243-258:,259-498:18；省略 offset 的段不参与页眉判定")
    e.set_defaults(func=cmd_extract)

    r = sub.add_parser("rebuild", help="按单元表重建单元 Markdown")
    r.add_argument("work", type=Path, help="extract 的输出目录")
    r.add_argument("--units", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--source", type=Path, help="实际底本，用于必需的 SHA-256 核验")
    r.add_argument("--work-json", type=Path, help="作品登记（默认读取输出目录的 work.json）")
    r.add_argument("--fixes", type=Path)
    r.add_argument("--tables", type=Path)
    r.add_argument("--figures", type=Path, help="插图清单：单元、插在哪一页之后、文件名与图注")
    r.add_argument("--normalize", choices=["ru"], help="套用该语种的通则性 OCR 修正")
    r.set_defaults(func=cmd_rebuild)

    c = sub.add_parser("crop", help="按行内文字裁切页面图像")
    c.add_argument("djvu", type=Path)
    c.add_argument("--page", type=int, required=True)
    c.add_argument("--find", required=True)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--words", type=Path, help="已导出的 word 目录，免得重跑 djvutxt")
    c.add_argument("--pad", type=int, default=30)
    c.add_argument("--scale", type=int, default=3)
    c.set_defaults(func=cmd_crop)

    args = ap.parse_args()
    result = args.func(args)
    return 0 if result is None else result


SCHEMA = """
units.json   {"title": 书名, "page_offset": 页码映射, "sections": 目录层级, "keep_hyphen": [...],
              "units": [{"unit": "u001", "dir": "00-slug", "slug": "...", "title": "...",
                         "author": "..." 或省略, "first": 起始文档页, "last": 结束文档页,
                         "kind": "toc" 仅目录单元}]}
page_offset  段表，段内 印张页 = 文档页 - offset。接受整数（全书同一偏移）、
             "3-242:2,243-258:,259-498:18"，或 [{"first": 3, "last": 242, "offset": 2},
             {"first": 243, "last": 258}, {"first": 259, "last": 498, "offset": 18}]。
             省略 offset 的段无印张页码（照片插页一类），不参与页眉判定；省略 first/last
             为开口段。无页码插页使偏移改变的底本分段给。旧写法 "offset": 2 仍可用；
             两者都省略时按偏移 0 处理。
sections     [{"dir": "02-slug", "title": "I. ..."}, ...]。按此顺序与标题生成 index.md 的
             部/章标题与单元链接；省略时 index.md 为平铺列表。未列入的目录附在末尾。
excluded_pages 不进入正文的文档页，[243, 244] 或 ["243-258"]。无页码照片插页、扉页一类
             属底本载体的整页内容列在这里：页虽落在某单元范围内，正文不含其文字。
             图片按第 5 步另行交付，图注随图块照录。
fixes.json   [{"scope": "line"|"block", "pattern": 正则, "replace": 替换, "label": 统计名,
               "literal": true 表示按字面而非正则}]
tables.json  [{"insert_after_page": 文档页, "header": [栏名...], "caption": [题注行...],
               "regions": [{"page": 文档页, "y_max": 表格区上界}], "cell_fixes": {误识: 更正}}]
figures.json [{"unit": "u037", "after_page": 文档页, "images": [{"file": "d243-01-slug.jpg",
               "caption": "原印图注，无图注留空"}]}]。图块排在 after_page 的块边界之后，
              block-id 续在单元既有末位之后，正文块编号不变；文件放作品目录 assets/ 下，
              正文以 ../assets/ 相对路径引用。
work.json    作品目录下的登记表（不参与生成本身）：{"work_id", "title", "year",
              "source_edition", "isbn", "source_url", "source_record_id",
              "digitization_route", "text_status",
              "source_scan": {"filename": 底本文件名, "sha256": 底本摘要}}。
              text_status 见工作流「状态」一节。
rebuild       --source 指定实际底本，--work-json 指定登记文件；默认使用输出目录 work.json
              和该登记文件同级 source_files/filename 路径。公开用法显式给出两项。
              每次重建必须先完成 source_scan 的 SHA-256 核验；不符或无法核验均非零退出。
              临时重建通过确定性结构校验后才替换目标 Markdown；候选疑难仍须人工核对。
"""

if __name__ == "__main__":
    sys.exit(main())
