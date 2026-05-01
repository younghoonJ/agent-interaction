> ### Confidential & Proprietary
> 
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-23

---

# Code Style Guidelines (Specification)

---

## 1. Scope

This document defines **global coding constraints** for all AI-generated code.

It applies across:

* all programming languages
* all execution environments
* all task types

This specification MUST be enforced alongside AGENTS.md.

---

## 2. Core Constraints

---

### 2.1 Determinism

#### Definition

Determinism is the property that identical inputs produce identical outputs.

#### Rules

* **[MUST]** Produce reproducible outputs
* **[MUST NOT]** Rely on implicit ordering or randomness
* **[SHOULD]** Avoid non-deterministic constructs unless required

---

### 2.2 No Hallucination

#### Definition

Hallucination is the use of undefined or non-existent APIs, data, or behavior.

#### Rules

* **[MUST]** Use only explicitly defined APIs, types, and modules
* **[MUST NOT]** Invent functions, fields, or interfaces
* **[MUST]** Request clarification when information is missing

---

### 2.3 Completeness

#### Rules

* **[MUST]** Produce complete implementations
* **[MUST NOT]** Include placeholder logic
* **[SHOULD]** Use `TODO` / `FIXME` only with clear context during development; all such markers MUST be removed from implementation files before delivery per AGENTS.md Section 8.

---

### 2.4 Fail-Fast

#### Rules

* **[MUST]** Validate assumptions early
* **[MUST]** Raise explicit errors on failure
* **[MUST NOT]** use silent fallback behavior

---

## 3. Code Structure

---

### 3.1 Naming

* **[MUST]** Use clear and descriptive identifiers
* **[SHOULD]** Avoid abbreviations unless widely accepted or the meaning is crystal clear (e.g., `url`, `id`, `db`).

---

### 3.2 Single Responsibility Principle (SRP)

* **[MUST]** Each function or class must have a single responsibility
* **[SHOULD]** Keep functions focused
---

### 3.3 Function Size

* **[SHOULD]** Keep functions ≤ 50 lines
* **[SHOULD]** Refactor larger functions unless justified

---

### 3.4 Complexity

* **[MUST NOT]** Use deep nesting (>3 levels)
* **[SHOULD]** Keep control flow simple and predictable

---

## 4. Type Safety

* **[MUST]** Use the language's type system
* **[MUST NOT]** Use untyped constructs (`Any`, `any`) without justification
* **[MUST]** Maintain type consistency across boundaries

---

## 5. Error Handling

* **[MUST]** Handle exceptions explicitly
* **[MUST NOT]** use bare exception handlers
* **[MUST]** Provide actionable error messages
* **[MUST NOT]** silently ignore errors

---

## 6. Elimination of Implicit Behavior

---

### 6.1 Magic Values

#### Definition

A magic value is a literal constant whose meaning is not explicitly defined.

#### Rules

* **[MUST]** Replace magic values with named constants
* **[MUST NOT]** introduce unexplained literals

---

### 6.2 Side Effects

* **[MUST]** Make side effects explicit
* **[MUST NOT]** introduce global mutable state
* **[SHOULD]** Separate pure logic from side effects

---

## 7. Documentation

* **[MUST]** Document all public APIs:

  * purpose
  * parameters
  * return values
  * exceptions

* **[MUST]** Write comments explaining **why**, not **what**

---

## 8. Duplication (DRY)

### Acceptable Cases

Duplication is acceptable when:

* **[MAY]** Cross-layer isolation is required
* **[MAY]** Abstraction reduces clarity
* **[MAY]** Test code requires independence
* **[MAY]** Framework conventions require repetition

---

### Prohibited Cases

* **[MUST NOT]** Duplicate logic in ≥3 locations
* **[MUST NOT]** Require synchronized updates across copies
* **[MUST]** Extract when extraction is safe and clear

---

## 9. Resource Management

* **[MUST]** Manage resources explicitly
* **[MUST]** Use structured constructs (`with`, `using`)
* **[MUST NOT]** leak resources

---

## 10. Anti-Patterns

The following are strictly prohibited:

* **[MUST NOT]** Global mutable state
* **[MUST NOT]** Silent failure handling
* **[MUST NOT]** Hidden dependencies
* **[MUST NOT]** Unbounded complexity
* **[MUST NOT]** Implicit side effects

---

## 11. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

## Appendix

### Appendix A. DRY (Non-Normative)

Avoid duplication, but prioritize clarity.

Duplication is **acceptable** when:

| Case | Example |
|---|---|
| **Cross-layer isolation** | identical validation logic in frontend and backend that must stay decoupled |
| **Readability over abstraction** | extracting would require more context than the duplication itself (e.g., a helper needing 3 parameters to replace a 2-line snippet, or an abstraction that obscures the intent of each call site) |
| **Test code** | test setup/teardown that mirrors production code for clarity and independence |
| **Framework convention** | boilerplate required by the framework (e.g., React component structure, pytest fixtures) |

Duplication is **not acceptable** when:

| Condition | Example |
|---|---|
| **Same logic, same intent, 3+ places** | identical permission check copied across 3 route handlers for the same reason |
| **Block longer than 5 lines AND intent is clear** | a data transformation block repeated across modules where a shared utility would be straightforward |
| **Change in one place requires updating others** | a business rule duplicated in 2 places that must always stay in sync |

---

### Appendix B. Examples (Non-Normative)

This appendix provides illustrative examples.
These examples are non-normative and do not override rules.

B.1 Magic Values

Bad:
```python
if retries > 3:
    raise Exception("failed")
```

Good:
```python
MAX_RETRIES = 3
if retries > MAX_RETRIES:
    raise Exception("failed")
```

B.2 Comments

Bad:
```python
# increment i
i += 1
```

Good:
```python
# offset by 1 to skip header row
i += 1
```

B.3 Error Handling

Bad:
```python
try:
    process()
except:
    pass
```

Good:
```python
try:
    process()
except ValueError as e:
    raise RuntimeError(f"Processing failed: {e}")
```

B.4 Duplication

Bad:
```python
if user.role == "admin":
    allow()
if user.role == "admin":
    log_access()
```

Good:
```python
def is_admin(user):
    return user.role == "admin"

if is_admin(user):
    allow()
    log_access()
```

---

© 2026 Younghoon. All rights reserved.
