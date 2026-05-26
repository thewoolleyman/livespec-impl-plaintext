---
topic: claude-opus-4-7-critique
author: claude-opus-4-7
created_at: 2026-05-26T04:31:59Z
---

## Proposal: next-output-schema-contradicts-upstream

### Target specification files

- SPECIFICATION/contracts.md

### Summary

The §"next" section of `SPECIFICATION/contracts.md` (lines ~170-208) defines the impl-side `next` wrapper's JSON output as a flat single-object shape `{action, work_item_ref, urgency, reason}` with `action` shown only as `"implement"` or `"none"`. The upstream contract at `livespec/SPECIFICATION/contracts.md` §"Implementation-plugin contract — the 10-skill surface" → bullet `next` mandates a paginated envelope with top-level `candidates[]` and `pagination` keys, the same shape `/livespec:next` emits, plus `--limit <count>` (default 5) and `--offset <count>` (default 0) flags with exit-2-on-invalid validation. Each candidate object MUST carry `action`, `reason`, `urgency`, and the impl-side-specific `work_item_ref` field. The local concretization neither names the upstream schema nor accepts the upstream flags.

### Motivation

The two surfaces directly contradict each other on the output shape: a flat object versus a paginated `candidates[]` envelope. Upstream is explicit that the impl-side ranker MUST emit a candidate-array shape so consumers (doctor, the Layer 3 loop driver, core's `next`) have a uniform abstraction across pluggable backends; the impl-plaintext spec restates that contract incompatibly, which is a load-bearing contradiction the running wrapper currently honors (the wrapper emits the flat shape, not the paginated one). A reader of this file cannot tell whether the local spec intentionally narrows the upstream contract (which it MUST NOT per the §"Scope boundary" rule that this file `MUST NOT re-state livespec's contract; it MUST concretize the contract`) or whether the local spec has drifted behind an upstream contract bump.

### Proposed Changes

Rewrite §"next" in `SPECIFICATION/contracts.md` to: (1) emit a `{candidates[], pagination}` envelope conforming to the upstream output schema; (2) MUST accept `--limit` (default 5) and `--offset` (default 0) flags with the upstream validation rules and exit-2-on-bad-flags behavior; (3) describe the per-candidate fields (`action`, `reason`, `urgency`, `work_item_ref`) plus any impl-plaintext-specific candidate fields (e.g., `priority`, `origin`) the wrapper actually emits; (4) cite the upstream `livespec/SPECIFICATION/contracts.md` §"Implementation-plugin contract — the 10-skill surface" → `next` section as the authoritative envelope. Either update the wrapper to match upstream, or — if the flat single-object shape is intentional during bootstrap — file a follow-up work-item capturing the drift and the bump-pin plan to close it.

## Proposal: next-action-enumeration-silent-on-memos-and-broader-actions

### Target specification files

- SPECIFICATION/contracts.md
- SPECIFICATION/scenarios.md

### Summary

The §"next" section of `SPECIFICATION/contracts.md` shows two example outputs (`action: implement` and `action: none`) but does not state whether that enumeration is exhaustive or illustrative. The ranking algorithm pins the input to work-items JSONL state only and never names unprocessed memos (`state: untriaged`) as a candidate-producing input, even though untriaged memos are first-class impl-side actionable state (doctor's memo-hygiene invariant blocks on them, and `process-memos` is the canonical clear path). Meanwhile, the project-local Layer 3 driver at `.claude/skills/loop/SKILL.md` (referenced by Scenario 6 in `scenarios.md:103-118`) carries a dispatch table that maps `process-memos (impl-side)`, `capture-impl-gaps (impl-side)`, and `capture-spec-drift (impl-side)` to skill invocations — action labels the impl-side `next` skill, as currently specified, will never emit.

### Motivation

The contract is silent on whether unprocessed memos contribute to `next`'s ranking, and the action enumeration is ambiguous (shown by example, never stated to be exhaustive). The silence creates an inconsistency between the impl-plaintext contract and the project-local Layer 3 driver: the driver expects to dispatch on `process-memos` / `capture-impl-gaps` / `capture-spec-drift` actions that the impl-side `next` will never produce under the current contract. Either the driver's dispatch rows are dead code (and the spec should say so explicitly so they get pruned), or `next`'s action surface is genuinely broader than what `contracts.md §"next"` documents — and the spec's silence on which interpretation holds is what needs resolving.

### Proposed Changes

Resolve the ambiguity in `SPECIFICATION/contracts.md §"next"` by either: (a) pinning the action enumeration to `implement | none` explicitly ("action MUST be one of"), declaring the work-items-only scoping principled (memos are a different store; the canonical actionable-memo probe is `list-memos --filter=untriaged`), and updating Scenario 6 in `scenarios.md` plus the Layer 3 driver to clarify that memo / gap-detection / drift-detection invocations are driver-side concerns the driver invokes outside of `next`'s ranking; OR (b) widening the enumeration to include the broader impl-side action set (`implement`, `process-memos`, `capture-impl-gaps`, `capture-spec-drift`, `none`), explicitly listing the secondary state inputs (memos JSONL untriaged subset, current gap-id set) the ranker would have to consult, and documenting the ranking weights (e.g., one untriaged memo aged > N days outranks a P3 work-item). Either path is defensible; the current silence is not.

## Proposal: next-empty-queue-hygiene-fallback-undefined

### Target specification files

- SPECIFICATION/contracts.md
- SPECIFICATION/scenarios.md

### Summary

When both `/livespec:next` and `/livespec-impl-plaintext:next` emit `action: none`, the user is left with no nudge toward useful hygiene work (e.g., a doctor pass, a critique pass, a prune-history check). Neither §"next" in `SPECIFICATION/contracts.md` nor Scenario 6 in `scenarios.md` ("Project-local Layer 3 loop driver") specifies what the consolidating Layer 3 surface MAY or SHOULD do when both queues are empty. The current behavior is a silent exit with `action: none` on both sides; whether the orchestration layer is permitted to escalate to doctor / critique / prune-history as a hygiene fallback, or whether such escalation is forbidden as a productivity heuristic that violates the durable-pending principle, is undefined.

### Motivation

The empty-queue case is a behavioral hole. The terminology entry for `Durable-pending` in `livespec/SPECIFICATION/spec.md` §"Terminology" explicitly assigns pile-up and staleness heuristics to the productivity layer (the `next` skills and the project-local orchestration), but the impl-plaintext spec and Scenario 6 are silent on what the orchestration layer's fallback behavior in the all-quiet state should be. A user reaching `none / none` reasonably expects guidance toward hygiene work; the spec is ambiguous on whether that guidance is expected, allowed, or forbidden, leaving the Layer 3 driver author with no spec-side anchor for the choice.

### Proposed Changes

Extend `SPECIFICATION/scenarios.md` Scenario 6 with an explicit "empty-queue handoff" sub-step: when both `/livespec:next` and `/livespec-impl-plaintext:next` emit `action: none`, the Layer 3 driver SHOULD offer the user a hygiene fallback — at minimum, a `/livespec:doctor` pass and a `/livespec:critique` pass — and MAY also offer prune-history if `next.prune_history_threshold` would otherwise have suppressed it. Optionally add a parallel one-paragraph note to `SPECIFICATION/contracts.md §"next"` clarifying that the `action: none` emission is purely advisory (no fallback baked into Layer 2; the fallback policy is a Layer 3 concern per the cross-side composition doctrine). This keeps the productivity heuristic at the right layer while removing the silence.

## Proposal: next-cross-side-composition-doctrine-not-cited

### Target specification files

- SPECIFICATION/contracts.md
- SPECIFICATION/scenarios.md

### Summary

A reader of `SPECIFICATION/contracts.md §"next"` and `SPECIFICATION/scenarios.md` Scenario 6 finds no pointer to the upstream `livespec/SPECIFICATION/spec.md` §"Three-layer orchestration architecture" passages that codify why impl-side `next` and spec-side `next` are intentionally separate Layer-2 surfaces (specifically the clause "Cross-side composition belongs at Layer 3 … Livespec-core MUST NOT bake a particular weighting in; impl plugins MUST NOT either"). Scenario 6 says only that "the composition rules are entirely in scope for `livespec` and the project-local driver, not for this spec" without naming the section of upstream that pins the rule.

### Motivation

The omission leaves the design rationale unclear at the local-contract layer. A reader who asks the natural question — "why aren't impl-side and spec-side `next` consolidated into a single skill?" — has no spec-side breadcrumb pointing at the doctrinal answer; the answer exists upstream but the impl-plaintext spec does not cite it. The Layer 3 driver at `.claude/skills/loop/SKILL.md` does cite it (in its §"Cross-side composition" section), but the contract and scenarios files do not. The inconsistency in citation discipline between the driver and the spec is itself ambiguous: a future reader cannot tell whether the spec's silence is intentional (the upstream link is meant to be implicit via §"Scope boundary") or accidental.

### Proposed Changes

Add a one-line cross-reference at the head of `SPECIFICATION/contracts.md §"next"` and at the head of `SPECIFICATION/scenarios.md` Scenario 6 pointing at `livespec/SPECIFICATION/spec.md` §"Three-layer orchestration architecture" → "Cross-side composition belongs at Layer 3". The wording should make clear that the impl-side `next` is intentionally scoped to impl-side state only, that consolidation with `/livespec:next` is a Layer 3 (project-local orchestration) responsibility, and that Layer 2 surfaces MUST NOT bake a cross-side weighting in. This closes the citation gap without re-stating the upstream rule.
