> ### Confidential & Proprietary
>
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.  
> Last updated: 2026-04-24

---

# Multi-Agent Collaboration Protocol

---

## 0. Abstract

Defines the execution model, role structure, handoff protocol, and verification requirements for collaborative task execution across multiple agents. Extends the single-agent execution model defined in AGENTS.md to multi-agent contexts.

---

## 1. Scope

Applies when a task requires coordination between two or more agents operating under the AGENTS.md ruleset.

Integrates with:
- `AGENTS.md` — base execution model and compliance rules
- `guidelines/failure-recovery.md` — failure classification and recovery across agents
- `guidelines/uncertainty.md` — uncertainty propagation between agents
- `guidelines/orchestration.md` — applies when Executor runs repetitive tasks per `AGENTS.md` Section 3.2

---

## 2. Terminology

- **Orchestrator**: The agent responsible for task decomposition, delegation, verification, and state tracking.
- **Executor**: The agent responsible for executing a delegated subtask and reporting results.
- **Delegation**: The act of assigning a subtask from Orchestrator to Executor.
- **Handoff**: The transfer of execution state between agents.
- **Session**: A complete multi-agent execution from task receipt to final output.

---

## 3. Role Model

### 3.1 Structure

This protocol adopts a **Hierarchical model**.

```
Orchestrator
  ├── Executor A (Subtask 1)
  ├── Executor B (Subtask 2)
  └── Executor C (Subtask 3)
```

Roles are fixed for the duration of a session. An agent MUST NOT switch roles mid-session.

### 3.2 Orchestrator Responsibilities

The Orchestrator MUST:
- Apply AGENTS.md as primary control plane for the full session
- Decompose the task into well-defined, isolatable subtasks
- Delegate subtasks with complete execution context
- Verify all Executor outputs before proceeding
- Maintain the state required to emit `EXECUTION_STATE::` at interruption, escalation, or completion (per `guidelines/ir-spec.md` Section 2)
- Escalate to user when recovery is exhausted

The Orchestrator MUST NOT:
- Delegate ambiguous or underspecified subtasks
- Accept Executor output without verification
- Proceed if session-level `EXECUTION_STATE::` is invalid

### 3.3 Executor Responsibilities

The Executor MUST:
- Apply AGENTS.md within the scope of the delegated subtask
- Emit UNCERTAINTY IR per `guidelines/uncertainty.md` before acting on uncertain elements
- Report subtask execution state in the `SUBTASK_RESULT:: execution_state` field upon completion or failure
- Apply failure recovery per `guidelines/failure-recovery.md` before escalating

The Executor MUST NOT:
- Expand scope beyond the delegated subtask
- Modify shared state outside its assigned scope
- Suppress UNCERTAINTY IR to avoid interrupting the Orchestrator
- Communicate directly with other Executors

---

## 4. Execution Model

### 4.1 Session Flow

```
1. Orchestrator receives task
2. Orchestrator applies Entry Procedure (AGENTS.md Section 3.1)
3. Orchestrator decomposes task into subtasks
4. For each subtask:
   a. Orchestrator constructs DelegationPacket
   b. Orchestrator delegates to Executor
   c. Executor applies Entry Procedure (scoped to subtask)
   d. Executor executes and reports SubtaskResult
   e. Orchestrator verifies SubtaskResult
   f. Orchestrator updates SessionState
5. Orchestrator aggregates verified results
6. Orchestrator validates final output
7. Orchestrator delivers output
```

### 4.2 Parallelism

Subtasks MAY be executed in parallel when:
- Subtasks are fully independent (no shared state, no output dependency)
- Orchestrator can verify results independently

Subtasks MUST be executed sequentially when:
- Subtask B depends on output of Subtask A
- Shared state access cannot be isolated

---

## 5. Delegation Protocol

### 5.1 DelegationPacket IR

The Orchestrator MUST construct and transmit a DelegationPacket for every subtask delegation.

Canonical source: `guidelines/ir-spec.md` (`DELEGATION::`).
This document MUST NOT redefine the minimum schema; use `guidelines/ir-spec.md` Section 4.8 as the single source of truth.

### 5.2 Delegation Rules

- `description` MUST be unambiguous — Executor MUST NOT need to infer task intent
- `inputs` MUST be complete — Executor MUST NOT fetch external state not provided
- `scope` MUST explicitly list exclusions, not just inclusions
- `guidelines` MUST reference all files the Executor needs — Executor MUST NOT assume applicability
- If any field is underspecified, Orchestrator MUST resolve it before delegation

**MUST NOT** delegate a subtask that would require the Executor to resolve a BLOCK-level uncertainty independently.

---

## 6. Handoff Protocol

### 6.1 SubtaskResult IR

The Executor MUST report results using the following IR upon subtask completion or failure.

Canonical source: `guidelines/ir-spec.md` (`SUBTASK_RESULT::`).
This document MUST NOT redefine the minimum schema; use `guidelines/ir-spec.md` Section 4.9 as the single source of truth.

### 6.2 Status Definitions

| Status | Meaning |
|--------|---------|
| `COMPLETE` | Subtask executed and self-verified successfully |
| `FAILED` | Execution fault occurred; recovery attempted but unsuccessful |
| `BLOCKED` | BLOCK-level uncertainty encountered; execution stopped |

### 6.3 Handoff Rules

- Executor MUST emit SubtaskResult before terminating, regardless of status
- Executor MUST NOT emit `COMPLETE` if self-audit checklist has unchecked items
- `uncertainty_log` MUST include all UNCERTAINTY IR emitted during execution, even if resolved
- Orchestrator MUST NOT discard SubtaskResult — it MUST be recorded in SessionState

---

## 7. Verification Protocol

### 7.1 Orchestrator Verification Steps

Upon receiving a SubtaskResult, the Orchestrator MUST perform the following in order:

```
1. Validate SubtaskResult structure (all required fields present)
2. Check status
   → BLOCKED: enter Uncertainty Resolution (Section 7.2)
   → FAILED:  enter Failure Propagation (Section 7.3)
   → COMPLETE: continue to step 3
3. Review uncertainty_log
   → For each UNCERTAINTY:: declared:
       INFER: can Orchestrator confirm from session context?
         YES → mark as confirmed, annotate SessionState
         NO  → retain as INFER, flag for final output annotation
4. Validate output against output_schema in DelegationPacket
5. Update SessionState
6. Proceed to next subtask or aggregation
```

### 7.2 Uncertainty Resolution

When SubtaskResult status is `BLOCKED`:

The Orchestrator MUST perform the following procedure in order:

1. Retrieve the blocking `UNCERTAINTY::` declaration from `uncertainty_log`.
2. Determine whether verified session context resolves the block without creating a new ambiguity.
3. If yes, update delegation inputs with the resolved information and re-delegate the same subtask within its original scope.
4. Count each such re-delegation as one recovery attempt and record it in SessionState.
5. If the same subtask remains `BLOCKED` after two recovery attempts, escalate to the user per Section 9.
6. If no, determine whether the session can still produce a valid result without this subtask.
7. If the session can continue, mark the subtask as `SKIPPED`, add its ID to the `skipped` field in `EXECUTION_STATE::`, and record the impact in SessionState and final output planning.
8. If the session cannot continue, escalate to the user per Section 9.
9. The Orchestrator MUST NOT treat a `BLOCKED` subtask as complete without re-delegation, explicit `SKIPPED` disposition, or user escalation.
10. The Orchestrator MUST NOT re-delegate a `BLOCKED` subtask without new verified input that resolves the declared blocking element.

### 7.3 Failure Propagation

When SubtaskResult status is `FAILED`:

The Orchestrator MUST perform the following procedure in order:

1. Retrieve the subtask `EXECUTION_STATE::` from `SubtaskResult`.
2. Assess blast radius: dependent pending subtasks, invalidated completed subtasks, and checkpoint validity.
3. If blast radius is contained to the failed subtask, re-delegate it with corrected inputs for attempt 1, then attempt 2 if needed.
4. If the subtask still fails after two recovery attempts, escalate to the user per Section 9.
5. If blast radius is not contained, identify the last valid SessionState checkpoint and re-plan only the affected portion from that checkpoint.
6. Preserve all previously verified outputs that remain valid.
7. If re-planning is not possible, escalate to the user per Section 9.
8. The Orchestrator MUST NOT continue dependent subtasks until recovery succeeds or the plan is revised from a valid checkpoint.

---

## 8. Session State

### 8.1 SessionState Schema

The Orchestrator MUST maintain SessionState throughout the session.

SessionState is an **internal runtime structure**, not an emitted IR block.
It holds the data required to emit `EXECUTION_STATE::` at the correct timing
(interruption, escalation, or completion) per `guidelines/ir-spec.md` Section 2.
The emitted IR schema for `EXECUTION_STATE::` is defined in `guidelines/ir-spec.md` Section 4.5
and takes precedence over this internal structure for all external IR emissions.

```
SessionState := {
  session_id:                   String,
  task_description:             String,
  subtasks:                     List<SubtaskID>,
  delegated:                    List<SubtaskID>,
  completed:                    List<SubtaskID>,
  failed:                       List<SubtaskID>,
  skipped:                      List<SubtaskID>,
  pending:                      List<SubtaskID>,
  uncertainty_log:              List<UNCERTAINTY:: declaration>,
  per_subtask_recovery_attempts: Map<SubtaskID, Integer>,
  resumable:                    Boolean,
  checkpoint:                   SubtaskID | null
}
```

### 8.2 Checkpoint Rule

The Orchestrator MUST record a checkpoint after each verified `COMPLETE` subtask. If session is interrupted, execution MUST resume from the last checkpoint, not from the beginning.

---

## 9. Escalation

Session-level escalation to user is triggered when:
- A BLOCK cannot be resolved by the Orchestrator and the session cannot continue without the blocked subtask
- A subtask remains `BLOCKED` after two re-delegation attempts with new verified input
- A subtask has failed after two re-delegation attempts (recovery exhausted)
- Blast radius of a failure invalidates the session plan
- SessionState becomes inconsistent

Escalation report MUST follow `guidelines/failure-recovery.md` Section 4.5, extended with:
`ESCALATION::` schema authority is `guidelines/ir-spec.md` Section 4.10.  
This document MUST NOT redefine the minimum schema.

Completed subtask outputs MUST be preserved and reported. The user MUST be able to resume from the checkpoint without losing verified work.

---

## 10. Orchestrator Failure

If the Orchestrator itself fails:

- All in-progress Executor sessions MUST be halted
- Last valid SessionState MUST be preserved
- User MUST be notified with current SessionState and checkpoint
- Session MAY be resumed by a new Orchestrator instance from the last checkpoint

---

## 11. Compliance

- Delegating an underspecified subtask is **non-compliant** with Section 5.2
- Accepting Executor output without verification is **non-compliant** with Section 7.1
- Suppressing UNCERTAINTY IR is **non-compliant** with `guidelines/uncertainty.md` Section 4.1
- Emitting `COMPLETE` with unchecked self-audit items is **non-compliant** with `guidelines/failure-recovery.md` Section 3.2
- Direct Executor-to-Executor communication is **non-compliant** with Section 3.3

---

## 12. Integration with AGENTS.md

This document extends:

- **Section 3.2** (Task Classification) → Composite or Repetitive Task requiring inter-agent coordination triggers this protocol
- **Section 7** (Failure Handling) → session-level escalation follows Section 9 of this document
- **Section 8** (Output Requirements) → final output must reflect verified SubtaskResults only

AGENTS.md Section 4 (Guideline Resolution Protocol) applies.  
In conflict, AGENTS.md takes precedence.

---

© 2026 Younghoon. All rights reserved.
