"""`/livespec-impl-plaintext:detect-impl-gaps` thin-transport command.

CLI surface per SPECIFICATION/contracts.md §"detect-impl-gaps":

  detect-impl-gaps [--spec-target <path>] [--project-root <path>] [--json]

Reads the live Specification via the Spec Reader, enumerates every
MUST / MUST NOT / SHOULD / SHOULD NOT rule, and emits the resulting
gap-id set. Gap-id derivation is a pure function of the spec-file
path + canonical heading path + rule text; the same rule text in the
same context always yields the same gap-id across runs.

The skill is the canonical gap-detection surface for the plugin.
Consumed by:

- `livespec` doctor's `gap-tracking-one-to-one` and
  `no-stale-gap-tied` invariants via subprocess.
- The heavyweight `capture-impl-gaps` sibling as its detection
  step.
- The heavyweight `implement` skill at gap-tied closure
  verification.

The skill is intrinsically non-mutating: no JSONL writes, no user
prompts, no spec modifications.
"""

import argparse
import hashlib
import json
import re
import sys
from base64 import b32encode
from dataclasses import dataclass
from pathlib import Path

from livespec_impl_plaintext.spec_reader import read_current_specification

_RULE_KEYWORD_PATTERN = re.compile(r"\b(MUST NOT|SHOULD NOT|MUST|SHOULD)\b")
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CODE_FENCE_PATTERN = re.compile(r"^\s*```")
_GAP_ID_LENGTH = 8


@dataclass(frozen=True, kw_only=True)
class RuleMatch:
    """A single MUST/SHOULD rule detected in the spec."""

    spec_file: str
    heading_path: str
    line_text: str
    gap_id: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="detect-impl-gaps")
    _ = parser.add_argument(
        "--spec-target",
        dest="spec_target",
        default=None,
        help="Path to the spec tree (default: SPECIFICATION/ under --project-root).",
    )
    _ = parser.add_argument(
        "--project-root",
        dest="project_root",
        default=None,
        help="Project root (default: current working directory).",
    )
    _ = parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help='Emit JSON `{"gap_ids": [...]}` instead of human-readable lines.',
    )
    args = parser.parse_args(argv)
    project_root = Path(args.project_root) if args.project_root is not None else Path.cwd()
    spec_root = (
        Path(args.spec_target) if args.spec_target is not None else project_root / "SPECIFICATION"
    )
    rules = detect_rules(spec_root=spec_root)
    if args.as_json:
        _write_json(rules=rules)
    else:
        _write_human(rules=rules)
    return 0


def detect_rules(*, spec_root: Path) -> list[RuleMatch]:
    """Enumerate every MUST/SHOULD rule in the live spec tree.

    Returns rules sorted by (spec_file, heading_path, line_text) so
    output ordering is deterministic across runs and platforms.
    """
    snapshot = read_current_specification(spec_root=spec_root)
    rules: list[RuleMatch] = []
    for spec_file in sorted(snapshot.files.keys()):
        if not spec_file.endswith(".md"):
            continue
        content = snapshot.files[spec_file]
        rules.extend(_extract_rules_from_file(spec_file=spec_file, content=content))
    rules.sort(key=lambda rule: (rule.spec_file, rule.heading_path, rule.line_text))
    return rules


def _extract_rules_from_file(*, spec_file: str, content: str) -> list[RuleMatch]:
    rules: list[RuleMatch] = []
    heading_stack: list[str] = []
    in_code_fence = False
    for raw_line in content.splitlines():
        if _CODE_FENCE_PATTERN.match(raw_line):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        heading_match = _HEADING_PATTERN.match(raw_line)
        if heading_match is not None:
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            _push_heading(stack=heading_stack, level=level, title=title)
            continue
        if _RULE_KEYWORD_PATTERN.search(raw_line) is None:
            continue
        rule_text = raw_line.strip()
        heading_path = " > ".join(heading_stack) if heading_stack else "(top)"
        gap_id = _derive_gap_id(spec_file=spec_file, heading_path=heading_path, rule_text=rule_text)
        rules.append(
            RuleMatch(
                spec_file=spec_file,
                heading_path=heading_path,
                line_text=rule_text,
                gap_id=gap_id,
            )
        )
    return rules


def _push_heading(*, stack: list[str], level: int, title: str) -> None:
    while len(stack) >= level:
        _ = stack.pop()
    while len(stack) < level - 1:
        stack.append("")
    stack.append(title)


def _derive_gap_id(*, spec_file: str, heading_path: str, rule_text: str) -> str:
    payload = f"{spec_file}\x1f{heading_path}\x1f{rule_text}".encode()
    digest = hashlib.sha256(payload).digest()
    suffix = b32encode(digest).decode("ascii").rstrip("=").lower()[:_GAP_ID_LENGTH]
    return f"gap-{suffix}"


def _write_json(*, rules: list[RuleMatch]) -> None:
    payload = {"gap_ids": [rule.gap_id for rule in rules]}
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_human(*, rules: list[RuleMatch]) -> None:
    if not rules:
        _ = sys.stdout.write("(no rules detected)\n")
        return
    for rule in rules:
        line = f"{rule.spec_file} > {rule.heading_path}  [{rule.gap_id}]  {rule.line_text}\n"
        _ = sys.stdout.write(line)
