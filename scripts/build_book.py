#!/usr/bin/env python3
r"""编译一个成书项目并报告验收指标。

现在的成书是原地手工维护的 tex（`main.tex` + `preamble.tex` + 各章 .tex），
没有装配层，本脚本只负责编译与验收：

* **跑两遍 xelatex** —— 目录、书眉、交叉引用都要第二遍才稳定；
  封面用 `remember picture` 时第一遍算不出坐标，出来几乎是空白页。
* **缺字形必须是 0** —— 缺字形不报错，只在 log 里留一行，付印才发现。
* 报出页数、开本、实际嵌入的字体 —— 换字体或改版式后用来对比基线。

用法：
    python3 scripts/build_book.py book/projects/某书
    python3 scripts/build_book.py book/projects/某书 --passes 3
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="编译成书并报告验收指标")
    ap.add_argument("project", type=Path, help="含 main.tex 的目录")
    ap.add_argument("--tex", default="main.tex", help="主文件名（默认 main.tex）")
    ap.add_argument("--passes", type=int, default=2, help="xelatex 遍数（默认 2）")
    args = ap.parse_args()

    proj = args.project.resolve()
    main_tex = proj / args.tex
    if not main_tex.is_file():
        print(f"找不到 {main_tex}", file=sys.stderr)
        return 2

    for i in range(1, args.passes + 1):
        r = run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", args.tex], proj)
        if r.returncode != 0:
            tail = "\n".join(r.stdout.splitlines()[-25:])
            print(f"第 {i} 遍 xelatex 失败：\n{tail}", file=sys.stderr)
            return 1
        print(f"  第 {i} 遍 xelatex 完成")

    stem = Path(args.tex).stem
    log = (proj / f"{stem}.log").read_text(encoding="utf-8", errors="replace")
    missing = len(re.findall(r"Missing character", log))
    over = len(re.findall(r"Overfull \\hbox", log))
    under = len(re.findall(r"Underfull \\vbox", log))

    pdf = proj / f"{stem}.pdf"
    info = run(["pdfinfo", str(pdf)], proj).stdout
    pages = (re.search(r"Pages:\s+(\d+)", info) or [None, "?"])[1]
    size = (re.search(r"Page size:\s+(.*)", info) or [None, "?"])[1].strip()
    fonts = [l.split()[0] for l in run(["pdffonts", str(pdf)], proj).stdout.splitlines()[2:] if l.strip()]

    print(f"\n{pdf.relative_to(Path.cwd()) if pdf.is_relative_to(Path.cwd()) else pdf}")
    print(f"  页数        {pages}")
    print(f"  开本        {size}")
    print(f"  缺字形      {missing}" + ("" if missing == 0 else "   ← 必须清零"))
    print(f"  Overfull    {over}")
    print(f"  Underfull   {under}")
    print(f"  嵌入字体    {len(fonts)}")
    for f in fonts:
        print(f"                {f}")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
