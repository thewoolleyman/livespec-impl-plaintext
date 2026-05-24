---
name: detect-impl-gaps
description: Detect spec→impl gaps mechanically via the Spec Reader and emit the current gap-id set as JSON. Required thin-transport surface per livespec/SPECIFICATION/contracts.md §"Thin-transport skills (4) — required machine query surface". Pure read-and-emit pass-through — never mutates the work-items JSONL, never prompts the user. Invoke as `/livespec-impl-plaintext:detect-impl-gaps [--spec-target <path>] [--project-root <path>] [--json]`.
allowed-tools: Bash
---

# detect-impl-gaps

Thin-transport pass-through. All behavior lives in
`.claude-plugin/scripts/livespec_impl_plaintext/commands/detect_impl_gaps.py`.

## Invocation

```bash
uv run python3 .claude-plugin/scripts/bin/detect_impl_gaps.py "$@"
```

Supported flags:

- `--spec-target <path>` — path to the spec tree (default:
  `SPECIFICATION/` under `--project-root`).
- `--project-root <path>` — project root (default: current working
  directory).
- `--json` — emit `{"gap_ids": [...]}` JSON instead of
  human-readable lines.

## When to use

- Doctor's `gap-tracking-one-to-one` and `no-stale-gap-tied`
  invariants subprocess `detect-impl-gaps --json` to enumerate the
  current gap-id set against the work-items JSONL store.
- The heavyweight `capture-impl-gaps` sibling invokes
  `detect-impl-gaps --json` as its detection step before walking
  the user through per-gap consent.
- The heavyweight `implement` skill invokes `detect-impl-gaps
  --json` at gap-tied closure verification to confirm the
  `gap_id` is no longer present in the returned set.

## Properties

- **Non-mutating.** No JSONL writes, no spec modifications, no
  user prompts.
- **Pure function of spec state.** Same spec text yields the same
  gap-id set; gap-id derivation hashes
  `<spec-file>\x1f<heading-path>\x1f<rule-text>`.
- **Excludes `proposed_changes/`** via the Spec Reader's exclusion
  contract — only ratified canonical content surfaces.
- **No LLM in the detection path.** Pattern-matching of
  MUST / MUST NOT / SHOULD / SHOULD NOT keywords (uppercase only)
  outside fenced code blocks is deterministic.
