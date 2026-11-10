#!/usr/bin/env python3
"""术语表与交换格式之间的导出和导入。

    glossary_io.py export 术语目录或文件… > glossary.json
    glossary_io.py import glossary.json 术语目录 [--skip-existing] [--approved] [-n]

交换格式是词条数组，每条含 collection（来源表名，即文件名去掉 .json）、id、canonical、forms、
zh_preferred、zh_alternatives、notes；collection 为 glossary 时另含 type。不含 status。

export 只输出 status 为 approved 的词条，写到标准输出。给出目录时读取其中全部 .json，
按 glossary、terms、其余表名的顺序输出。

import 把词条写入术语目录中与 collection 同名的表，状态为 provisional；--approved 写为
approved。同一表中已有相同 id 时整体停止；--skip-existing 跳过这些词条。输入文件为 - 时读取
标准输入。成功时不输出；-n 列出将写入的 collection/id，不写入。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
TYPES = {"person", "organization", "institution", "work", "journal"}
COMMON_FIELDS = ["id", "canonical", "forms", "zh_preferred", "zh_alternatives"]
EXCHANGE_FIELDS = ["collection", *COMMON_FIELDS, "notes", "type"]


def fail(message: str) -> None:
    print(f"glossary_io.py: {message}", file=sys.stderr)
    sys.exit(1)


def dump(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_list(path: Path) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path}：无法读取 JSON（{error}）")
    if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
        fail(f"{path}：须为词条对象数组")
    return data


def check_fields(entry: dict, collection: str, where: str) -> list[str]:
    """按交换格式核对公开字段，返回问题列表。"""
    problems = []
    if not isinstance(entry.get("id"), str) or not SLUG.fullmatch(entry["id"]):
        problems.append("id 须为小写字母、数字和连字符")
    for key in ("canonical", "zh_preferred"):
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            problems.append(f"{key} 须为非空字符串")
    for key in ("forms", "zh_alternatives"):
        value = entry.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
            problems.append(f"{key} 须为非空字符串组成的数组")
    if not isinstance(entry.get("notes", ""), str):
        problems.append("notes 须为字符串")
    if collection == "glossary":
        if entry.get("type") not in TYPES:
            problems.append("glossary 的 type 须为 " + "、".join(sorted(TYPES)))
    return [f"{where}：{p}" for p in problems]


def collections_of(paths: list[str]) -> list[tuple[str, Path]]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found = sorted(path.glob("*.json"))
            rank = {"glossary": 0, "terms": 1}
            files += sorted(found, key=lambda p: (rank.get(p.stem, 2), p.stem))
        elif path.is_file():
            files.append(path)
        else:
            fail(f"找不到 {path}")
    result = []
    for file in files:
        if not SLUG.fullmatch(file.stem):
            fail(f"{file}：表名须为小写字母、数字和连字符")
        result.append((file.stem, file))
    seen = [name for name, _ in result]
    duplicates = sorted({n for n in seen if seen.count(n) > 1})
    if duplicates:
        fail("表名重复：" + "、".join(duplicates))
    return result


def cmd_export(args: argparse.Namespace) -> None:
    out, problems = [], []
    for collection, path in collections_of(args.paths):
        ids: set[str] = set()
        for index, entry in enumerate(load_list(path)):
            if entry.get("status") != "approved":
                continue
            where = f"{path} 第 {index + 1} 条"
            problems += check_fields(entry, collection, where)
            if entry.get("id") in ids:
                problems.append(f"{where}：id 重复")
            ids.add(entry.get("id"))
            item = {"collection": collection, **{k: entry.get(k) for k in COMMON_FIELDS},
                    "notes": entry.get("notes", "")}
            if collection == "glossary":
                item["type"] = entry.get("type")
            out.append(item)
    if problems:
        fail("approved 词条字段无效，未输出：\n  " + "\n  ".join(problems))
    sys.stdout.write(dump(out))


def cmd_import(args: argparse.Namespace) -> None:
    target = Path(args.directory)
    if not target.is_dir():
        fail(f"术语目录 {target} 不存在")
    if args.file == "-":
        try:
            entries = json.loads(sys.stdin.read())
        except json.JSONDecodeError as error:
            fail(f"标准输入：无法读取 JSON（{error}）")
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            fail("标准输入：须为词条对象数组")
    else:
        entries = load_list(Path(args.file))

    problems, seen = [], set()
    for index, entry in enumerate(entries):
        where = f"第 {index + 1} 条"
        collection = entry.get("collection")
        if not isinstance(collection, str) or not SLUG.fullmatch(collection):
            problems.append(f"{where}：collection 须为小写字母、数字和连字符")
            continue
        extra = sorted(set(entry) - set(EXCHANGE_FIELDS))
        if extra:
            problems.append(f"{where}：未知字段 " + "、".join(extra))
        if "type" in entry and collection != "glossary":
            problems.append(f"{where}：type 只用于 glossary")
        problems += check_fields(entry, collection, where)
        key = (collection, entry.get("id"))
        if key in seen:
            problems.append(f"{where}：{collection}/{entry.get('id')} 重复")
        seen.add(key)
    if problems:
        fail("输入无效，未写入：\n  " + "\n  ".join(problems))

    tables: dict[str, list] = {}
    for collection in dict.fromkeys(e["collection"] for e in entries):
        path = target / f"{collection}.json"
        tables[collection] = load_list(path) if path.exists() else []
    existing = {(c, e.get("id")) for c, table in tables.items() for e in table}
    conflicts = [f"{e['collection']}/{e['id']}" for e in entries if (e["collection"], e["id"]) in existing]
    if conflicts and not args.skip_existing:
        fail(f"术语表中已有 {len(conflicts)} 个相同词条，未写入（可用 --skip-existing 跳过）：\n  "
             + "\n  ".join(conflicts))

    status = "approved" if args.approved else "provisional"
    added: dict[str, list] = {}
    for entry in entries:
        if (entry["collection"], entry["id"]) in existing:
            continue
        item = {"id": entry["id"]}
        if entry["collection"] == "glossary":
            item["type"] = entry["type"]
        item.update({k: entry[k] for k in COMMON_FIELDS[1:]})
        item.update(status=status, notes=entry.get("notes", ""))
        added.setdefault(entry["collection"], []).append(item)

    if args.dry_run:
        for collection, items in added.items():
            for item in items:
                print(f"{collection}/{item['id']}")
        return
    for collection, items in added.items():
        path = target / f"{collection}.json"
        handle, temp = tempfile.mkstemp(dir=target, prefix=f".{collection}.", suffix=".json")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(dump(tables[collection] + items))
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(temp, path.stat().st_mode & 0o777 if path.exists() else 0o666 & ~umask)
        os.replace(temp, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("export", help="导出 approved 词条到标准输出")
    p.add_argument("paths", nargs="+", help="术语目录或术语表文件")
    p = sub.add_parser("import", help="把交换格式的词条写入术语目录")
    p.add_argument("file", help="交换格式文件；- 表示标准输入")
    p.add_argument("directory", help="术语目录")
    p.add_argument("--skip-existing", action="store_true", help="跳过术语表中已有 id 的词条")
    p.add_argument("--approved", action="store_true", help="写为 approved；仅在 Owner 明确批准时使用")
    p.add_argument("-n", "--dry-run", action="store_true", help="列出将写入的词条，不写入")
    args = parser.parse_args()
    {"export": cmd_export, "import": cmd_import}[args.command](args)


if __name__ == "__main__":
    main()
