---
proposal: capture-impl-gaps-since-version.md
decision: accept
revised_at: 2026-05-27T00:00:37Z
author_human: thewoolleyman <chad@thewoolleyman.com>
author_llm: claude-opus-4-7
---

## Decision and Rationale

Impl already landed via li-3aottg (PR #38) — this acceptance ratifies the --since-version contract that the wrapper already obeys. The flag scopes detect-impl-gaps and capture-impl-gaps to spec files differing between a historical version and the live spec, enabling /livespec:revise's post-step to focus per-revise gap detection on newly-introduced content.

## Resulting Changes

(none)
