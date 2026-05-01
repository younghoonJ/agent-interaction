> ### Confidential & Proprietary
>
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-19

---

# Testing & Verification Guidelines (Core)

---

## 1. Scope

This document defines baseline testing and verification requirements for general software changes.

It applies to:

* Python/JS/TS code generation
* refactoring
* bug fixes
* code review verification

For numerical/ML operator work, this core document MUST be used together with:
`guidelines/testing-ml.md`.

---

## 2. Core Principles

* **[MUST]** Ensure each test case is atomic and independent.
* **[MUST NOT]** Allow side effects from one test to affect another.
* **[MUST]** Add or update tests for every behavior-changing implementation change.
* **[MUST]** Add a regression test before fixing a reproducible bug.
* **[SHOULD]** Use pytest or project-standard framework.

---

## 3. Minimum Verification Gate

Before delivery, the agent MUST complete all of the following:

1. Execute relevant test suites for changed components.
2. Verify new/updated tests fail before fix (for bugfix tasks) and pass after fix.
3. Confirm no placeholder implementation remains in delivered implementation files (`TODO`, `FIXME`, stub returns). Documentation-only TODO/FIXME notes are out of scope for this gate.
4. Confirm failure paths are covered for newly introduced error handling.

If any required verification step cannot be executed, output MUST explicitly report:

* which step was not run
* why it was blocked
* residual risk introduced by the gap

---

## 4. Coverage Requirements

* **[MUST]** Cover nominal flow for new/changed behavior.
* **[MUST]** Cover at least one boundary or edge case per changed decision branch.
* **[MUST]** Cover invalid input or error behavior when input validation changes.
* **[SHOULD]** Keep tests deterministic (fixed seed or seedless deterministic strategy).

---

## 5. Agent-Specific Instructions

### 5.1 [Role: Coder]

* **[MUST]** Generate tests for each logic change.
* **[MUST]** Include a regression test for each fixed defect.
* **[SHOULD]** Use naming pattern `test_[module]_[unit]_[scenario]`.
* **[SHOULD]** If failure cause is unclear, classify uncertainty per `guidelines/uncertainty.md` before proposing a fix.

### 5.2 [Role: Reviewer]

* **[MUST NOT]** approve when required tests are missing or verification was skipped.
* **[MUST]** evaluate adequacy of boundary and error-path coverage.
* **[SHOULD]** verify test reproducibility in current environment.

### 5.3 [Role: Planner]

* **[MUST]** define Definition of Done (DoD) with explicit verification steps.
* **[MUST]** state required test commands for each subtask.

---

## 6. Failure Analysis & Reporting

* **[MUST]** provide relevant traceback/error logs when tests fail.
* **[MUST]** classify root cause (logic error, edge-case miss, environment mismatch, assumption error).
* **[MUST]** propose corrective action and rerun verification.

Refer to: `guidelines/failure-recovery.md`

---

## 7. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

© 2026 Younghoon. All rights reserved.
