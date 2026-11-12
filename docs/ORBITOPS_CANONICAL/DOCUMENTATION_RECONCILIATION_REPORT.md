# ORBITOPS Documentation Reconciliation Report

**Review date:** 2026-11-12  
**Scope:** Documentation comparison only. No source documentation was edited, moved, overwritten, or deleted. No application code, migrations, or tests were created or run.

## 1. Compared document sets

Compared all Markdown files in:

- `C:\Users\dharm\Downloads\ORBITOPS_Documentation` — 13 files.
- Project `outputs` folder — 10 matching architecture specifications.

The ten matched specifications were compared by content, line counts, headings, and unified diffs. The Downloads folder additionally contains `README.md`, `CHANGELOG.md`, and `POST_MVP_BACKLOG.md`; no counterparts for those three are present in `outputs`. The ten matched pairs all have different SHA-256 hashes. Hash differences include both substantive corrections and harmless formatting/wording changes, so a hash mismatch alone is not treated as a technical conflict.

Downloads metadata shows a later timestamp on the same date, and its README/CHANGELOG describe a consolidated pack with two corrections. This is evidence of a later packaging pass, not automatic authority. The Downloads pack calls itself a review draft and explicitly keeps approvals open. Neither set is designated canonical by this report.

## 2. Comparison of the ten specifications

| Specification | Exact substantive differences observed | Latest audited content / missing content | Recommended canonical basis |
|---|---|---|---|
| `ARCHITECTURE.md` | Downloads edits prose and headings, clarifies up-to-four team, explicitly defers advisor, says Vercel serves static frontend and removes Supabase Realtime from deployment text; it redistributes the final architecture/strict MVP contract and reference headings. No core stack change found. | Downloads is the later edited copy. Outputs has more explicit final strict-contract text and some specific rationale/terminology. | Downloads, retaining the explicit strict MVP contract and references from outputs where the pack’s reorganization loses precision. |
| `SYSTEM_DESIGN.md` | Downloads explicitly defers the advisor feature and removes “progress” from run lifecycle, consistent with terminal-only run updates. Otherwise mostly wording. It softens explicit version pin names in one sentence to generic “score formula/execution profile.” | Outputs spells out `lander-score-v2` and `lander-exec-v1`; that precision is absent from the corresponding Downloads sentence, though other docs still define these IDs. Both versions say the site preset is “approved” while the technical-decision list says the site remains unselected/unapproved. | Downloads for MVP scope, with explicit version IDs retained from outputs. **Site approval wording is internally unresolved and must not be treated as a selected site.** |
| `DATABASE_SCHEMA.md` | Downloads changes `simulation_runs.seed` from PostgreSQL `INT` to `BIGINT` and adds a correction note. All other schema content is effectively retained. | Downloads fixes a real type/range defect: PostgreSQL signed `INT` cannot represent the accepted maximum `4,294,967,295`; `BIGINT` plus the uint32 CHECK can. Outputs’ `INT` declaration conflicts with the API seed range. | Downloads. This correction is mathematically required if the API continues accepting the full uint32 range. |
| `API_SPECIFICATION.md` | Contract content matches; Downloads removes seven trailing blank lines only. | No substantive API contract difference identified. | Either copy; use Downloads for pack consistency. |
| `SIMULATION_ENGINE_SPEC.md` | Downloads changes the landed-failure example from `(A,F,E,R,O)=(.6,0,.4,.5,.5)` / raw 39 to `(.6,1,.4,.5,.5)` / raw 64 and adds a note defining `F` as pre-touchdown hard-gate feasibility. Early-failure data-denominator example remains raw 50.575 and capped 49.9 in both. | Downloads resolves an internal inconsistency in outputs: `F` is described as pre-touchdown feasibility, so a failure after touchdown must not retroactively set it to zero. With the published formula, `.30*.6 + .25*1 + .15*.4 + .15*.5 + .15*.5 = .64`, or 64 points, then the 49.9 landed-failure cap applies. | Downloads, including the explicit `F` definition and corrected example. |
| `COMPONENT_CATALOG_SPEC.md` | Catalog values and 118-credit arithmetic match. Downloads omits the output-only dry-mass/payload arithmetic paragraph: component dry mass `290 kg`, plus `360 kg` propellant = `650 kg`, below the illustrative `900 kg` payload cap. | The omitted paragraph is a useful validation example, not a changed hardware specification. | Downloads, with the output-only mass ledger restored as a clearly illustrative arithmetic check during reconciliation. Do not change any component value. |
| `TESTING_STRATEGY.md` | Content matches; Downloads removes one trailing blank line. | No substantive test-contract difference identified. | Either copy; use Downloads for pack consistency. |
| `DEVELOPMENT_ROADMAP.md` | Downloads clarifies fixed duration/site UI, drops intermediate progress from lifecycle wording, adds advisor deferral if scope threatens core loop, and formats MVP gates as a checklist. Other differences are editorial. | Gate set is substantively the same; “no progress” aligns with the current terminal-only status contract. | Downloads. |
| `NASA_DATA_SOURCES.md` | Downloads changes “fixed MVP sites” to singular “fixed MVP site” and lightly edits wording. | The singular form matches the one-site MVP; actual site/product selection remains pending in both sets. | Downloads, but do not infer an approved location or dataset. |
| `TECHNICAL_DECISIONS.md` | Downloads retains the six approval gates and adds explicit consistency notes for `BIGINT` seed and the `F` score correction. Outputs includes a more detailed strict-audit change log, including specific immutable-record, replay-race, catalog-ID and partial-hour changes. Some rationale phrasing differs. | Downloads has the later corrections; outputs has useful detailed audit provenance absent from Downloads’ shorter correction list. Both keep human decisions open. | Use Downloads’ decision values and pending approvals; preserve outputs’ additional audit-change details in any eventual canonical merged record. |

## 3. Critical differences and conflicts

1. **Seed database type:** outputs declares `INT` while API accepts the entire uint32 range. This is incompatible at values above `2,147,483,647`. Downloads’ `BIGINT` correction is consistent with the stated API range and uint32 constraint. If the accepted API range is not to change, `BIGINT` is the technically consistent choice; this report does not edit either file.
2. **Scoring feasibility term:** outputs’ landed-failure example assigns `F=0` after a landed failure even though `F` is pre-touchdown feasibility. Its raw score arithmetic is correct only for that inconsistent input. Downloads correctly uses `F=1` where pre-touchdown gates passed and computes 64.0 for that worked example; the final score is capped at 49.9. The separate early-failure vector’s raw 50.575 and cap remain unchanged.
3. **Site approval contradiction:** `SYSTEM_DESIGN.md` describes one “approved” site, while both technical-decision documents state that the site is still to be selected/approved and `south_pole_site_a` is a placeholder. README also says site selection is pending. The site remains BLOCKED until a human chooses a real named site and dataset or explicitly approves an illustrative schedule.
4. **Output-only component mass check:** Downloads omits a useful catalog payload arithmetic check present in outputs. Restore it in a future reconciliation only as an illustrative check, not as a claim about a real launcher.
5. **Precision loss:** Downloads’ `SYSTEM_DESIGN.md` uses generic version pin labels where outputs names the score and execution profile IDs. Keep the explicit `lander-score-v2` and `lander-exec-v1` identifiers in the canonical contract.
6. **Extra-document status:** README identifies the pack as a consolidated review draft and says approval is pending; CHANGELOG says two corrections were applied; POST_MVP_BACKLOG lists explicit deferrals. These files add context but do not supersede the ten specifications or approve their open decisions.

No other conflicting engineering equations, partial-hour rules, run-state transitions, canonical `run_start` payload, idempotency behavior, 118-credit minimum, or 140-credit budget were found in the compared sections. “No conflict found” means the documented statements matched during this audit; it is not a claim of implementation verification.

## 4. Reconciliation disposition by document

The recommended baseline is the later Downloads pack for all ten specifications, with these explicit carry-forwards from outputs: (a) the 290 kg dry / 650 kg payload arithmetic as a labeled illustrative check in `COMPONENT_CATALOG_SPEC.md`; (b) the exact score/execution version IDs in `SYSTEM_DESIGN.md`; and (c) the detailed audit history in `TECHNICAL_DECISIONS.md`. The two substantive Downloads corrections (`BIGINT` seed and score `F` semantics) should be preserved because they resolve verified inconsistencies.

This is a **recommendation**, not a silent merge or approval. Source files remain unchanged. Documentation is not yet reconciled because no canonical merged set has been approved, and the site wording conflict and approval gates remain open.

## 5. Unresolved human approval decisions

The six gates below are stated in both `TECHNICAL_DECISIONS.md` copies. They are all still pending. The additional canonical-documentation choice is required to complete this reconciliation.

| ID | Approval needed / choices documented | Why it matters | Recommendation and rationale | Dependent documents/modules |
|---|---|---|---|---|
| R0 — Canonical documentation set | Approve Downloads as the canonical base with the three output-only carry-forwards listed above, or specify another merge/source policy. | Otherwise implementers can follow conflicting `INT`/`BIGINT` and score semantics. | Approve the recommended Downloads-based merge, preserving the precise audited details noted above; the seed range and scoring correction are internally justified. | All ten specs; implementation kickoff and review baseline. |
| R1 — Named lunar site and environment data | Choose one named site and approve source dataset/transforms, or explicitly approve a fully illustrative schedule until curation. | Site coordinates, illumination, contact windows and heater/environment schedules affect operations, science, and provenance. | Select a named public-source site after domain review; if timing prevents curation, explicitly approve an illustrative schedule and label every derived value illustrative. Do not use placeholder `south_pole_site_a` as a real site. | `NASA_DATA_SOURCES`, `SYSTEM_DESIGN`, `SIMULATION_ENGINE_SPEC`; environment manifest/data ingestion, briefing and mission scenario. |
| R2 — Illustrative engineering/game parameters | Approve the 18 catalog values, event probabilities/impacts, environment schedules, 700/1,300 m/s propulsion requirements, 300 s Isp and 360 kg propellant as illustrative; alternatively require sourcing/revision for any values. | They drive feasibility, resource tradeoffs, event outcomes, budget and payload arithmetic; none should be presented as NASA hardware specifications. | Approve them only as explicitly illustrative educational parameters, subject to provenance labels and domain review for sourced values. | `COMPONENT_CATALOG_SPEC`, `SIMULATION_ENGINE_SPEC`, `NASA_DATA_SOURCES`, tests; catalog, validator and simulator. |
| R3 — Scoring | Approve `lander-score-v2` weights, hard gates, normalization targets and 49.9 landed-failure cap, or request revisions. | Scores shape player incentives and mission evaluation; reproducibility requires pinning the accepted formula. | Approve the documented transparent formula only after reviewing the corrected `F` meaning and examples; keep the formula version pinned. | `SIMULATION_ENGINE_SPEC`, `SYSTEM_DESIGN`, `API_SPECIFICATION`, `TESTING_STRATEGY`; scorer and reports. |
| R4 — Collaboration and demo policy | Approve four members, Supabase-authenticated demo, one-time copied invite token, editor/viewer roles, and one-instance Render expectations, or change specific items. | These set authorization behavior, invitation UX, concurrency and deployment capacity. | Approve the four-member bounded MVP and documented owner/editor/viewer policy if it fits the team demo; keep invite/auth checks server-side. | `API_SPECIFICATION`, `DATABASE_SCHEMA`, `ARCHITECTURE`, `SYSTEM_DESIGN`, tests; identity, invitation, collaboration and hosting configuration. |
| R5 — Execution budget | Benchmark 720 steps on chosen Render instance; approve or revise provisional `lander-exec-v1` 5-second deadline, 100-event cap, 2 MB result cap. | A wall-time limit can make run outcome depend on host load; result/event limits affect completeness and failure handling. | Benchmark first, then approve a fixed versioned profile; do not treat 5 seconds as measured capacity. Keep one-instance architecture unless measurements show the bounded run cannot fit and the user explicitly revisits scope. | `SIMULATION_ENGINE_SPEC`, `API_SPECIFICATION`, `DATABASE_SCHEMA`, `TESTING_STRATEGY`, `TECHNICAL_DECISIONS`; orchestration/runtime. |
| R6 — Event/team/UI requirements | Confirm event deadline, team capacity, UI currency label, and accessibility/language requirements; no options are specified in the docs. | These affect schedule, collaboration capacity, terminology and accessibility scope. | Confirm actual event/team constraints and choose an understandable non-real “credits” label plus accessibility/language baseline before final UI scope. | `DEVELOPMENT_ROADMAP`, `SYSTEM_DESIGN`, `TECHNICAL_DECISIONS`; project planning and frontend copy/accessibility. |

### Decisions that can be technically recommended without changing the source documents

- If the API remains uint32 seed, use PostgreSQL `BIGINT` with the stated range CHECK; PostgreSQL `INT` is insufficient.
- If `F` remains pre-touchdown feasibility, a later surface failure does not make it zero; the landed-failure cap handles mission failure. The Downloads vector follows that definition.
- Use the exact one-hour outer step and 720 landed steps with actual segment seconds for partial operations, as already specified.

These are audit findings/recommendations, not claims that the human has approved the final document merge.

## 6. Final status

- **DOCUMENTATION_RECONCILED:** No — both source sets remain intact and there is no approved canonical merged set; the site wording conflict also remains unresolved.
- **APPROVALS_PENDING:** Yes — R1–R6 are explicit human gates; R0 is needed to establish the canonical documentation baseline.
- **IMPLEMENTATION_READY:** No — implementation is blocked pending document-baseline approval and the domain/product decisions above.

## 7. What to approve before implementation

Please approve or revise:

1. The Downloads-based canonical merge recommendation in R0, including restoring the catalog mass check, exact version IDs, and detailed audit history from outputs.
2. The named site/data strategy in R1.
3. The illustrative parameter policy in R2.
4. The `lander-score-v2` formula and failure cap in R3.
5. The collaboration/auth/invite/hosting policy in R4.
6. The benchmarked execution profile in R5.
7. The event, team, currency, accessibility, and language requirements in R6.

Until those are approved, the project remains documentation-only and implementation-blocked.

