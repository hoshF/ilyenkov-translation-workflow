#!/usr/bin/env python3
"""建立翻译项目，或向已有项目加入一部作品。

    new_project.py article 项目目录 --work-id ID --title 题名 [--source 原文.md]
    new_project.py book    项目目录 --work-id ID --title 题名

新项目写入 AGENTS.md、CLAUDE.md、.gitignore、空术语表和 workflow/ 规范副本；已有项目只加入作品。
文章写 translation/ID/work.json（及 source/ID.md），书籍写 source/ID/work.json。
目标已存在时不写入任何文件。成功时不输出；-n 列出将写入的文件。
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = "WORKFLOW_VERSION.txt"
WORK_ID = re.compile(r"[a-z0-9][a-z0-9-]*")

# 复制进 workflow/ 的规范、工具、模板与示例。
WORKFLOW_ENTRIES = [
    "AGENTS.md", "STRUCTURE.md", "AGENT_TASKS.md", "README.md", "CHANGELOG.md", "SOURCE_MAP.md",
    "LICENSE",
    "translation", "digitization", "glossary", "book", "scripts", "examples",
]
SKIP_NAMES = {"__pycache__", ".DS_Store"}
SKIP_SUFFIXES = {".pyc", ".aux", ".log", ".out", ".toc", ".xdv", ".fls", ".pdf"}

PROJECT_AGENTS = """\
# 翻译项目

本目录是独立的翻译项目。工作流规范在 `workflow/`，版本见 `workflow/WORKFLOW_VERSION.txt`。

## 开始任务前

1. 完整阅读 [`workflow/AGENTS.md`](workflow/AGENTS.md)，再按其中「动手之前先读」读取当前任务的规范。
2. 规范文件中的相对链接指向 `workflow/` 内的文件；规范所说的工作区位置按下表对应到本项目。
3. 执行 Owner 交代的角色和步骤，到该步骤的停止条件停止。

任务指令模板见 [`workflow/AGENT_TASKS.md`](workflow/AGENT_TASKS.md)。

## 位置对应

| 规范中的位置 | 本项目 |
| --- | --- |
| 单篇文章原文 | `source/<work-id>.md` |
| 书籍原文作品目录 | `source/<work-id>/` |
| 译文作品目录 | `translation/<work-id>/` |
| 术语目录（规范中的 `glossary/`） | `glossary/` |
| 本地底本目录 | `originals/`（不进 Git） |
| 临时目录 | `tmp/<任务>/`（不进 Git） |
| 成书工程目录 | `book/<work-id>/` |

`workflow/` 是规范副本；翻译任务中保持其中文件不变。

## 工具

在本项目根目录调用，例如 `python3 workflow/scripts/md_to_latex.py 译文.md -o tmp/章节.tex`。依赖、输入与输出见 [`workflow/scripts/README.md`](workflow/scripts/README.md)。

## Git

本项目是独立的 Git 仓库，主分支为 `main`。书籍翻译与统稿的分支、提交与合并依规范在本仓库执行；其他工作在 Owner 明确要求时提交。
"""

PROJECT_CLAUDE = "@AGENTS.md\n"

PROJECT_GITIGNORE = """\
# 本地底本与临时文件
/originals/
/tmp/

# Python 与 LaTeX 生成文件
__pycache__/
*.aux
*.log
*.out
*.toc
*.xdv
*.fls
*.fdb_latexmk
*.synctex.gz
*.draft.tex
"""


def fail(message: str) -> None:
    print(f"new_project.py: {message}", file=sys.stderr)
    sys.exit(1)


def git_output(*args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def version_text() -> str:
    toplevel = git_output("rev-parse", "--show-toplevel")
    commit = git_output("rev-parse", "HEAD") if toplevel and Path(toplevel).resolve() == ROOT else None
    if commit is None:
        state = "提交：未知（复制来源不是 Git 检出）"
    else:
        dirty = git_output("status", "--porcelain", "--", *WORKFLOW_ENTRIES)
        state = f"提交：{commit}" + ("（复制时有未提交修改）" if dirty else "")
    return (
        "本目录复制自 ilyenkov-translation-workflow。\n"
        f"{state}\n"
        f"复制日期：{datetime.date.today().isoformat()}\n"
        "许可：MIT，见 LICENSE。\n"
    )


def workflow_files() -> list[Path]:
    files = []
    for entry in WORKFLOW_ENTRIES:
        path = ROOT / entry
        if not path.exists():
            fail(f"工作流仓库缺少 {entry}")
        candidates = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        for file in candidates:
            rel = file.relative_to(ROOT)
            if SKIP_NAMES & set(rel.parts) or file.suffix in SKIP_SUFFIXES:
                continue
            files.append(rel)
    return files


def work_json(args: argparse.Namespace) -> str:
    data: dict[str, object] = {"work_id": args.work_id, "title": args.title}
    if args.kind == "article" and args.title_zh:
        data["title_zh"] = args.title_zh
    if args.year:
        data["year"] = int(args.year) if args.year.isdigit() else args.year
    if args.source_edition:
        data["source_edition"] = args.source_edition
    if args.source_url:
        data["source_url"] = args.source_url
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def is_project(directory: Path) -> bool:
    return (directory / "AGENTS.md").is_file() and (directory / "workflow" / VERSION_FILE).is_file()


def plan(args: argparse.Namespace, project: Path) -> list[tuple[Path, object]]:
    """返回 [(目标路径, 内容)]；内容为 str，或表示复制来源的 Path。"""
    if project.exists() and not project.is_dir():
        fail(f"{project} 已存在且不是目录")
    new = not project.exists() or not any(project.iterdir())
    if not new and not is_project(project):
        fail(f"{project} 非空，且不是翻译项目")

    items: list[tuple[Path, object]] = []
    if new:
        items += [
            (project / "AGENTS.md", PROJECT_AGENTS),
            (project / "CLAUDE.md", PROJECT_CLAUDE),
            (project / ".gitignore", PROJECT_GITIGNORE),
            (project / "glossary" / "glossary.json", "[]\n"),
            (project / "glossary" / "terms.json", "[]\n"),
            (project / "workflow" / VERSION_FILE, version_text()),
        ]
        items += [(project / "workflow" / rel, ROOT / rel) for rel in workflow_files()]

    if args.kind == "article":
        items.append((project / "translation" / args.work_id / "work.json", work_json(args)))
        if args.source:
            source = Path(args.source).expanduser()
            if not source.is_file():
                fail(f"找不到原文文件 {source}")
            items.append((project / "source" / f"{args.work_id}.md", source.resolve()))
    else:
        items.append((project / "source" / args.work_id / "work.json", work_json(args)))

    # 同一作品标识已占用的任何位置都视为冲突。
    work_paths = [project / "source" / f"{args.work_id}.md", project / "source" / args.work_id,
                  project / "translation" / args.work_id]
    taken = list(dict.fromkeys(p for p in work_paths + [p for p, _ in items] if p.exists()))
    if taken:
        fail("已存在，未写入：" + "、".join(str(p) for p in taken))
    return items


def write(items: list[tuple[Path, object]]) -> None:
    for target, content in items:
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, Path):
            with content.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
        else:
            with target.open("x", encoding="utf-8") as dst:
                dst.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["article", "book"], help="article：单篇文章；book：书籍")
    parser.add_argument("project", help="翻译项目目录，位于工作流仓库之外")
    parser.add_argument("--work-id", required=True, help="作品标识：小写字母、数字和连字符")
    parser.add_argument("--title", required=True, help="原文题名")
    parser.add_argument("--title-zh", help="正式中文题名（单篇文章）；译文一级标题与之一致")
    parser.add_argument("--year", help="出版年份")
    parser.add_argument("--source-edition", help="所用底本的版本或出处")
    parser.add_argument("--source-url", help="来源地址")
    parser.add_argument("--source", help="单篇文章：复制到项目中的原文 Markdown 文件")
    parser.add_argument("-n", "--dry-run", action="store_true", help="列出将写入的文件，不写入")
    args = parser.parse_args()

    if not WORK_ID.fullmatch(args.work_id):
        fail("--work-id 只用小写字母、数字和连字符")
    if args.kind == "book" and (args.source or args.title_zh):
        fail("book 不接受 --source、--title-zh")

    project = Path(args.project).expanduser().resolve()
    if project == ROOT or ROOT in project.parents:
        fail("项目目录须在工作流仓库之外")

    items = plan(args, project)
    if args.dry_run:
        for target, _ in items:
            print(target.relative_to(project))
        return
    write(items)


if __name__ == "__main__":
    main()
