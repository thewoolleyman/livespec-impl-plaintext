---
proposal: claude-opus-4-7-critique.md
decision: modify
revised_at: 2026-05-27T00:00:37Z
author_human: thewoolleyman <chad@thewoolleyman.com>
author_llm: claude-opus-4-7
---

## Decision and Rationale

Modify-then-accept with the following per-sub-proposal paths: (A) MATCH UPSTREAM — rewrite §next so the documented output is the {candidates[], pagination} envelope per upstream §Implementation-plugin contract — the 10-skill surface → next and upstream §/livespec:next → §Output schema; add --limit (default 5) and --offset (default 0) with exit-2-on-invalid validation. The wrapper at .claude-plugin/scripts/bin/next.py is NOT modified in this PR — the resulting spec-impl gap will be surfaced via /livespec-impl-plaintext:capture-impl-gaps after the revise. (B) PIN ENUM — action MUST be one of 'implement' | 'none'; work-items-only scoping is principled (memos are a different store; canonical actionable-memo probe is list-memos --filter=untriaged); Scenario 6 clarifies memo / gap-detection / drift-detection invocations are Layer 3 driver-side concerns. (C) Empty-queue handoff added to Scenario 6 as a Layer 3 productivity heuristic with parallel one-paragraph note in §next clarifying empty-array emission is purely advisory. (D) One-line cross-reference at the head of §next and Scenario 6 pointing at upstream spec.md §Three-layer orchestration architecture → 'Cross-side composition belongs at Layer 3'.

## Modifications

(A) Rewrite §next output schema to {candidates[], pagination} envelope; add --limit (default 5) and --offset (default 0) flags with exit-2 on invalid; describe per-candidate fields (action, reason, urgency, work_item_ref) plus optional impl-plaintext-specific fields; cite upstream as the authoritative envelope. The flat single-object shape is removed; empty candidates array is the no-work signal. Wrapper update is deferred to a follow-up work-item (filed via capture-impl-gaps after the revise) so the resulting spec-impl gap surfaces naturally. (B) Pin action enum to 'implement' | 'none' explicitly. Update Scenario 6 to clarify memo / gap-detection / drift-detection invocations are Layer 3 driver-side concerns the driver invokes outside of next's ranking. (C) Extend Scenario 6 with the empty-queue handoff sub-step: when both /livespec:next and /livespec-impl-plaintext:next emit empty candidates[], the Layer 3 driver SHOULD offer a hygiene fallback (/livespec:doctor, /livespec:critique, optionally /livespec:prune-history). Add parallel one-paragraph note to §next clarifying the fallback is a Layer 3 concern, never baked into Layer 2. (D) Add one-line cross-reference at the head of §next and at the head of Scenario 6 pointing at livespec/SPECIFICATION/spec.md §Three-layer orchestration architecture → 'Cross-side composition belongs at Layer 3'.

## Resulting Changes

- contracts.md
- scenarios.md
