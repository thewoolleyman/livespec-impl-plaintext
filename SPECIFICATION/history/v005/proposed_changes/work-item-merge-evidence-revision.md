---
proposal: work-item-merge-evidence.md
decision: accept
revised_at: 2026-05-27T00:00:37Z
author_human: thewoolleyman <chad@thewoolleyman.com>
author_llm: claude-opus-4-7
---

## Decision and Rationale

Accepts all four sub-proposals: (a) add merge_sha/pr_number to AuditRecord with widened applicability {fix, spec-revised, resolved-out-of-band}; (b) canonical_branch optional config key in .livespec.jsonc with origin/HEAD default and master fallback; (c) work_item_merge_evidence static check verifying non-empty merge_sha and master-reachability via local git operations (network-free); (d) backfill strategy with disciplined-default and grandfather-fallback. Unblocks li-tenpup and follow-up impl work-items.

## Resulting Changes

(none)
