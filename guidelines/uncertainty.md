> ### Confidential & Proprietary
>
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.  
> Last updated: 2026-04-23

---

# Uncertainty Expression Protocol

---

## 0. Abstract

Defines how an agent MUST classify, express, and act on uncertainty during execution. Introduces a structured Intermediate Representation (IR) for uncertainty declarations to prevent Silent Failures (Type 3) and minimize unnecessary execution interruptions.

---

## 1. Scope

Applies to all points during execution where the agent cannot derive a fact, assumption, or decision with full confidence from the provided context.

Integrates with:
- `guidelines/failure-recovery.md` — uncertainty at BLOCK level triggers Type 1 or Type 3 failure
- `AGENTS.md` Section 6.3 (No Hallucination) — INFER and BLOCK levels are hallucination risk zones
- `AGENTS.md` Section 7 (Failure Handling) — BLOCK level maps to STOP and ask
- `guidelines/ir-spec.md` — canonical IR prefixes and minimum schema

---

## 2. Uncertainty Level Taxonomy

Each uncertainty instance MUST be classified into exactly one level.

### 2.1 BLOCK

**Definition**: The agent cannot derive the required fact from the provided context, and proceeding without it would invalidate the output or a significant portion of it.

**Criteria** (any one sufficient):
- Required input is absent from context
- Two or more valid interpretations exist with no disambiguation rule
- Proceeding requires inventing an API, type, contract, or behavior

**Mandatory action**: STOP. Do not proceed. Issue an uncertainty declaration and request clarification.

---

### 2.2 INFER

**Definition**: The agent can derive a plausible value through reasoning, but it is not explicitly stated in the provided context.

**Criteria**:
- Fact is implied but not confirmed
- Pattern exists in context but edge case is not covered
- Reasonable default exists but has not been explicitly authorized

**Mandatory action**: PROCEED_WITH_DECLARATION. State the inference explicitly using the IR before acting on it. Do not treat inference as confirmed fact.

---

### 2.3 LOW

**Definition**: The agent can derive the fact directly and unambiguously from the provided context with high confidence.

**Criteria**:
- Fact is explicitly stated in context
- Fact follows unambiguously from stated constraints
- No alternative interpretation is plausible

**Mandatory action**: PROCEED. No declaration required.

---

## 3. Uncertainty IR

### 3.1 Structure

When uncertainty level is BLOCK or INFER, the agent MUST emit an uncertainty declaration using the following IR before taking any action based on the uncertain element.

Canonical source: `guidelines/ir-spec.md` (`UNCERTAINTY::`).
This document MUST NOT redefine the minimum schema; use `guidelines/ir-spec.md` Section 4.3 as the single source of truth.

### 3.2 Field Definitions

Field semantics:

**`source` MUST be specific.** "The API contract" is not acceptable. "The return type of `process()` when input is empty" is acceptable.

**`basis` MUST reference context.** "I assumed" is not acceptable. "The provided schema shows X, but does not specify Y" is acceptable.

**`impact` determines level.** If impact is localized and recoverable → INFER. If impact invalidates a major output component → BLOCK.

### 3.3 Examples

**BLOCK example — missing contract:**
```
UNCERTAINTY::
  level:  BLOCK
  source: Return type of process() when input list is empty
  basis:  Function signature provided shows List[Item] for non-empty case.
          No specification for empty input behavior exists in context.
  impact: Error handling logic and caller implementation will be incorrect
          if the actual behavior differs from assumption.
  action: STOP
```

The clarification request is emitted separately using `CLARIFICATION_NEEDED::`.

**INFER example — implied convention:**
```
UNCERTAINTY::
  level:  INFER
  source: Naming convention for private helper functions
  basis:  All existing functions in provided codebase use snake_case.
          No explicit style rule provided for private helpers.
  impact: Naming inconsistency only. Does not affect correctness or behavior.
  action: PROCEED_WITH_DECLARATION
```

The applied inference is stated in the surrounding response before execution.

---

## 4. Behavioral Rules

### 4.1 Emission Rules

- The agent MUST emit the IR **before** acting on the uncertain element, not after.
- The agent MUST NOT suppress an IR because it expects the user will not notice.
- Multiple uncertainties in the same execution MUST each produce a separate IR.
- IR declarations MUST appear inline at the point of uncertainty, not aggregated at the end.

### 4.2 BLOCK Behavior

After emitting a BLOCK declaration, the agent MUST:

1. Stop execution of the affected component
2. Preserve all completed work up to the point of BLOCK
3. Formulate a minimal clarification request (max 3 questions)
4. Report execution state per `guidelines/failure-recovery.md` Section 5

The agent MUST NOT:
- Proceed with a guess after declaring BLOCK
- Emit BLOCK and then immediately resolve it with an assumption
- Re-classify BLOCK as INFER to avoid stopping

### 4.3 INFER Behavior

After emitting an INFER declaration, the agent MUST:

1. Treat the declared inference as a **provisional fact**, not a confirmed one
2. Proceed with implementation based on the inference
3. Flag the inferred element in the output (e.g., code comment, note)
4. Include the inference in the post-execution self-audit checklist
   (per `guidelines/failure-recovery.md` Section 3.2)

The agent MUST NOT:
- Omit the IR and proceed silently — this constitutes a Type 3 failure trigger
- Escalate an INFER to a full BLOCK unless impact reassessment justifies it

### 4.4 Reassessment Rule

During execution, if new information changes the impact assessment:

- INFER MAY be downgraded to LOW if context confirms the inference
- INFER MUST be upgraded to BLOCK if new information reveals the impact is larger than declared
- BLOCK MUST NOT be downgraded without explicit user confirmation

---

## 5. Clarification Request Format

When action is STOP, the agent MUST emit `CLARIFICATION_NEEDED::` using the canonical schema in `guidelines/ir-spec.md` Section 4.11.
This document MUST NOT redefine the minimum schema.

**Questions MUST be:**
- Answerable with a specific value, choice, or constraint
- Independent of each other where possible
- Ordered by impact (most critical first)
- Count-limited to at most 3

---

## 6. Integration with Failure Recovery

| Uncertainty Level | Failure Risk | Recovery Path |
|-------------------|--------------|---------------|
| BLOCK (not declared) | Type 3 | Self-audit detection → rebuild |
| BLOCK (declared, not stopped) | Type 2 | Re-execute from failure point |
| BLOCK (declared, stopped) | Type 1 | Clarification → resume |
| INFER (not declared) | Type 3 | Self-audit detection → rebuild |
| INFER (declared) | Low | Monitor at post-execution audit |
| LOW | None | No action required |

The highest-risk path is undeclared BLOCK or INFER — both collapse into Type 3 Silent Failure, which has no automatic detection signal.

---

## 7. Compliance

- Proceeding past a BLOCK without declaration is **non-compliant** with AGENTS.md Section 6.3.
- Proceeding past an INFER without declaration is a **Type 3 failure trigger** per `guidelines/failure-recovery.md`.
- Emitting an IR after acting on the uncertainty (retroactive declaration) is **non-compliant**.
- Re-classifying BLOCK as INFER without impact reassessment is **non-compliant**.

---

## 8. Integration with AGENTS.md

This document extends:

- **Section 6.3** (No Hallucination) → BLOCK and undeclared INFER are hallucination instances
- **Section 6.5** (Fail-Fast) → BLOCK triggers immediate stop, not silent continuation
- **Section 7** (Failure Handling) → BLOCK maps to "Missing information → STOP and ask"

AGENTS.md Section 4 (Guideline Resolution Protocol) applies.  
In conflict, AGENTS.md takes precedence.

---

© 2026 Younghoon. All rights reserved.
