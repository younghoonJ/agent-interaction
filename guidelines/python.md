> ### Confidential & Proprietary
> 
> **Author:** Younghoon  
> **Copyright:** © 2026 Younghoon  
> **Notice:** This document is part of the AGENTS.md suite. For internal use only.
> Last updated: 2026-04-19

---

# Python Guidelines (Specification)

---

## 1. Scope

This document defines Python-specific constraints for AI-generated code.  
It extends AGENTS.md and code-style guidelines.

---

## 2. Environment

* **[MUST]** Target Python 3.10+
* **[SHOULD]** Use pip or poetry

---

## 3. Determinism & Execution

* **[MUST]** Avoid non-deterministic behavior
* **[MUST]** Ensure consistent outputs
* **[SHOULD]** Avoid implicit ordering

---

## 4. Type System

* **[MUST]** Use type hints
* **[MUST]** Avoid Any unless justified
* **[SHOULD]** Prefer dataclass / TypedDict
* **[MUST]** Ensure type consistency

---

## 5. Imports

* **[MUST]** Use explicit imports
* **[MUST]** Avoid wildcard imports
* **[MUST]** Use pathlib instead of os.path

---

## 6. Code Structure

* **[MUST]** Follow PEP8 (≤120 chars)
* **[MUST]** Avoid deep nesting
* **[MUST]** Use f-strings

---

## 7. Naming

* **[MUST]** snake_case for variables/functions
* **[MUST]** PascalCase for classes
* **[MUST]** UPPER_CASE for constants

---

## 8. Async & Concurrency

* **[SHOULD]** Prefer parallel execution
* **[MUST]** Avoid blocking in async
* **[SHOULD]** Use asyncio.gather

---

## 9. Error Handling

* **[MUST]** Catch specific exceptions
* **[MUST]** No bare except
* **[MUST]** Provide contextual errors

---

## 10. Logging

* **[MUST]** Use logging, not print

---

## 11. File Handling

* **[MUST]** Use context managers

---

## 12. Configuration

* **[MUST]** No hardcoded secrets
* **[MUST]** Use env variables for all secrets (per `guidelines/security.md` §3.2)

---

## 13. Dependencies

* **[MUST]** Pin core dependencies

---

## 14. Testing

* **[SHOULD]** Use pytest
* **[MUST]** Test core logic
* **[MUST]** For numerical/ML operator tasks, load and follow `guidelines/testing-ml.md` in addition to core testing.

Refer to: `guidelines/testing.md`

---

## 15. Anti-Patterns

* **[MUST NOT]** circular imports

---

## 16. Compliance

Violation of any **[MUST]** rule is non-compliant.

---

## Appendix


### Appendix A. Examples (Non-Normative)

This appendix provides illustrative examples.
These examples are **non-normative** and do not override rules.

---

#### A.1 Type Hinting

Bad:

```python
def process(data):
    return data * 2
```

Good:

```python
from typing import List

def process(data: List[int]) -> List[int]:
    return [x * 2 for x in data]
```

---

#### A.2 Avoid `Any`

Bad:

```python
from typing import Any

def process(data: Any) -> Any:
    return data
```

Good:

```python
def process(data: int) -> int:
    return data * 2
```

---

#### A.3 Docstrings

Bad:

```python
def add(a, b):
    return a + b
```

Good:

```python
def add(a: int, b: int) -> int:
    """
    Add two integers.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Sum of a and b
    """
    return a + b
```

---

#### A.4 Context Manager

Bad:

```python
f = open("file.txt")
data = f.read()
f.close()
```

Good:

```python
with open("file.txt") as f:
    data = f.read()
```

---

#### A.5 Exception Handling

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

---

#### A.6 Constant Extraction

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

---

#### A.7 Function Responsibility

Bad:

```python
def process(data):
    validate(data)
    transform(data)
    save(data)
```

Good:

```python
def validate(data):
    ...

def transform(data):
    ...

def save(data):
    ...

def process(data):
    validated = validate(data)
    transformed = transform(validated)
    save(transformed)
```

---

© 2026 Younghoon. All rights reserved.
