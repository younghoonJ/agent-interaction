> ### Confidential & Proprietary
> 
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-25

---

# Orchestration & Repetitive Tasks Specification

---

This document covers single-agent repetitive execution only.
For inter-agent collaboration, refer to: `guidelines/multi-agent.md`.

## 1. Scope

This document defines execution protocol for repetitive tasks performed by one agent using internal parallel worker slots.

It applies to:

* benchmarks
* A/B tests
* repeated test execution
* ML experiments
* any task with multiple independent runs

---

## 2. Terminology

* **Run**: one execution unit in a repetitive task.
* **WorkerSlot**: an internal parallel execution slot inside a single agent session.
* **Orchestrator Loop**: single-agent control flow that plans, dispatches, validates, and aggregates runs.
* **Checkpoint**: mandatory validation gate during execution progress.
* **Baseline**: reference run or reference metric used for comparison.

---

## 3. Orchestration Trigger

Orchestration MUST be used only when all are true:

* **[MUST]** Number of runs `N >= 10`
* **[MUST]** Runs are independent
* **[MUST]** Estimated total sequential execution time exceeds 5 minutes

If any condition is false, orchestration MUST NOT be used.

Time estimation and ambiguity handling are governed by `AGENTS.md` Section 3.2.

---

## 4. Execution Boundary

* **[MUST]** Follow execution mode declared in `INTENT::`.
* **[MUST]** Treat orchestration state as bounded session state.
* **[MUST]** Record external snapshots with source and timestamp before use when execution mode is `SNAPSHOT_BOUNDED`.
* **[MUST NOT]** use unbounded polling or streaming.

---

## 5. Planning

Before run dispatch, Orchestrator Loop MUST:

* **[MUST]** determine total runs (`N`)
* **[MUST]** define run unit contract (inputs, expected output, failure criteria)
* **[MUST]** compute worker slots:

```
workers = min(ceil(N / 10), 8)
```

* **[MUST]** state that `workers` are internal WorkerSlots, not multi-agent delegates
* **[MUST]** partition run IDs deterministically

Deterministic partitioning rule:

```
slot_index = run_id mod workers
```

---

## 6. IR & Tool Gate Requirements

Before execution, Orchestrator Loop MUST:

* **[MUST]** emit `PLAN::` with `type: Repetitive`
* **[MUST]** include deterministic ordering and dependency declarations
* **[MUST]** include `stop_on_fail` policy in `PLAN::`

During execution:

* **[MUST]** emit `TOOL_INTENT::` immediately before every side-effecting tool call
* **[MUST]** emit `UNCERTAINTY::` before `TOOL_INTENT::` when a tool action depends on uncertain facts
* **[MUST]** update `EXECUTION_STATE::` at each checkpoint and terminal state

Schema authority: `guidelines/ir-spec.md`.

---

## 7. Runtime Detection

* **[MUST]** detect only runtime capabilities required by the run contract
* **[MUST]** use minimal sufficient checks
* **[MUST NOT]** assume runtime capabilities
* **[MUST NOT]** hardcode a specific command set as universally required

Examples are non-normative; detection method is environment-dependent.

---

## 8. Parallel Execution Protocol

* **[MUST]** WorkerSlots operate independently
* **[MUST NOT]** share mutable state across WorkerSlots
* **[MUST NOT]** allow cross-slot hidden dependencies
* **[MUST]** continue remaining runs on single-run failure unless checkpoint stop condition triggers

---

## 9. Checkpoint Rule (50%)

At 50% completion of scheduled runs:

* **[MUST]** validate failure rate and output integrity

| Condition       | Action   |
| --------------- | -------- |
| `>20%` failure  | STOP     |
| invalid output  | STOP     |
| valid execution | CONTINUE |

---

## 10. Artifact Logging

### 10.1 Location

Artifacts MUST be stored under a workspace-scoped path:

```
artifacts/orchestration/YYYY-MM-DD_<task>/
```

Absolute fixed root paths are non-normative and MUST NOT be required.

### 10.2 Per-Run Required Fields

Each run record MUST include:

* run_id
* start_timestamp (ISO 8601)
* end_timestamp (ISO 8601)
* run_contract_id
* environment_snapshot
* status (`COMPLETE | FAILED | BLOCKED`)
* result summary
* validation outcome

### 10.3 Logging Rules

* **[MUST]** log every run including failures and blocked runs
* **[MUST NOT]** cherry-pick results
* **[MUST]** preserve reproducibility metadata

---

## 11. Result Evaluation & Completion

* **[MUST]** compare against baseline
* **[MUST]** use at least 3 runs when stability is required
* **[SHOULD]** report variance (`avg ± stddev`) when numeric metrics exist
* **[MUST]** preserve intermediate artifacts until summary is finalized

When stopping condition is met, Orchestrator Loop MUST summarize:

* best run
* final conclusion
* recommended next step

---

## 12. Failure Handling

| Scenario                 | Action                                    |
| ------------------------ | ----------------------------------------- |
| single run failure       | continue remaining runs                   |
| checkpoint stop condition| STOP and report                           |
| orchestration tool failure | STOP, emit `FAILURE::`, preserve checkpoint |

Refer to: `guidelines/failure-recovery.md`.

---

## 13. Security & Isolation

* **[MUST]** isolate execution environment
* **[MUST NOT]** use production data unless explicitly authorized
* **[MUST NOT]** modify shared systems outside declared scope
* **[MUST]** constrain side effects to declared execution boundary

---

## 14. Prohibitions

* **[MUST NOT]** bypass required IR emissions for repetitive execution
* **[MUST NOT]** skip the 50% checkpoint when orchestration is active
* **[MUST NOT]** mutate partitioning logic mid-run
* **[MUST NOT]** reinterpret WorkerSlots as multi-agent delegates

---

## 15. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

## 16. Integration with AGENTS.md

This document extends:

- **Section 3.2** (Task Classification) → Repetitive task classification and sequential time estimation govern orchestration trigger
- **Section 5.3** (IR Emission Gate) → TOOL_INTENT:: required before side-effecting tool calls
- **Section 6.1** (Determinism) → deterministic partitioning and run ordering
- **Section 7** (Failure Handling) → checkpoint stop conditions and orchestration failure recovery follow this section

AGENTS.md Section 4 (Guideline Resolution Protocol) applies.
In conflict, AGENTS.md takes precedence.

---

# Appendix A. Example Run Record (Non-Normative)

```yaml
run_id: 003
start_timestamp: 2026-04-25T13:20:00+09:00
end_timestamp: 2026-04-25T13:22:10+09:00
run_contract_id: latency-benchmark-v2
environment_snapshot: python=3.11,cpu=8
status: COMPLETE
result_summary: p95=340ms
validation_outcome: PASS
```

---

© 2026 Younghoon. All rights reserved.
