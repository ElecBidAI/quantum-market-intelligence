# research/experiments

Not populated as a data directory yet, but the record shape it will hold is
implemented: `services/backtester/src/backtester/experiment.py`'s
`ExperimentRecord` (status: `REJECTED | RESEARCH | PAPER | APPROVED`, see
[`docs/risk/RISK-GOVERNANCE.md`](../../docs/risk/RISK-GOVERNANCE.md) Section 10),
persisted via `services/backtester/src/backtester/persistence.py` into the
`research_runs` table (`data/migrations/0004_backtests.sql`) rather than as
files in this directory. No actual experiments have been run yet — there's no
strategy-engine producing candidates to research (Phase 6).
