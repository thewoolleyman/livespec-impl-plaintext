"""`/livespec-impl-plaintext:list-work-items` thin-transport command.

CLI surface per SPECIFICATION/contracts.md §"list-work-items":

  list-work-items [--filter <name>] [--with-gap-id <id>] [--json]
                  [--work-items-path <path>]

Filters:

- `--filter=gap-tied` / `--filter=freeform` — origin filter
- `--filter=blocked` — status == "blocked"
- `--filter=ready` — status == "open" AND every depends_on item is closed
- `--filter=closed` — status == "closed"
- `--filter=all` (default)

`--with-gap-id=<id>` filters to exact gap_id match (combinable with --filter).

Output:

- Default: one-line summary per work-item.
- `--json`: an array of work-item materialized views.
"""

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from livespec_impl_plaintext.commands._config import resolve_store_config
from livespec_impl_plaintext.errors import StoreFileMissingError
from livespec_impl_plaintext.store import materialize_work_items, read_work_items
from livespec_impl_plaintext.types import WorkItem

FilterChoice = Literal["all", "gap-tied", "freeform", "blocked", "ready", "closed"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="list-work-items")
    _ = parser.add_argument(
        "--filter",
        dest="filter_name",
        default="all",
        choices=["all", "gap-tied", "freeform", "blocked", "ready", "closed"],
    )
    _ = parser.add_argument("--with-gap-id", dest="with_gap_id", default=None)
    _ = parser.add_argument("--json", dest="as_json", action="store_true")
    _ = parser.add_argument("--work-items-path", dest="work_items_path", default=None)
    args = parser.parse_args(argv)
    config = resolve_store_config(
        cwd=Path.cwd(),
        work_items_arg=args.work_items_path,
        memos_arg=None,
    )
    materialized = _load_work_items(path=config.work_items_path)
    filtered = _filter_work_items(
        materialized=materialized,
        name=args.filter_name,
        with_gap_id=args.with_gap_id,
    )
    if args.as_json:
        _write_json(items=filtered)
    else:
        _write_human(items=filtered)
    return 0


def _load_work_items(*, path: Path) -> list[WorkItem]:
    try:
        return list(materialize_work_items(read_work_items(path=path)).values())
    except StoreFileMissingError:
        return []


def _filter_work_items(
    *,
    materialized: list[WorkItem],
    name: str,
    with_gap_id: str | None,
) -> list[WorkItem]:
    by_name = _filter_by_name(materialized=materialized, name=name)
    if with_gap_id is None:
        return by_name
    return [item for item in by_name if item.gap_id == with_gap_id]


def _filter_by_name(*, materialized: list[WorkItem], name: str) -> list[WorkItem]:
    predicates: dict[str, Callable[[WorkItem, dict[str, WorkItem]], bool]] = {
        "all": lambda _item, _ix: True,
        "gap-tied": lambda item, _ix: item.origin == "gap-tied",
        "freeform": lambda item, _ix: item.origin == "freeform",
        "blocked": lambda item, _ix: item.status == "blocked",
        "ready": lambda item, ix: item.status == "open"
        and all((ix[dep].status == "closed") if dep in ix else False for dep in item.depends_on),
        "closed": lambda item, _ix: item.status == "closed",
    }
    predicate = predicates[name]
    index = {item.id: item for item in materialized}
    return [item for item in materialized if predicate(item, index)]


def _write_json(*, items: list[WorkItem]) -> None:
    payload = [_work_item_to_dict(item=item) for item in items]
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_human(*, items: list[WorkItem]) -> None:
    if not items:
        _ = sys.stdout.write("(no work-items)\n")
        return
    for item in items:
        gap_marker = f" gap={item.gap_id}" if item.gap_id is not None else ""
        line = (
            f"{item.id}  [{item.status}/P{item.priority}/{item.origin}{gap_marker}]"
            f"  {item.title}\n"
        )
        _ = sys.stdout.write(line)


def _work_item_to_dict(*, item: WorkItem) -> dict[str, object]:
    payload = asdict(item)
    payload["depends_on"] = list(item.depends_on)
    if item.audit is not None:
        payload["audit"] = {
            "verification_timestamp": item.audit.verification_timestamp,
            "commits": list(item.audit.commits),
            "files_changed": list(item.audit.files_changed),
        }
    return payload
