# Documentation Pack — Change Log

**Generated:** 2026-11-12

- Consolidated the supplied architecture, system design, roadmap, NASA data-source policy and technical decision content into standalone Markdown documents.
- Used the latest supplied versions of the database, API, simulation, component catalog and testing specifications.
- Corrected the database seed storage type from PostgreSQL `INT` to `BIGINT`, retaining the uint32 CHECK range.
- Corrected the landed-failure score example so `F=1` remains consistent with its definition as pre-touchdown feasibility; recalculated raw score to 64.0 and applied the 49.9 cap.
- Added a README index and a separate post-MVP backlog.
- No implementation code was generated and no tests were executed. Human approval gates remain open.

- Created this canonical documentation set from the R0-approved Downloads pack without overwriting either source set.
- Carried forward the illustrative 290 kg dry-mass + 360 kg propellant = 650 kg payload arithmetic, exact `lander-score-v2` / `lander-exec-v1` identifiers, and detailed audit history from the audited outputs specifications.
- Marked the actual lunar site and dataset **NOT YET APPROVED** throughout relevant documents; R1–R6 remain pending.
- Added `FINAL_DOCUMENTATION_STATUS.md` to record inventory and consistency checks. No implementation code or migrations were created.
