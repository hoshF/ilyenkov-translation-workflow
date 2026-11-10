# /// script
# requires-python = ">=3.10"
# dependencies = ["pdfplumber"]
# ///
"""数字原生 PDF 的对象审计工具，对应 `digitization/DIGITAL_PDF_RECONSTRUCTION_WORKFLOW.md` 第 4 步。

    uv run scripts/pdf_object_audit.py extract 底本.pdf --work-json 作品目录/work.json --out 临时目录
    uv run scripts/pdf_object_audit.py audit 临时目录 --md 正文.md [--config audit.json] --out report.json
    uv run scripts/pdf_object_audit.py show report.json [--category 类别] [--limit N]
    uv run scripts/pdf_object_audit.py targets 临时目录 [--config audit.json] [--report report.json] --out targets.json
    uv run scripts/pdf_object_audit.py crop 底本.pdf --page N --find 行内文字 [--lines 2] --out 图.png

extract 直接从底本导出逐页字符、规线与图像对象，并按 work.json 的 source_scan 核对底本 SHA-256。
audit 从页面对象独立推定文字、大小写、斜体、上标、断词、段落、脚注分段与条目边界，与 Markdown
正文逐词、逐结构比对，只输出候选差异，不修改正文。候选只作核对线索，程序退出成功不表示核验通过。
targets 列出须定向对照渲染页面的页。crop 裁出含指定文字的一行及上下各若干行的整幅宽放大图。

判据以页内正文字号、行距中位数和中位字宽的倍数表述。该书特有的页码范围与已确认的残余差异
由临时目录中的 audit.json 给入，格式见本文件末尾的 SCHEMA。
"""
from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import json
import re
import statistics
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

INDENT = 0.4          # 段首缩进：行首右移超过 0.4 倍字号
SHORT = 1.3           # 短行：行尾距栏右界超过 1.3 倍字号
GAP = 1.5             # 段间空：行距超过 1.5 倍行距中位数
WORD_GAP = 0.1        # 无空格字符的页，字间空隙超过 0.1 倍字号即断词
SMALLCAP = 0.04       # 小写字母字宽偏离同字形主宽 4% 以上，作为异形的初始依据
GLYPH_ROUND = 0.006   # 字宽偏离 0.6% 以内视为同一字形
GLYPH_ALT = 0.01      # 连字成分以外的字母，字宽偏离 1% 以上即为另一字形
GLYPH_SHARED = 0.8    # 某一字宽 80% 以上与初始异形字母同词出现，即为异形
LIGATURE = set('fijl')  # 连字拆分后字宽会变的字母，偏离 4% 以内只凭同词证据判定
HEAD_BAND = 0.075     # 页眉带：页高上 7.5%
FOOT_BAND = 0.92      # 页脚带：页高 92% 以下
ITALIC = re.compile(r'Italic|Oblique|-It\b|-It$|BoldIt')
SPACES = {' ', '\u2002', '\u2003', '\u2009', '\u00a0', '\u202f'}
ZERO_WIDTH = {'\u200b', '\u200c', '\u200d', '\ufeff'}


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKC', s)
    return ''.join(c for c in s if c not in ZERO_WIDTH)


def key(t: str) -> str:
    return re.sub(r'[-\u2011\u00ad]', '', t).lower()


def white(color) -> bool:
    if color is None:
        return False
    if isinstance(color, (int, float)):
        color = (color,)
    try:
        vals = [float(v) for v in color]
    except (TypeError, ValueError):
        return False
    if len(vals) == 1:
        return vals[0] >= 0.99
    if len(vals) == 3:
        return all(v >= 0.99 for v in vals)
    if len(vals) == 4:
        return all(v <= 0.01 for v in vals)
    return False


# ---------------------------------------------------------------- extract

def cmd_extract(args) -> None:
    import pdfplumber

    pdf = Path(args.pdf)
    work = json.loads(Path(args.work_json).read_text())
    expected = (work.get('source_scan') or {}).get('sha256')
    if not expected:
        fail('未完成核验：work.json 未登记 source_scan.sha256')
    actual = sha256(pdf)
    if actual != expected:
        fail(f'摘要不匹配：底本 {actual}，登记 {expected}')
    out = Path(args.out)
    (out / 'pages').mkdir(parents=True, exist_ok=True)
    with pdfplumber.open(pdf) as doc:
        for n, page in enumerate(doc.pages, 1):
            fonts: list[str] = []
            chars = []
            for c in page.chars:
                f = c['fontname'].split('+')[-1]
                if f not in fonts:
                    fonts.append(f)
                chars.append([c['text'], fonts.index(f), round(c['size'], 2), round(c['x0'], 2), round(c['x1'], 2),
                              round(c['top'], 2), round(c['bottom'], 2), int(bool(c['upright'])),
                              int(white(c.get('non_stroking_color')))])
            rules = [[round(x['x0'], 2), round(x['x1'], 2), round(x['top'], 2)] for x in page.lines
                     if abs(x['top'] - x['bottom']) < 1.5]
            rules += [[round(x['x0'], 2), round(x['x1'], 2), round(x['top'], 2)] for x in page.rects
                      if x['height'] < 1.5 and x['width'] > 5]
            rec = {'n': n, 'w': float(page.width), 'h': float(page.height), 'rot': page.rotation or 0,
                   'fonts': fonts, 'chars': chars, 'rules': rules,
                   'images': [[round(i['x0'], 1), round(i['top'], 1), round(i['x1'], 1), round(i['bottom'], 1)]
                              for i in page.images],
                   'curves': len(page.curves), 'rects': len(page.rects)}
            (out / 'pages' / f'p{n:04}.json').write_text(json.dumps(rec, ensure_ascii=False))
        count = len(doc.pages)
    (out / 'meta.json').write_text(json.dumps({'pdf': str(pdf), 'sha256': actual, 'pages': count}, ensure_ascii=False))
    print(f'已导出 {count} 页；底本 SHA-256 与登记一致')


# ---------------------------------------------------------------- page model

class Book:
    def __init__(self, tmp: Path, config: dict):
        meta = json.loads((tmp / 'meta.json').read_text())
        self.count = meta['pages']
        self.config = config
        self.pages = {}
        for n in range(1, self.count + 1):
            self.pages[n] = json.loads((tmp / 'pages' / f'p{n:04}.json').read_text())
        sizes = collections.Counter()
        for rec in self.pages.values():
            for c in rec['chars']:
                if c[0].strip():
                    sizes[round(c[2] * 2) / 2] += 1
        self.body_size = sizes.most_common(1)[0][0] if sizes else 10.0
        self._glyph_widths()
        self._running_heads()

    def font(self, rec, c) -> str:
        return rec['fonts'][c[1]]

    def italic(self, rec, c) -> bool:
        return bool(ITALIC.search(self.font(rec, c)))

    def _glyph(self, rec, c) -> tuple | None:
        if not (c[0].isalpha() and c[0].islower()) or c[2] <= 0:
            return None
        return c[0], self.font(rec, c), round((c[4] - c[3]) / c[2], 3)

    def _deviation(self, g) -> float:
        d = self.dominant[g[:2]]
        return abs(g[2] - d) / d

    def _glyph_widths(self) -> None:
        """小型大写与小写共用字符编码，只能凭字宽区分：每个字宽是否异形，看它偏离主宽的程度和同词证据。"""
        widths = collections.defaultdict(collections.Counter)
        for rec in self.pages.values():
            for c in rec['chars']:
                g = self._glyph(rec, c)
                if g:
                    widths[g[:2]][g[2]] += 1
        self.dominant = {k: v.most_common(1)[0][0] for k, v in widths.items()}
        seed = lambda g: g[0] not in LIGATURE and self._deviation(g) > SMALLCAP
        seen, shared = collections.Counter(), collections.Counter()
        for rec in self.pages.values():
            for l in self._raw_lines(rec):
                word, prev = [], None
                for c in l['chars'] + [None]:
                    if c is None or c[0] in SPACES or not c[0].strip() or (prev and c[3] - prev[4] > WORD_GAP * c[2]):
                        gs = [g for g in map(lambda x: self._glyph(rec, x), word) if g]
                        for k, g in enumerate(gs):
                            seen[g] += 1
                            shared[g] += any(seed(h) for h in gs[:k] + gs[k + 1:])
                        word = []
                    if c is not None and c[0].strip() and c[0] not in SPACES:
                        word.append(c)
                    prev = c
        self.alternate = {g for g in seen if self._deviation(g) > GLYPH_ROUND and (
            shared[g] >= GLYPH_SHARED * seen[g] or self._deviation(g) > (SMALLCAP if g[0] in LIGATURE else GLYPH_ALT))}

    def bold_start(self, rec, l) -> bool:
        vis = [c for c in l['chars'] if c[0].strip()][:3]
        return len(vis) >= 2 and all('Bold' in self.font(rec, c) for c in vis)

    def odd_glyph(self, rec, c) -> bool:
        return self._glyph(rec, c) in self.alternate

    def _raw_lines(self, rec) -> list[dict]:
        rows: list[dict] = []
        for c in sorted(rec['chars'], key=lambda c: (c[6], c[3])):
            if not c[7]:
                continue
            for r in rows:
                if abs(r['bottom'] - c[6]) < 0.35 * max(c[2], 1):
                    r['chars'].append(c)
                    break
            else:
                rows.append({'bottom': c[6], 'chars': [c]})
        lines = []
        for r in sorted(rows, key=lambda r: r['bottom']):
            cs = sorted(r['chars'], key=lambda c: c[3])
            vis = [c for c in cs if c[0].strip()]
            if not vis:
                continue
            lines.append({'chars': cs, 'x0': vis[0][3], 'x1': vis[-1][4], 'top': min(c[5] for c in cs),
                          'bottom': r['bottom'], 'size': max(c[2] for c in vis)})
        return lines

    def _running_heads(self) -> None:
        seen = collections.Counter()
        for rec in self.pages.values():
            for l in self._raw_lines(rec):
                if self._in_band(rec, l):
                    seen[(l['top'] < HEAD_BAND * rec['h'], self._head_key(l))] += 1
        self.heads = {k for k, v in seen.items() if k[1] and v >= (2 if k[0] else 3)}

    @staticmethod
    def _text(l) -> str:
        return ''.join(c[0] for c in l['chars'])

    def _head_key(self, l) -> str:
        t = re.sub(r'\s+', '', self._text(l).lower())
        return re.sub(r'^[\divxlcdm]+|[\divxlcdm]+$', '', t)

    @staticmethod
    def _in_band(rec, l) -> bool:
        return l['top'] < HEAD_BAND * rec['h'] or l['bottom'] > FOOT_BAND * rec['h']

    def is_furniture(self, rec, l) -> bool:
        if not self._in_band(rec, l) or l['size'] > 1.05 * self.body_size:
            return False
        t = self._text(l).strip()
        if re.fullmatch(r'[\divxlcdmIVXLCDM]+', t):
            return True
        return (l['top'] < HEAD_BAND * rec['h'], self._head_key(l)) in self.heads

    def note_rule(self, rec) -> float | None:
        cands = [r[2] for r in rec['rules'] if 0.08 * rec['w'] < r[1] - r[0] < 0.5 * rec['w'] and r[2] > 0.15 * rec['h']]
        return min(cands) if cands else None

    def columns(self, lines, few: bool = False) -> float | None:
        if len(lines) < (2 if few else 16):
            return None
        xs = [l['x0'] for l in lines] + [l['x1'] for l in lines]
        lo, hi = min(xs), max(xs)
        best = None
        for i in range(31, 70):
            x = lo + (hi - lo) * i / 100
            cross = sum(1 for l in lines if any(c[3] < x < c[4] for c in l['chars'] if c[0].strip()))
            left = sum(1 for l in lines if any(c[4] <= x for c in l['chars'] if c[0].strip()))
            right = sum(1 for l in lines if any(c[3] >= x for c in l['chars'] if c[0].strip()))
            if left >= (2 if few else 8) and right >= (2 if few else 8) and cross <= 0.2 * len(lines):
                if best is None or cross < best[0]:
                    best = (cross, x)
        return best[1] if best else None

    def page_lines(self, n: int) -> dict:
        rec = self.pages[n]
        raw = [l for l in self._raw_lines(rec) if not self.is_furniture(rec, l)]
        rule = self.note_rule(rec)
        body = [l for l in raw if not (rule and l['top'] > rule)]
        notes = [l for l in raw if rule and l['top'] > rule]
        out = {}
        few = entry_kind(self.config, n) is not None
        body_mid = self.columns(body, few)
        for name, ls in (('body', body), ('note', notes)):
            mid = body_mid if name == 'body' else (self.columns(ls) if body_mid is not None else None)
            if mid is None:
                out[name] = [ls]
                continue
            top, left, right, bottom = [], [], [], []
            split = False
            for l in ls:
                vis = [c for c in l['chars'] if c[0].strip()]
                if any(c[3] < mid < c[4] for c in vis):
                    (bottom if split else top).append(l)
                    continue
                split = True
                lc = [c for c in l['chars'] if c[4] <= mid]
                rc = [c for c in l['chars'] if c[3] >= mid]
                for part, dest in ((lc, left), (rc, right)):
                    pv = [c for c in part if c[0].strip()]
                    if pv:
                        dest.append({'chars': part, 'x0': pv[0][3], 'x1': pv[-1][4], 'top': min(c[5] for c in part),
                                     'bottom': l['bottom'], 'size': max(c[2] for c in pv)})
            out[name] = [x for x in (top, left, right, bottom) if x]
        out['two_column'] = body_mid is not None
        return out


# ---------------------------------------------------------------- pdf token stream

def entry_kind(config: dict, n: int) -> str | None:
    for r in config.get('entry_ranges', []):
        a, b = r['pages']
        if a <= n <= b:
            return r['kind']
    return None


def page_set(config: dict, book: Book) -> list[int]:
    a, b = config.get('body_pages', [1, book.count])
    skip = set(config.get('exclude_pages', []))
    return [n for n in range(a, b + 1) if n not in skip]


def index_turnover(book: Book, config: dict) -> float:
    offs = collections.Counter()
    for n in page_set(config, book):
        if entry_kind(config, n) != 'index':
            continue
        for col in book.page_lines(n)['body']:
            left = min(l['x0'] for l in col)
            offs.update(round(l['x0'] - left) for l in col)
    common = [o for o, c in offs.items() if c >= 3 and o > 0]
    return max(common) if common else book.body_size * 9


def author_rule(rec, l) -> float | None:
    """条目页中代替重复作者名的绘制横线：与该行同高，紧接行首文字左侧，宽 1.5–6 倍字号。"""
    s = l['size']
    for x0, x1, top in rec['rules']:
        if l['top'] <= top <= l['bottom'] and 0 <= l['x0'] - x1 < 1.5 * s and 1.5 * s <= x1 - x0 <= 6 * s:
            return x0
    return None


def pdf_streams(book: Book, config: dict) -> dict:
    streams = {'body': [], 'note': []}
    index_turn = index_turnover(book, config)
    last = {'body': None, 'note': None}
    for n in page_set(config, book):
        rec = book.pages[n]
        pl = book.page_lines(n)
        space_mode = sum(1 for c in rec['chars'] if c[0] in SPACES) > 0.05 * max(1, len(rec['chars']))
        kind = entry_kind(config, n)
        for name in ('body', 'note'):
            for col in pl[name]:
                if not col:
                    continue
                if kind == 'hanging' and name == 'body':
                    for l in col:
                        x0 = author_rule(rec, l)
                        if x0 is not None:
                            l['x0'], l['rule'] = x0, True
                left = min(l['x0'] for l in col if l['size'] >= 0.9 * book.body_size) if any(
                    l['size'] >= 0.9 * book.body_size for l in col) else min(l['x0'] for l in col)
                spacing = statistics.median([b['top'] - a['top'] for a, b in zip(col, col[1:])] or [book.body_size * 1.2])
                for k, l in enumerate(col):
                    l['toks'] = line_tokens(book, rec, l, space_mode)
                    if l.get('rule'):
                        l['toks'].insert(0, {'t': '———', 'i': 0, 'sc': False, 'soft': False, 'dg': []})
                    near = [m['x1'] for m in col[max(0, k - 2):k + 3] if abs(m['size'] - l['size']) <= 0.05 * l['size']
                            and abs(m['x0'] - l['x0']) <= 1.2 * l['size']]
                    l['right'] = max(near) if len(near) > 1 else max(m['x1'] for m in col)
                rest = [l['x0'] for l in col if l['toks'] and not NOTE_NUM.match(l['toks'][0]['t'])]
                text_left = collections.Counter(round(x) for x in rest).most_common(1)[0][0] if rest else left
                for i, l in enumerate(col):
                    prev = col[i - 1] if i else last[name]
                    s = l['size']
                    toks = l['toks']
                    if name == 'note' and toks and NOTE_NUM.match(toks[0]['t']):
                        toks[0]['t'] = toks[0]['t'].rstrip('.')
                    head = ' '.join(t['t'] for t in toks)
                    marker = bool(toks) and bool(MARKER.match(toks[0]['t'] + ' '))
                    bold = book.bold_start(rec, l)
                    large = s > 1.15 * book.body_size
                    same_large = prev is not None and large and abs(s - prev['size']) <= 0.15 * s
                    if kind == 'hanging' and name == 'body':
                        start = l['x0'] - left < INDENT * s
                    elif kind == 'index' and name == 'body':
                        start = l['x0'] - left < index_turn - INDENT * s
                    elif name == 'note':
                        number = bool(toks) and bool(NOTE_NUM.match(toks[0]['t'])) and l['x0'] - left < INDENT * s
                        start = number or l['x0'] - text_left > INDENT * s
                    elif prev is None:
                        start = True
                    elif large:
                        start = not same_large or bold != prev.get('bold') or l['top'] - prev['top'] > 2 * GAP * s
                    elif i == 0:
                        start = ((l['x0'] - left) - prev['off'] > INDENT * s or prev['short']
                                 or (bold and prev['ends']) or abs(s - prev['size']) > 0.05 * max(s, prev['size']))
                    else:
                        indent = l['x0'] - prev['x0'] > INDENT * s
                        hanging = bool(indent and not prev['short'] and (prev.get('item') or prev.get('hang')))
                        l['hang'] = hanging
                        outdent = prev['x0'] - l['x0'] > INDENT * s and marker
                        resized = abs(s - prev['size']) > 0.05 * max(s, prev['size'])
                        start = ((indent and not hanging) or prev['short'] or outdent or resized
                                 or (l['top'] - prev['top'] > GAP * spacing) or (bold and prev['ends']))
                    l['short'] = l['right'] - l['x1'] > SHORT * s
                    l['off'] = l['x0'] - left
                    l['bold'] = bold
                    l['ends'] = bool(re.search(r'[.!?…:’”)\]][\d*†]*$', head))
                    l['item'] = marker
                    if not toks:
                        continue
                    for j, t in enumerate(toks):
                        t.update({'p': n, 'ls': j == 0, 'le': j == len(toks) - 1, 'start': start and j == 0})
                        streams[name].append(t)
                    last[name] = l
    for name in streams:
        streams[name] = join_hyphens(streams[name])
    return streams


NOTE_NUM = re.compile(r'\d{1,3}\.?$')
RAISED_SHARE = 0.8    # 某一数字字宽 80% 以上落在正文脚注引用号位置，即为上标字形
RAISE = '\x01\x02'    # 正文中括起脚注引用号
SUPER = '\x03\x04'    # 正文中括起 <sup>
RAISED = re.compile('[\x01\x03]([^\x02\x04]*)[\x02\x04]')
MARKER = re.compile(r'(\(?[ivxlc]+[.)]|\(?\d+[.)]|\d{1,2}|\([a-z]\)|[a-z]\))\s', re.I)


def line_text(l) -> str:
    return ''.join(c[0] for c in l['chars'])


def line_tokens(book: Book, rec, l, space_mode: bool) -> list[dict]:
    toks, cur, it, sc, dg = [], [], [], [], []
    prev = None

    def flush():
        if cur:
            text = ''.join(cur)
            letters = [x for x in sc if x is not None]
            odd = sum(1 for x in letters if x)
            toks.append({'t': text, 'i': sum(it) / len(it),
                         'sc': (odd >= 2 and odd >= 0.6 * len(letters)) or (len(letters) == 1 and odd == 1 and len(text.strip('.,;:()[]')) == 1),
                         'soft': '\u00ad' in text and not text.endswith('\u00ad'), 'dg': dg[:]})
        cur.clear(); it.clear(); sc.clear(); dg.clear()

    for c in l['chars']:
        ch = norm(c[0])
        if c[0] in SPACES or not ch.strip():
            flush()
            prev = c
            continue
        if not space_mode and prev is not None and c[3] - prev[4] > WORD_GAP * c[2]:
            flush()
        prev = c
        cur.append(ch)
        it.append(book.italic(rec, c))
        sc.append(book.odd_glyph(rec, c) if len(ch) == 1 and c[0].isalpha() and c[0].islower() else None)
        if ch.isdigit() and c[2] > 0:
            dg.append((ch, book.font(rec, c), round((c[4] - c[3]) / c[2], 3)))
    flush()
    for t in toks:
        t['t'] = t['t'].replace('\u00ad', '-')
    return [t for t in toks if not re.fullmatch(r'\.{6,}', t['t'])]


def join_hyphens(tokens: list[dict]) -> list[dict]:
    out = []
    for t in tokens:
        prev = out[-1] if out else None
        if (prev and prev['le'] and t['ls'] and len(prev['t']) > 1 and prev['t'].endswith('-')
                and prev['t'][-2].isalpha() and t['t'][:1].isalpha() and not t['start']):
            head = prev['t'][:-1]
            la, lb = len(prev['t']), len(t['t'])
            prev['i'] = (prev['i'] * la + t['i'] * lb) / (la + lb)
            prev['jh'] = re.sub(r'^\W+|\W+$', '', head + '-' + t['t']).lower()
            prev['jw'] = re.sub(r'^\W+|\W+$', '', head + t['t']).lower()
            prev['t'] = head + '-' + t['t']
            prev['dg'] = prev['dg'] + t['dg']
            prev['le'] = t['le']
            prev['join'] = True
            continue
        out.append(dict(t))
    return out


# ---------------------------------------------------------------- markdown stream

def md_streams(md: Path) -> dict:
    lines = md.read_text().split('\n')
    streams = {'body': [], 'note': []}
    section = 0
    in_note = False
    for ln, raw in enumerate(lines, 1):
        line = raw
        if not line.strip():
            continue
        if line.startswith('```') or line.startswith('![') or re.fullmatch(r'\|?[\s:\-|]+\|?', line):
            continue
        if re.match(r'#{1,3} ', line):
            section += 1
        if re.fullmatch(r'\*(\s*\*){2,}', line.strip()):
            streams['body'].extend({'t': '*', 'i': 0, 'ln': ln, 'start': k == 0, 'sec': section} for k in range(line.count('*')))
            continue
        stream = 'body'
        m = re.match(r'\[\^([^\]]+)\]:\s*', line)
        if m:
            in_note = True
            stream = 'note'
            num = re.search(r'(\d+)$', m.group(1))
            line = (num.group(1) + ' ' if num else '') + line[m.end():]
        elif line.startswith('    ') and in_note:
            stream = 'note'
            line = line.strip()
        else:
            in_note = False
        line = re.sub(r'\[\^[^\]]*?(\d+)\]', RAISE[0] + r'\1' + RAISE[1], line)
        line = re.sub(r'\[\^[^\]]*\]', '', line)
        line = re.sub(r'<sup>(.*?)</sup>', SUPER[0] + r'\1' + SUPER[1], line)
        line = re.sub(r'^#+\s*', '', line)
        line = re.sub(r'^(>\s?)+', '', line)
        line = re.sub(r'^\s*-\s+', '', line)
        line = line.replace('|', ' ').replace('<br>', ' ')
        chars = []
        ital = False
        for piece in re.split(r'(<em>|</em>|\*\*\*|\*\*|\*|\\.)', line):
            if piece == '<em>':
                ital = True
            elif piece == '</em>':
                ital = False
            elif piece in ('*', '***'):
                ital = not ital
            elif piece == '**':
                pass
            elif piece.startswith('\\') and len(piece) == 2:
                chars.append((piece[1], ital))
            else:
                chars.extend((ch, ital) for ch in re.sub(r'</?(?:em|i|b|strong|sup|sub|span|br)\b[^>]*>', '', piece))
        cur, it = [], []
        first = True
        for ch, f in chars + [(' ', False)]:
            ch = norm(ch)
            if not ch.strip() or ch in SPACES:
                if cur:
                    text = ''.join(cur)
                    up = ''.join(RAISED.findall(text))
                    streams[stream].append({'t': re.sub('[' + RAISE + SUPER + ']', '', text), 'i': sum(it) / len(it) if it else 0,
                                            'ln': ln, 'start': first, 'sec': section, 'up': ''.join(filter(str.isdigit, up)),
                                            'sup': SUPER[0] in text})
                    first = False
                cur, it = [], []
                continue
            cur.append(ch)
            if ch not in RAISE + SUPER:
                it.append(f)
    return streams


# ---------------------------------------------------------------- audit

def ctx(tokens, i, k=5) -> str:
    return ' '.join(t['t'] for t in tokens[max(0, i - k):i + k + 1])


def strip(t: str) -> str:
    return re.sub(r'^\W+|\W+$', '', t).lower()


def cmd_audit(args) -> None:
    tmp = Path(args.tmp)
    config = json.loads(Path(args.config).read_text()) if args.config else {}
    book = Book(tmp, config)
    md_path = Path(args.md)
    md = md_streams(md_path)
    pdf = pdf_streams(book, config)
    words = set()
    dict_path = Path('/usr/share/dict/words')
    if dict_path.exists():
        words = {w.strip().lower() for w in dict_path.read_text(errors='ignore').split()}
    front = set(config.get('front_pages', []))
    cands = []

    def add(cat, page, ln, pdf_text, md_text, context=''):
        cands.append({'category': cat, 'page': page, 'md_line': ln, 'pdf': pdf_text[:300], 'md': md_text[:300],
                      'context': context[:300]})

    aligned = []
    for name in ('body', 'note'):
        P, M = pdf[name], md[name]
        a = [key(t['t']) for t in P]
        b = [key(t['t']) for t in M]
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        pairs = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                pairs.extend((i1 + k, j1 + k) for k in range(i2 - i1))
                aligned.extend((P[i1 + k], M, j1 + k) for k in range(i2 - i1))
                continue
            pt = ' '.join(t['t'] for t in P[i1:i2])
            mt = ' '.join(t['t'] for t in M[j1:j2])
            if re.sub(r'\s', '', pt).lower() == re.sub(r'\s', '', mt).lower():
                continue
            page = P[i1]['p'] if i1 < len(P) else (P[-1]['p'] if P else None)
            ln = M[j1]['ln'] if j1 < len(M) else (M[-1]['ln'] if M else None)
            add(f'text_{name}', page, ln, pt, mt, ctx(P, i1))
        # section of each pdf token via alignment
        sec = [None] * len(P)
        for i, j in pairs:
            sec[i] = M[j]['sec']
        cur = 0
        for i in range(len(P)):
            if sec[i] is None:
                sec[i] = cur
            cur = sec[i]
        inline_h = collections.Counter()
        inline_w = collections.Counter()
        for i, t in enumerate(P):
            # 跨行断开的词只取去掉断行连字符后仍留在行内的连字符作依据
            w = t['jw'] if t.get('join') else strip(t['t'])
            if t.get('join') and '-' not in w:
                continue
            if '-' in w:
                inline_h[(sec[i], w)] += 1
            inline_w[(sec[i], w)] += 1
        for i, j in pairs:
            pt, mt = P[i], M[j]
            if pt['t'].lower() == mt['t'].lower() and pt['t'] != mt['t'] and not (pt.get('sc') and mt['t'] != mt['t'].lower()):
                add('case', pt['p'], mt['ln'], pt['t'], mt['t'], ctx(M, j))
            if pt.get('sc') and mt['t'] == mt['t'].lower() and any(c.isalpha() for c in mt['t']):
                add('smallcaps', pt['p'], mt['ln'], pt['t'], mt['t'], ctx(M, j))
            if abs(pt['i'] - mt['i']) > 0.5:
                add('italic', pt['p'], mt['ln'], pt['t'], mt['t'] + (' [正文斜体]' if mt['i'] > 0.5 else ' [正文非斜体]'), ctx(M, j))
            if pt.get('soft') and '-' not in mt['t']:
                add('soft_hyphen', pt['p'], mt['ln'], pt['t'], mt['t'], ctx(M, j))
            if pt.get('join'):
                mw = strip(mt['t'])
                jh, jw = pt['jh'], pt['jw']
                kept = mw == jh
                joined = mw == jw
                eh, ew = inline_h[(sec[i], jh)], inline_w[(sec[i], jw)] - ('-' in jw)
                if kept and ew and not eh:
                    add('hyphen_kept_vs_chapter', pt['p'], mt['ln'], pt['t'], mt['t'], ctx(M, j))
                elif joined and eh and not ew:
                    add('hyphen_joined_vs_chapter', pt['p'], mt['ln'], pt['t'], mt['t'], ctx(M, j))
                elif kept and not eh and not ew and jw in words and jh not in words:
                    add('hyphen_kept_dictionary_word', pt['p'], mt['ln'], pt['t'], mt['t'], ctx(M, j))
            if name == 'body' and pt['p'] in front:
                continue
            if mt['start'] != pt['start'] and (mt['start'] or pt['ls']):
                cat = f'paragraph_{name}_md_only' if mt['start'] else f'paragraph_{name}_pdf_only'
                add(cat, pt['p'], mt['ln'], pt['t'], mt['t'], ctx(M, j))
    # 上标数字与正文数字共用字符编码、字号和基线，只能凭字宽区分：以正文脚注引用号位置上的数字字宽为上标字宽
    seen, raised = collections.Counter(), collections.Counter()
    for pt, M, j in aligned:
        for k, g in enumerate(pt['dg']):
            seen[g] += 1
            raised[g] += k >= len(pt['dg']) - len(M[j].get('up', ''))
    superior = {g for g in seen if raised[g] >= max(2, RAISED_SHARE * seen[g])}
    sup_pages = set()
    for pt, M, j in aligned:
        up = ''.join(g[0] for g in pt['dg'] if g in superior)
        if up != M[j].get('up', ''):
            add('superscript', pt['p'], M[j]['ln'], f"{pt['t']} [上标 {up or '无'}]", f"{M[j]['t']} [上标 {M[j].get('up') or '无'}]",
                ctx(M, j))
        if M[j].get('sup'):
            sup_pages.add(pt['p'])
    # markdown-only checks
    text = md_path.read_text()
    refs = re.findall(r'\[\^([^\]]+)\](?!:)', text)
    defs = re.findall(r'^\[\^([^\]]+)\]:', text, re.M)
    for r in sorted(set(refs) - set(defs)):
        add('footnote', None, None, '', f'[^{r}] 无定义')
    for d in sorted(set(defs) - set(refs)):
        add('footnote', None, None, '', f'[^{d}] 无引用')
    for d, c in collections.Counter(defs).items():
        if c > 1:
            add('footnote', None, None, '', f'[^{d}] 重复定义 {c} 次')
    cyr = lambda ch: '\u0400' <= ch <= '\u04ff'
    for ln, line in enumerate(text.split('\n'), 1):
        for w in re.findall(r'\w+', line):
            if any(cyr(ch) for ch in w) and any(ch.isascii() and ch.isalpha() for ch in w):
                add('mixed_script', None, ln, '', w)
        body = re.sub(r'\\.', '', line)
        if re.fullmatch(r'\*(\s*\*){2,}', body.strip()):
            continue
        if re.search(r'\*\*\s+\*\*\*|\*{4,}|\*\*\*\s+\*\*', body) or body.count('*') % 2:
            add('markdown', None, ln, '', line[:200])
    accept = config.get('accept', [])
    kept = []
    for c in cands:
        if any(a.get('category') == c['category'] and a.get('page', c['page']) == c['page']
               and a.get('pdf', c['pdf']) == c['pdf'] and a.get('md', c['md']) == c['md'] for a in accept):
            continue
        kept.append(c)
    summary = collections.Counter(c['category'] for c in kept)
    report = {'md': str(md_path), 'summary': dict(sorted(summary.items())), 'candidates': kept,
              'superscript_pages': sorted(sup_pages)}
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f'正文字号 {book.body_size}；PDF 词 {len(pdf["body"])}+{len(pdf["note"])}，正文词 {len(md["body"])}+{len(md["note"])}')
    for k, v in sorted(summary.items()):
        print(f'  {k}: {v}')
    print(f'候选共 {len(kept)} 条，写入 {args.out}。候选只作核对线索，须按页面对象和页面渲染判定。')


def cmd_show(args) -> None:
    report = json.loads(Path(args.report).read_text())
    shown = 0
    for c in report['candidates']:
        if args.category and c['category'] != args.category:
            continue
        print(f"{c['category']} p{c['page']} L{c['md_line']} | PDF: {c['pdf'][:120]} | MD: {c['md'][:120]}")
        shown += 1
        if args.limit and shown >= args.limit:
            break


# ---------------------------------------------------------------- targets

def cmd_targets(args) -> None:
    tmp = Path(args.tmp)
    config = json.loads(Path(args.config).read_text()) if args.config else {}
    book = Book(tmp, config)
    targets = collections.defaultdict(set)
    for n in config.get('front_pages', []):
        targets[n].add('front')
    for n in page_set(config, book):
        rec = book.pages[n]
        chars = rec['chars']
        if any(c[2] >= 1.3 * book.body_size and c[0].strip() for c in chars):
            targets[n].add('large_type')
        if rec['images']:
            targets[n].add('image')
        if rec['curves'] > 5 or rec['rects'] > 5 or len(rec['rules']) > 4:
            targets[n].add('vector_graphics')
        if book.page_lines(n)['two_column']:
            targets[n].add('two_column')
        if rec['rot'] or any(not c[7] for c in chars if c[0].strip()):
            targets[n].add('rotated')
        if any(c[8] for c in chars if c[0].strip()):
            targets[n].add('white_text')
        if any(c[3] < 0 or c[4] > rec['w'] or c[5] < 0 or c[6] > rec['h'] for c in chars if c[0].strip()):
            targets[n].add('outside_page')
        seen = collections.Counter((c[0], round(c[3], 1), round(c[5], 1)) for c in chars if c[0].strip())
        if any(v > 1 for v in seen.values()):
            targets[n].add('overlap')
        if any('\ufffd' in c[0] or '(cid:' in c[0] for c in chars):
            targets[n].add('unmapped_glyph')
    if args.report:
        report = json.loads(Path(args.report).read_text())
        for c in report['candidates']:
            if c['page']:
                targets[c['page']].add('candidate')
        for n in report.get('superscript_pages', []):
            targets[n].add('superscript')
    out = {str(k): sorted(v) for k, v in sorted(targets.items())}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    reasons = collections.Counter(r for v in out.values() for r in v)
    print(f'须定向对照 {len(out)} 页：' + '，'.join(f'{k} {v}' for k, v in sorted(reasons.items())))


# ---------------------------------------------------------------- crop

def cmd_crop(args) -> None:
    import pdfplumber

    want = re.sub(r'\s', '', args.find)
    with pdfplumber.open(args.pdf) as doc:
        page = doc.pages[args.page - 1]
        for line in page.extract_text_lines():
            if want in re.sub(r'\s', '', line['text']):
                top, bottom = line['top'], line['bottom']
                break
        else:
            fail(f'第 {args.page} 页未找到：{args.find}')
        w, h = float(page.width), float(page.height)
    scale = args.dpi / 72
    pad = (bottom - top) * (0.5 + 1.4 * args.lines)
    x, y = 0, max(0, top - pad)
    W, H = w, min(h, bottom + pad) - y
    out = Path(args.out)
    with tempfile.TemporaryDirectory() as d:
        stem = Path(d) / 'crop'
        subprocess.run(['pdftoppm', '-f', str(args.page), '-l', str(args.page), '-r', str(args.dpi), '-png',
                        '-singlefile', '-x', str(int(x * scale)), '-y', str(int(y * scale)),
                        '-W', str(int(W * scale)), '-H', str(int(H * scale)), args.pdf, str(stem)], check=True)
        out.write_bytes(stem.with_suffix('.png').read_bytes())
    print(f'已输出 {out}')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('extract')
    p.add_argument('pdf')
    p.add_argument('--work-json', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('audit')
    p.add_argument('tmp')
    p.add_argument('--md', required=True)
    p.add_argument('--config')
    p.add_argument('--out', required=True)
    p = sub.add_parser('show')
    p.add_argument('report')
    p.add_argument('--category')
    p.add_argument('--limit', type=int)
    p = sub.add_parser('targets')
    p.add_argument('tmp')
    p.add_argument('--config')
    p.add_argument('--report')
    p.add_argument('--out', required=True)
    p = sub.add_parser('crop')
    p.add_argument('pdf')
    p.add_argument('--page', type=int, required=True)
    p.add_argument('--find', required=True)
    p.add_argument('--dpi', type=int, default=300)
    p.add_argument('--lines', type=int, default=2)
    p.add_argument('--out', required=True)
    args = ap.parse_args()
    {'extract': cmd_extract, 'audit': cmd_audit, 'show': cmd_show, 'targets': cmd_targets, 'crop': cmd_crop}[args.cmd](args)


if __name__ == '__main__':
    main()


SCHEMA = """
audit.json（放在该书临时目录，不进版本控制）：

{
  "body_pages": [首页, 末页],          # 进入比对的物理页范围；缺省为全书
  "exclude_pages": [页, ...],          # 不进正文的页：封面、版权页、空白页等
  "front_pages": [页, ...],            # 前置页与目录页：只作定向对照，不作段落比对
  "entry_ranges": [                    # 条目式版面
    {"pages": [首页, 末页], "kind": "hanging"},   # 悬挂缩进条目（参考文献、著述目录）
    {"pages": [首页, 末页], "kind": "index"}      # 索引：顶层与子条目各自成条，转行并入
  ],
  "accept": [                          # 已确认无需修改的残余候选，按类别与片段匹配；给出 page 时只匹配该物理页
    {"category": "text_body", "page": 页, "pdf": "PDF 片段", "md": "正文片段"}
  ]
}
"""
