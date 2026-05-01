> ### Confidential & Proprietary
>
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.  
> Last updated: 2026-05-01 (document consistency and orchestration timing clarified)

---

# Intermediate Representation (IR) Canonical Specification

---

## 0. Abstract

Defines canonical prefixes, minimum required fields, and validation rules
for all Intermediate Representation (IR) blocks used across this suite.

This document is authoritative for IR contracts.

---

## 1. Scope

Applies to:
- `AGENTS.md` and any agent-specific counterpart (e.g., `CLAUDE.md` per its Section 0.1 naming note)
- `guidelines/uncertainty.md`
- `guidelines/failure-recovery.md`
- `guidelines/multi-agent.md`
- `guidelines/document-consistency.md`
- any validator or runtime enforcement that parses IR blocks

---

## 2. Prefix Registry

| Prefix | Purpose | Required timing |
|--------|---------|-----------------|
| `INTENT::` | Declares interpreted task and execution mode | Entry Procedure, before task execution |
| `GUIDELINES LOADED::` | Declares always/task/missing guideline sets | Entry Procedure completion |
| `CONTROL::` | Declares compact entry control-plane state for valid `COMPACT` tasks | After classification, guideline loading, and planning if needed; before task execution |
| `UNCERTAINTY::` | Declares BLOCK/INFER uncertainty | Before acting on uncertain element |
| `FAILURE::` | Declares failure type, cause, recovery path | Immediately on failure detection |
| `EXECUTION_STATE::` | Declares resumable state for interrupted/composite work | On interruption, escalation, completion, or orchestration checkpoints when required |
| `TOOL_INTENT::` | Declares intent for side-effecting tool operation | Immediately before side-effecting tool call |
| `PLAN::` | Declares decomposition and execution plan for Composite/Repetitive tasks | After GUIDELINES LOADED::, before subtask execution |
| `DELEGATION::` | Declares subtask delegation packet | Before Executor handoff |
| `SUBTASK_RESULT::` | Declares subtask completion/failure payload | At subtask termination |
| `ESCALATION::` | Declares escalation state and resume requirement | When escalation is triggered |
| `CLARIFICATION_NEEDED::` | Declares blocking questions and resume point | After BLOCK-level stop |
| `CLAIM_INDEX::` | Declares compact claim inventory and grouping summary for consistency analysis | After guideline loading and scope lock, before comparison |
| `CONSISTENCY_PLAN::` | Declares comparison plan, compared pairs, and inter-group edges used for consistency adjudication | After `CLAIM_INDEX::`, before consistency adjudication |
| `CONSISTENCY_FINDINGS::` | Declares consistency findings and overall status | After in-group/inter-group comparison and adjudication |

---

## 3. Prefix Rules

- External IR emission MUST use canonical prefixes defined in Section 2.
- Prefixes MUST match exactly, including uppercase/lowercase and trailing `::`.
- Internal alias names are optional and out of scope for this spec.

---

## 4. Minimum Schemas

### 4.1 INTENT::

```
INTENT::
  task:           <one-line normalized task statement>
  type:           <Simple | Composite | Repetitive | Ambiguous>
  objective:      <expected outcome>
  constraints:    <key constraints list or null>
  execution_mode: <LOCAL_ONLY | SNAPSHOT_BOUNDED>
  __token__:      <session IR token | omit if no session IR token is active>
```

### 4.2 GUIDELINES LOADED::

```
GUIDELINES LOADED::
  always:    <List<String>>
  task:      <List<String>>
  missing:   <List<String>>
  __token__: <session IR token | omit if no session IR token is active>
```

### 4.3 UNCERTAINTY::

```
UNCERTAINTY::
  level:     <BLOCK | INFER>
  source:    <specific uncertain element>
  basis:     <known context used for classification>
  impact:    <consequence if incorrect>
  action:    <STOP | PROCEED_WITH_DECLARATION>
  __token__: <session IR token | omit if no session IR token is active>
```

### 4.4 FAILURE::

```
FAILURE::
  type:      <Type1 | Type2 | Type3>
  point:     <step/subtask identifier>
  cause:     <root cause summary>
  recovery:  <planned next recovery action>
  attempts:  <integer>
  __token__: <session IR token | omit if no session IR token is active>
```

### 4.5 EXECUTION_STATE::

```
EXECUTION_STATE::
  task_id:           <String>
  total_subtasks:    <Integer>
  completed:         <List<SubtaskID>>
  failed:            <SubtaskID | null>
  failure_type:      <Type1 | Type2 | Type3 | null>
  recovery_attempts: <Integer>
  skipped:           <List<SubtaskID>>
  pending:           <List<SubtaskID>>
  resumable:         <YES | NO>
  __token__:         <session IR token | omit if no session IR token is active>
```

### 4.6 PLAN::

Required for Composite and Repetitive tasks only. MUST NOT be emitted for Simple tasks.
Under `COMPACT`, a Composite task MAY embed the plan in `CONTROL::` instead of
emitting a separate `PLAN::`. Repetitive tasks always require `PLAN::`.

```
PLAN::
  type:         <Composite | Repetitive>
  subtasks:     <List<{id: String, description: String}>>
  order:        <Sequential | Parallel | Mixed>
  dependencies: <Map<SubtaskID, List<SubtaskID>> | null>
  stop_on_fail: <YES | NO>
  __token__:    <session IR token | omit if no session IR token is active>
```

### 4.6.1 CONTROL::

Compact equivalent of `INTENT::`, `GUIDELINES LOADED::`, and `PLAN::` for valid
`COMPACT` tasks only.

MUST NOT be emitted for `Repetitive`, document consistency verification,
multi-agent, security-sensitive, authority-adjudication, or full-audit tasks.

```
CONTROL::
  task:           <one-line normalized task statement>
  type:           <Simple | Composite>
  objective:      <expected outcome>
  constraints:    <key constraints list or null>
  execution_mode: <LOCAL_ONLY | SNAPSHOT_BOUNDED>
  guidelines:     {
                    always: List<String>,
                    always_status: "pre-loaded via system prompt",
                    task: List<String>,
                    missing: List<String>
                  }
  plan:           <null | {
                    subtasks: List<{id: String, description: String}>,
                    order: Sequential | Parallel | Mixed,
                    dependencies: Map<SubtaskID, List<SubtaskID>> | null,
                    stop_on_fail: YES | NO
                  }>
  __token__:      <session IR token | omit if no session IR token is active>
```

All `List<String>` entries in `guidelines` MUST be canonical guideline paths.

`guidelines.always` MUST remain list-shaped and path-only. Preload status belongs
in `always_status`; path strings MUST NOT contain preload annotations.

`SNAPSHOT_BOUNDED` is valid under `COMPACT` only when the required external data
is already captured in the execution environment snapshot and no new external
system access is needed. If new external system access is required, the task
MUST use `STRICT`.

For `Simple` tasks, `plan` MUST be `null`.

For `Composite` tasks, `plan` MUST preserve the minimum planning semantics of
`PLAN::`: subtasks, order, dependencies, and stop-on-fail policy.

### 4.7 TOOL_INTENT::

```
TOOL_INTENT::
  tool:      <tool identifier>
  purpose:   <why this call is required>
  input:     <minimal declared input summary>
  effect:    <READ_ONLY | SIDE_EFFECTING>
  __token__: <session IR token | omit if no session IR token is active>
```

### 4.8 DELEGATION::

```
DELEGATION::
  session_id:    <String>
  subtask_id:    <String>
  description:   <precise subtask objective>
  inputs:        <required data/contracts/constraints>
  scope:         <explicit boundaries, including exclusions>
  output_schema: <expected SUBTASK_RESULT.output structure>
  guidelines:    <List<String>>
  depends_on:    <List<SubtaskID> | null>
  __token__:     <session IR token | omit if no session IR token is active>
```

### 4.9 SUBTASK_RESULT::

```
SUBTASK_RESULT::
  session_id:        <String>
  subtask_id:        <String>
  status:            <COMPLETE | FAILED | BLOCKED>
  output:            <artifact | null>
  execution_state:   <EXECUTION_STATE:: object>
  uncertainty_log:   <List<UNCERTAINTY:: object> | null>
  recovery_attempts: <Integer>
  notes:             <String | null>
  __token__:         <session IR token | omit if no session IR token is active>
```

### 4.10 ESCALATION::

```
ESCALATION::
  session_id:       <String>
  trigger:          <reason escalation occurred>
  session_state:    <SessionState summary>
  completed_output: <verified completed outputs | null>
  blocking_issue:   <specific information or decision needed>
  resumable:        <YES | NO>
  resume_from:      <SubtaskID | StepID | null>
  __token__:        <session IR token | omit if no session IR token is active>
```

### 4.11 CLARIFICATION_NEEDED::

```
CLARIFICATION_NEEDED::
  context:     <one-sentence execution context>
  blocking:    <reference to related UNCERTAINTY::>
  questions:   <List<String> (1..3)>
  resumable:   <YES | NO>
  resume_from: <subtask_id | step identifier | null>
  __token__:   <session IR token | omit if no session IR token is active>
```

### 4.12 CLAIM_INDEX::

Required for document consistency verification tasks only.

```
CLAIM_INDEX::
  source_scope:    <List<SourceID>>
  unit_of_check:   <paragraph | section | rule | table | example | mixed>
  extraction_unit: <paragraph | section | rule | table | example | mixed>
  total_claims:    <Integer>
  claim_index:     <List<{
                     id: String,
                     source: String,
                     location: String,
                     modality: FACT | DEF | MUST | SHOULD | MAY | EXAMPLE,
                     topic: String,
                     normalized_summary: String,
                     scope: String | null,
                     version: String | null
                   }>>
  groups:          <List<{
                     id: String,
                     label: String,
                     member_claims: List<String>
                   }>>
  __token__:       <session IR token | omit if no session IR token is active>
```

### 4.13 CONSISTENCY_PLAN::

Required for document consistency verification tasks only.

```
CONSISTENCY_PLAN::
  grouping_basis:    <topic | subject | procedure | schema | mixed>
  in_group_checks:   <List<{
                       group_id: String,
                       pairs: List<List<String>>,
                       basis: String
                     }>>
  inter_group_edges: <List<{
                       source_group: String,
                       target_group: String,
                       relation: depends_on | example_of | overrides | supports | refines,
                       basis: String
                     }>>
  __token__:         <session IR token | omit if no session IR token is active>
```

### 4.14 CONSISTENCY_FINDINGS::

Required for document consistency verification tasks only.

```
CONSISTENCY_FINDINGS::
  verification_boundary: <{
                           source_scope: List<String>,
                           consistency_scope: INTRA_DOC | CROSS_DOC | AUTHORITY_CONFORMANCE,
                           authority_order: List<String>,
                           version_scope: String | null
                         }>
  overall_status:        <CONSISTENT | CONSISTENT_WITH_MINOR_ISSUES | INCONSISTENT | UNDETERMINABLE>
  findings:              <List<{
                           id: String,
                           type: CONTRADICTION | AMBIGUITY | MISSING_DEPENDENCY | REFERENCE_ERROR | TERM_DRIFT | SCOPE_MISMATCH | EXAMPLE_MISMATCH | AUTHORITY_MISMATCH | STATUS_MISMATCH,
                           severity: CRITICAL | MAJOR | MINOR,
                           in_group: YES | NO,
                           related_claims: List<String>,
                           explanation: String,
                           resolution_basis: String | null,
                           needs_human_decision: YES | NO
                         }>>
  __token__:             <session IR token | omit if no session IR token is active>
```

---

## 5. Emission Order Constraints

Profiles:

* `STRICT`: full control-plane IR required.
* `STANDARD`: control-plane IR MAY be omitted only for `Simple` tasks that are read-only and `LOW` uncertainty.
  Omission of control-plane IR does NOT waive applicable guideline loading/compliance obligations.
* `COMPACT`: `CONTROL::` MAY replace the entry `INTENT::`, `GUIDELINES LOADED::`, and `PLAN::`
  sequence only when permitted by `AGENTS.md` Section 3.1.1.
  It MUST NOT be selected as a runtime fallback for a task that already began under `STANDARD`.
  Compact entry emission does NOT waive applicable guideline loading/compliance obligations.

Required baseline sequence:

`INTENT::` → `GUIDELINES LOADED::` → (`UNCERTAINTY::` / `TOOL_INTENT::` / `FAILURE::` as needed) → final output

For Composite and Repetitive tasks not using `COMPACT`, `PLAN::` MUST be inserted after `GUIDELINES LOADED::`:

`INTENT::` → `GUIDELINES LOADED::` → `PLAN::` → (`UNCERTAINTY::` / `TOOL_INTENT::` / `FAILURE::` as needed) → final output

For `COMPACT` tasks, the compact entry sequence is:

`CONTROL::` → (`UNCERTAINTY::` / `TOOL_INTENT::` / `FAILURE::` as needed) → (`EXECUTION_STATE::` when required) → final output

If `CONTROL::type` is `Composite`, the embedded `plan` field replaces `PLAN::`
for entry control-plane purposes only.

For Composite tasks, `EXECUTION_STATE::` remains required on interruption,
escalation, or completion.

`CONTROL::` does NOT replace:

* `TOOL_INTENT::` before side-effecting tool calls
* `UNCERTAINTY::` before acting on `INFER` or `BLOCK`
* `FAILURE::` on failure detection
* `EXECUTION_STATE::`
* document consistency IR
* multi-agent IR
* orchestration IR

For document consistency verification tasks, the analysis-plane sequence MUST include:

`INTENT::` → `GUIDELINES LOADED::` → `CLAIM_INDEX::` → `CONSISTENCY_PLAN::` → (`UNCERTAINTY::` / `FAILURE::` / `TOOL_INTENT::` as needed) → `CONSISTENCY_FINDINGS::` → final output

If a document consistency verification task is also `Composite` or `Repetitive`, the combined sequence MUST be:

`INTENT::` → `GUIDELINES LOADED::` → `PLAN::` → `CLAIM_INDEX::` → `CONSISTENCY_PLAN::` → (`UNCERTAINTY::` / `FAILURE::` / `TOOL_INTENT::` as needed) → `CONSISTENCY_FINDINGS::` → final output

If a side-effecting tool call relies on uncertain facts:

`UNCERTAINTY::` MUST precede `TOOL_INTENT::`.

In `STANDARD` profile, if any of the following occurs, full baseline sequence MUST be restored immediately:

* required guideline missing during the internal load attempt
* side-effecting operation
* `INFER` or `BLOCK` uncertainty
* any detected execution failure

When a required guideline is missing after `STANDARD` omission or `COMPACT`
entry selection, the agent MUST restore `STRICT`, emit `GUIDELINES LOADED::`
with `missing` populated, and stop under `AGENTS.md` Section 3.1 Step 6.

Late guideline discovery exception:

If a newly required task-specific guideline is discovered during execution, the agent MUST emit
`UNCERTAINTY::` (`BLOCK`) or `FAILURE::`, then emit an updated `GUIDELINES LOADED::` before
continuing the affected component.

---

## 6. Validation Rules

- Parsers MUST match exact prefixes including trailing `::`.
- Missing required fields in minimum schema is non-compliant.
- Unknown extra fields MAY be accepted if required fields are present.
- If two specs disagree on IR shape, this file is authoritative.
- When a session IR token is active, any IR block missing `__token__` is non-compliant. Validators MUST reject such blocks.
- When no session IR token is active, `__token__` MUST be omitted; its presence is non-compliant.

---

## 7. Compliance

Any output that violates canonical prefix, required timing, or minimum schema
rules in this file is non-compliant with AGENTS.md.

---

© 2026 Younghoon. All rights reserved.
