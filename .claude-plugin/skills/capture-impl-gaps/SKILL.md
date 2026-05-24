---
name: capture-impl-gaps
description: Detect spec→impl gaps by invoking the sibling detect-impl-gaps thin-transport skill, then file gap-tied work-items into the JSONL store with per-gap user consent. Required heavyweight authored skill per livespec/SPECIFICATION/contracts.md §"Heavyweight authored skills (6)". Invoke as `/livespec-impl-plaintext:capture-impl-gaps`.
allowed-tools: Bash, Read, Grep, Glob, Write
---

# capture-impl-gaps

Mechanical detection of spec→impl gaps. Heavyweight skill — orchestration
lives here in the SKILL.md prose per
SPECIFICATION/constraints.md §"Skill orchestration constraints". The
plugin's `detect-impl-gaps` thin-transport sibling and `store` module are
the load-bearing surfaces this skill composes.

## Pre-requisites

- The consumer project has a `<spec-root>/` directory at the path
  declared in `.livespec.jsonc` (default: `SPECIFICATION/`).
- The `livespec-impl-plaintext` Python package is on the import path
  (uv-managed; verified by `uv run python3 -c "import
  livespec_impl_plaintext"`).
- The work-items JSONL store path is reachable (created on first
  append if absent).

## Flow

### Step 1 — Enumerate gap candidates via detect-impl-gaps

Invoke the sibling thin-transport skill `detect-impl-gaps` to retrieve
the authoritative gap-id set. Per SPECIFICATION/contracts.md
§"capture-impl-gaps", both this skill and the doctor invariants consume
the same canonical surface; in-skill duplication of the detection logic
is forbidden.

Run the skill twice — once with `--json` for the authoritative gap-id
set, once without for the rich line form used to surface each candidate
to the user in Step 2:

```bash
# Authoritative gap-id set:
uv run python3 .claude-plugin/scripts/bin/detect_impl_gaps.py --json
# → {"gap_ids": ["gap-abc123", "gap-def456", ...]}

# Rich human-readable context for display:
uv run python3 .claude-plugin/scripts/bin/detect_impl_gaps.py
# → each line: <spec-file> > <heading-path>  [<gap_id>]  <rule-text>
```

Both invocations use the same canonical `detect_rules` function and
emit deterministically-sorted output, so the two outputs can be joined
by `gap_id` to produce a candidate list of
`(gap_id, spec_file, heading_path, rule_text)` tuples. The `--json`
form is the authoritative set; the rich form is convenience metadata
for human display.

### Step 2 — Per-rule gap classification

For each candidate, ask the user:

> Is the implementation honoring this rule? (yes / no / skip)

- `yes` — no gap; move on.
- `no` — a gap exists. Proceed to Step 3.
- `skip` — defer judgment; move on without filing.

### Step 3 — Per-gap consent + filing

For each `no` rule, the `gap_id` is already in hand from Step 1 (derived
inside `detect-impl-gaps` from `<spec-file>\x1f<heading-path>\x1f<rule-text>`
hashing; shape `gap-<8-char-base32-suffix>`). Then:

1. Check the work-items store: if a record with this `gap_id` already
   exists and is not closed, surface "already filed as `<li-id>`" and
   skip filing.
2. Otherwise, ask the user to confirm title + description (auto-drafted
   from the rule text). Defaults are pre-filled; the user accepts or
   edits.
3. On confirm, append a new work-item JSONL record:

```python
from livespec_impl_plaintext._ids import new_work_item_id
from livespec_impl_plaintext.store import append_work_item
from livespec_impl_plaintext.types import WorkItem
from datetime import datetime, timezone
from pathlib import Path

item = WorkItem(
    id=new_work_item_id(),
    type="task",
    status="open",
    title=user_confirmed_title,
    description=user_confirmed_description,
    origin="gap-tied",
    gap_id=gap_id,
    priority=2,
    assignee=None,
    depends_on=(),
    captured_at=datetime.now(tz=timezone.utc).isoformat(),
    resolution=None,
    reason=None,
    audit=None,
    superseded_by=None,
)
append_work_item(path=Path("work-items.jsonl"), item=item)
```

### Step 4 — Summary

When all candidates are processed, print a summary:

- N candidate rules surfaced
- M classified as gaps, of which K were newly filed and J were already-tracked
- Skipped: S

## Important properties

- **In-memory ephemeral detection state** — no persistent intermediate
  artifact. The candidate list is discarded at skill exit per
  livespec/SPECIFICATION/contracts.md §"Heavyweight authored
  skills (6)" → capture-impl-gaps.
- **Per-gap user consent is REQUIRED** — never auto-file without
  explicit confirmation.
- **Idempotent** — re-running surfaces no duplicates for gaps already
  tracked (status≠closed).
- **No LLM in the detection path itself** — pattern-matching of MUST /
  SHOULD clauses is deterministic. LLM dialogue is used only for the
  classification and authoring steps (and only with user-in-the-loop).

## What this skill does NOT do

- Does NOT close work-items. Use `implement` for that.
- Does NOT modify the spec tree (all spec reads are delegated to
  `detect-impl-gaps`).
- Does NOT detect impl→spec drift. That's `capture-spec-drift`.
