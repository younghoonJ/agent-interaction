> ### Confidential & Proprietary
>
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.  
> Last updated: 2026-04-24

---

# Failure Detection & Recovery Protocol

---

## 0. Abstract

Defines the classification of execution failures, their detection criteria, and the structured recovery procedures an agent MUST follow to maximize task completion rate under non-deterministic conditions.

This document does NOT replace AGENTS.md failure handling (Section 7).  
It extends it with detection criteria and recovery paths.

---

## 1. Scope

Applies to all task types defined in AGENTS.md Section 3.2:

- Simple Task
- Composite Task
- Repetitive Task (per AGENTS.md Section 3.2)
- Ambiguous Task

---

## 2. Failure Taxonomy

Each failure MUST be classified into exactly one type before recovery is attempted.

### 2.1 Type 1 — Information Deficit

**Definition**: Execution cannot begin or continue due to missing, ambiguous, or contradictory input.

**Detection criteria** (any one sufficient):
- Required parameter is undefined or underspecified
- Conflicting requirements exist with no resolution rule
- Assumed context cannot be verified

**Examples**:
- Target API contract not provided
- Conflicting type constraints with no priority rule
- Environment state unknown at execution start

---

### 2.2 Type 2 — Execution Fault

**Definition**: Execution proceeded but produced an incorrect, incomplete, or unverifiable output.

**Detection criteria** (any one sufficient):
- Output fails structural validation
- Output is partial (stub, placeholder, or TODO present)
- Output cannot be verified against stated requirements
- Verification step was skipped or produced an error

**Examples**:
- Generated code fails to compile or pass tests
- Implementation covers only a subset of specified cases
- Output structure deviates from required schema

---

### 2.3 Type 3 — Silent Failure

**Definition**: Execution completed without an explicit error, but the output is incorrect or based on invalid assumptions. This is the highest-risk failure type.

**Detection criteria** (any one sufficient):
- Agent inferred an API, type, or behavior not present in the provided context
- Agent made an assumption that was not explicitly validated
- Output is internally consistent but does not match the actual requirement
- Agent completed without requesting clarification on genuinely ambiguous inputs

**Key property**: Type 3 failures are not self-reported by the agent.  
They MUST be caught by explicit self-audit steps defined in Section 4.

---

## 3. Failure Detection Protocol

### 3.1 Mandatory Self-Audit Checkpoints

The agent MUST perform a self-audit at the following points:

1. **Pre-execution** — before any implementation begins
2. **Post-decomposition** — after breaking a Composite Task into subtasks
3. **Post-implementation** — before delivering any output
4. **Post-verification** — after running tests or validation

### 3.2 Self-Audit Checklist

At each checkpoint, the agent MUST answer the following:

```
[ ] All required inputs are explicitly provided (not inferred)
[ ] All assumptions are stated and verifiable
[ ] No APIs, types, or behaviors have been invented
[ ] Output is complete — no stubs, placeholders, or TODOs
[ ] Output has been verified against stated requirements
[ ] Verification step was executed, not skipped
```

If any item is unchecked → classify failure type and enter recovery.

### 3.3 Confidence Threshold

The agent MUST NOT proceed when:

- Confidence in input interpretation is below explicit confirmation
- A required fact is absent from the provided context
- Two valid interpretations exist with no disambiguation rule

"I think this is what was meant" is NOT a valid basis for proceeding.  
The agent MUST surface the ambiguity explicitly.

---

## 4. Recovery Protocol

### 4.1 General Principles

- Recovery MUST be attempted before reporting failure to the user
- Recovery MUST NOT silently alter requirements or assumptions
- Each recovery attempt MUST be logged in the execution state report when Section 5 applies;
  otherwise it MUST be reported in the applicable `FAILURE::`, `UNCERTAINTY::`,
  `CLARIFICATION_NEEDED::`, or final output.
- Maximum recovery attempts per failure: **2**
- If recovery fails after 2 attempts → escalate to user (Section 4.5)

### 4.2 Type 1 Recovery — Information Deficit

```
DETECT → STOP execution
       → Identify the specific missing information
       → Formulate a minimal, precise clarification request
       → WAIT for user response
       → Resume from the point of interruption
```

Clarification request MUST:
- Identify exactly what is missing
- Provide options where possible
- NOT ask more than 3 questions per request

**MUST NOT**: Make an assumption and proceed without confirmation.

---

### 4.3 Type 2 Recovery — Execution Fault

```
DETECT → Identify the specific failure point
       → Determine root cause category:
           (a) Logic error in implementation
           (b) Missing edge case
           (c) Invalid assumption about environment
           (d) Incomplete decomposition of task
       → Apply targeted correction:
           (a)(b) → Revise implementation, re-verify
           (c)    → Surface assumption, request confirmation, revise
           (d)    → Re-decompose task, re-execute from failed subtask
       → Re-run full verification
       → If verification passes → deliver output
       → If verification fails again → attempt 2 or escalate
```

**MUST NOT**: Re-deliver the same output after a failed verification.  
**MUST NOT**: Expand scope beyond the failed component.

---

### 4.4 Type 3 Recovery — Silent Failure

Because Type 3 failures are not self-evident, recovery is triggered by the self-audit checklist (Section 3.2), not by an error signal.

```
DETECT (via self-audit) → Identify all inferred or assumed elements
                        → For each inference:
                            - Can it be verified from provided context? 
                              YES → verify and continue
                              NO  → treat as Type 1, request clarification
                        → Rebuild affected output components from verified facts only
                        → Re-run self-audit checklist
                        → Re-run verification
```

**Key rule**: An output built on an unverified inference MUST be discarded and rebuilt, not patched.

---

### 4.5 Escalation

Escalation to the user is triggered when:

- Recovery has been attempted twice without success
- The failure cannot be resolved without external information
- Conflicting requirements cannot be resolved by the priority rules in AGENTS.md Section 4

Escalation report MUST include:

```
1. Task state at time of escalation
   - Completed subtasks (if any)
   - Failed subtask and failure type
2. Root cause summary (1–3 sentences)
3. What is needed to resume
   - Specific missing information, OR
   - Decision required from user
4. Recovery attempts made
   - What was tried
   - Why it did not succeed
```

**MUST NOT** escalate without this report.  
**MUST NOT** discard completed subtask results — they MUST be preserved and reported.

---

## 5. Execution State Report

For Composite and Repetitive Tasks, the agent MUST maintain and report execution state when interrupted or upon completion.
For Simple Tasks, `EXECUTION_STATE::` is not required unless another applicable guideline
or runtime requires it; recovery state MUST still be represented in `FAILURE::`,
`UNCERTAINTY::`, `CLARIFICATION_NEEDED::`, or final output as applicable.

### 5.1 State Schema

Canonical source: `guidelines/ir-spec.md` (`EXECUTION_STATE::`).         
This document MUST NOT redefine the minimum schema; use `guidelines/ir-spec.md` Section 4.5 as the single source of truth.    

### 5.2 Resumability

An interrupted task is resumable if:

- Completed subtasks produced verified outputs
- The failed subtask is isolatable (does not invalidate completed work)
- Required clarification or correction can be applied to the failed subtask only

If resumable → agent MUST resume from the failed subtask, not restart.  
If not resumable → agent MUST report which completed subtasks are still valid.

---

## 6. Compliance

- Skipping the self-audit checkpoint is a **Type 3 failure trigger**, not a shortcut.
- Delivering output without verification is **non-compliant** with AGENTS.md Section 9.
- Proceeding past a detected Type 1 failure without clarification is **non-compliant** with AGENTS.md Section 7.

---

## 7. Integration with AGENTS.md

This document extends:

- **Section 6.5** (Fail-Fast) → adds detection criteria and classification
- **Section 7** (Failure Handling) → adds recovery paths and escalation structure
- **Section 8** (Output Requirements) → adds self-audit as a pre-delivery gate
- **Section 9** (Testing & Verification) → self-audit checkpoint 3 and 4 are verification gates

AGENTS.md Section 4 (Guideline Resolution Protocol) applies.  
In conflict, AGENTS.md takes precedence.

---

© 2026 Younghoon. All rights reserved.
